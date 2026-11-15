# First-boot setup service

Runs `control/setup/` at boot: the device name, the Wi-Fi onboarding page and
the first baseline. The installer prepares files only; **nothing here has been
run on a device.** No unit has been enabled, no radio has been raised by it, and
no `nmcli`, `hostnamectl` or `raspi-config` call has been made by Debra. Read
[what is still unproven](#what-is-still-unproven) before trusting a step.

The journey itself is described in [first boot](../../docs/design/first-boot.md);
this page is only the service around it.

## What one boot looks like

The unit runs on every boot and asks `Onboarder.resume()`
([`onboarding.py`](onboarding.py)) what that boot is:

1. It gives NetworkManager up to 30 seconds to autoconnect. A configured device
   usually joins its own network in that window, and the boot is then quiet.
2. `resume()` decides from the recorded state. Online: nothing to do, the
   process exits 0 and no page is started.
3. No usable uplink: it sets the device name, raises the setup access point,
   writes the setup-network password to the boot partition, and serves the page
   on the address the access point actually got. In shared mode that is
   `http://10.42.0.1/`, which is also the fallback when the address cannot be
   read.
4. A submission joins the household network. On success the phase becomes
   `online`, the access point is gone, and the service closes the listening
   socket within a couple of seconds rather than leaving the page open. It then
   waits up to five seconds for the first baseline, because the join worker
   captures it after recording the online phase. On failure the access point
   comes back with the reason and the page keeps serving.
5. After the first successful join the baseline is captured once. It is
   configuration recovery, not whole-device recovery, and it contains secrets.

Nothing reboots the device to apply Wi-Fi, nothing restarts NetworkManager, and
no passphrase is written anywhere except NetworkManager's own keyfile.

## Why this is a system unit, not a user unit

The [web installer](../web/README.md) uses a systemd **user** unit, because it
controls one user's audio session. This cannot, and the reasons are specific:

- `nmcli device wifi hotspot` and `nmcli connection load` change system-wide
  NetworkManager state. A user unit runs with no seat and no login session, so
  polkit has nobody to authenticate and refuses. It would install cleanly and
  then fail at boot.
- `raspi-config nonint do_wifi_country` writes the supplicant configuration and
  the regulatory domain, and needs root.
- The setup page binds port 80, a privileged port.
- The baseline reads `/etc/NetworkManager/system-connections`, which is
  root-only, and writes `/var/lib/debra`.
- The setup-network note goes to the boot partition, which is owned by root.

A unit that silently fails at boot is worse than an honest system unit, so this
one is `WantedBy=multi-user.target` and runs as root.

**The tradeoff:** a root process serves an HTTP page that accepts a Wi-Fi
passphrase from whoever is on the setup network. Three things limit that, and
none of them make it a secure portal:

- The page is bound to the access point's own address, not `0.0.0.0`, so it is
  reachable only through the setup access point, not from the household network.
- The access point is WPA2 with a password derived from the device name and
  written to the boot partition. Anyone who can join the setup network can also
  submit the form; the password protects the setup window, not the household.
- The service shuts the page down as soon as the device is online.

Port 80 rather than 8080 is the same kind of choice: the journey promises
`http://10.42.0.1/`, and a port suffix is one more thing a beginner has to be
told and can mistype. Root can bind it. `0.0.0.0` is not an option: the portal's
same-origin check compares the `Host` header with the address it was given, so a
wildcard bind would reject the pages it served.

## What the device must already have

- NetworkManager with `NetworkManager.service`, and `nmcli`.
- Python 3.10 or newer, at an absolute path.
- `iw` (the country read) and `raspi-config` (only used when a country has to be
  set). On a board with no country the radio can be off, so the country step
  fails and the access point cannot start.
- A Wi-Fi interface.
- A boot partition at `/boot/firmware` (Raspberry Pi OS Bookworm) or `/boot`.
- Root.

The installer installs no packages and changes no network setting.

## Install

On the device, from the repository root, as root:

```sh
sudo python3 -B control/setup/install.py --python "$(command -v python3)"
```

It prints the release id and path, the unit, the state directory, the card-note
path, the retained previous unit (when upgrading) and `changed`. It prepares
files only. To make the service run at boot, after reviewing the unit:

```sh
sudo systemctl daemon-reload
sudo systemctl enable --now debra-setup.service
```

`--root <directory>` prepares another tree instead of `/`; the unit it writes
still names the device paths (`/usr/local/lib/debra/setup/...`), so it is only
useful for inspection or imaging. `--restore <unit>` is the rollback below.

## What it writes

| Path on device | Mode | Purpose |
| --- | --- | --- |
| `/usr/local/lib/debra/setup/releases/<sha256>/` | `0700` | Fixed payload, content-addressed; old releases retained |
| `/usr/local/lib/debra/setup/previous-units/` | `0700` | Previous generated units, retained for rollback |
| `/var/lib/debra/setup/setup.json` | `0600` | The setup state; no passphrase |
| `/var/lib/debra/setup/baseline/` | `0700` | Baseline archive and manifest; contains secrets |
| `/var/lib/debra/setup/keyfiles/` | `0700` | Transient keyfile before `nmcli connection load` deletes it |
| `/etc/systemd/system/debra-setup.service` | `0644` | The rendered unit; no credential |
| `/boot/firmware/debra-setup.txt` | (boot partition) | Setup-network name and password, written at runtime |

`debra-setup.service` in this directory is the **template**: the installer
substitutes `@PYTHON@`, `@RUNNER@`, `@STATE@` and `@CARD_NOTE@` with
systemd-quoted values. It is copied into the release as well, so a re-install
from a release works. The release also contains `install.py` itself, because the
unit runs `releases/<id>/install.py --serve`; the runner on the device is
therefore this reviewed file and not a generated second program.

An identical install changes nothing and creates no rollback copy. A release or
unit that differs from what the installer would write is refused, not
overwritten. Nothing is ever deleted.

## Check that it worked

```sh
systemctl status debra-setup.service
journalctl -u debra-setup -b --no-pager
sudo systemctl show debra-setup.service -p ExecStart -p MainPID
sudo cat /var/lib/debra/setup/setup.json
ss -ltn 'sport = :80'
```

- On a device that is already online the unit is `inactive (dead)` with
  `status=0/SUCCESS`. That is the expected result, not a failure: it decided
  there was nothing to do. The journal says `setup phase online`.
- On a device with no uplink the journal says `setup phase hotspot` and
  `setup page listening on http://<address>/`, naming the address it bound. The
  card note on the boot partition holds the setup-network name and password.
- `ExecStart` must name the `releases/<id>/install.py` that the installer just
  reported. `MainPID` and `ps -p <pid> -o args=` must show the same path.
- After the device is online, `ss` must show nothing listening on port 80. The
  unit's `ExecStart` is the only thing that ever binds it.

## Roll back

An upgrade keeps the unit it replaced. Use the exact `previous_unit` path that
install printed, not an arbitrary newest file:

```sh
sudo python3 -B control/setup/install.py --restore '<previous_unit>'
sudo systemctl daemon-reload
sudo systemctl restart debra-setup.service
```

The restore is a temp file plus an atomic rename, not `cp`: a copy interrupted
partway leaves a truncated unit that cannot start. The old release is retained,
so the restored unit still names real code. `--restore` refuses a file that is
not a unit this installer wrote and is not under `previous-units/`.

To stop the service without removing anything:

```sh
sudo systemctl disable --now debra-setup.service
```

This is **setup-service rollback**, not whole-device recovery. Speech, music and
the web prototype are unaffected; they are separate units.

## What is still unproven

Ordered by how likely it is to bite on a real first boot.

1. **The portal's bind address is read from NetworkManager, with a fallback.**
   It asks for the access point interface's IPv4 and binds that, falling back to
   `10.42.0.1` when the read returns nothing. If both are wrong the bind fails,
   the unit exits non-zero, and systemd retries three times in five minutes and
   gives up — while the card note has already been written, so the person has a
   setup network and no page. Neither path has run against a real radio.
2. **The 30-second uplink wait is a guess.** If NetworkManager takes longer than
   that to autoconnect on a slow card, a configured device raises a setup access
   point, and the household connection may not come up until the next boot. No
   boot has been timed.
3. **Only Wi-Fi uplinks count.** `nmcli`-based `active()` looks at Wi-Fi devices,
   so a device with working Ethernet and no Wi-Fi still raises the setup access
   point.
4. **Nothing has read a real root-only keyfile set.** The baseline has only ever
   run against a temporary root.
5. **The device name is applied with `hostnamectl`, which has never run.** The
   adapter refuses a name that would not resolve as `<name>.local`, but no boot
   has applied one, and a failure is logged and carried past rather than retried,
   so the page can show a name the device does not answer to.
6. **No captive-portal helper.** A phone will not offer to open the page; the
   address has to be typed from the card note.
7. **If `/boot/firmware` is not mounted when the note is written**, the note is
   created on the root filesystem instead. The service logs a warning and the
   access point still starts.
8. **The unit has never been loaded by systemd.** The tests read the rendered
   unit as text; they do not run `systemd-analyze verify`, and they prove nothing
   about polkit, D-Bus or a radio.

The offline checks behind this page:

```sh
python3 -B -m unittest tests.test_setup_install -v
python3 -B -m unittest tests.test_onboarding -v
```

They prove the artifacts on disk and the boot decisions against a recorded fake
NetworkManager. They prove nothing about hardware.

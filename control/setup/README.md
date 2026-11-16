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
3. No usable uplink: it sets the device name, looks for nearby networks while
   the radio is still free, raises the setup access point, writes the
   setup-network password to the boot partition, and serves the page on the
   address the access point actually got. In shared mode that is
   `http://10.42.0.1/`, which is also the fallback when the address cannot be
   read. The scan is a convenience for the form: a failure is an empty list and
   the person types the name, which always works.
4. A submission joins the household network. The profile is written into
   NetworkManager's own store, pinned to the radio in use, and promoted to
   autoconnect only after the join is verified, so the device rejoins the
   household network on the next boot. On success the phase becomes `online`,
   the access point is gone, and the service closes the listening socket within
   a couple of seconds rather than leaving the page open. It then waits up to
   five seconds for the first baseline, because the join worker captures it
   after recording the online phase. That grace is a wait, not a deadline: the
   worker thread is deliberately not a daemon so that a capture in progress is
   not abandoned, and a slow capture therefore keeps the process alive past
   those five seconds. On failure the access point comes back with the reason
   and the page keeps serving.
5. Once the socket is bound, the note on the boot partition is reprinted with
   the address that is actually listening. The note written when the access
   point came up carries the address the radio reported, and those two are not
   always the same. A person typing an address the portal's own same-origin
   check rejects is stuck at the first step of setup.
6. After the first successful join the baseline is captured once. It is a
   **capture, not a recovery point in practice**: nothing in this repository
   restores from it, no restore has been run, and the allowlist captures
   configuration files, not a package or hardware inventory. It contains
   secrets.

Nothing reboots the device to apply Wi-Fi, nothing restarts NetworkManager, and
no passphrase is written anywhere except NetworkManager's own keyfile.

## Why this is a system unit, not a user unit

The [web installer](../web/README.md) uses a systemd **user** unit, because it
controls one user's audio session. This cannot, and the reasons are specific:

- `nmcli connection reload`, `nmcli connection up` and `nmcli connection delete`
  change system-wide NetworkManager state. A user unit runs with no seat and no
  login session, so polkit has nobody to authenticate and refuses. It would
  install cleanly and then fail at boot.
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

- The page is bound to the access point's own address rather than `0.0.0.0`.
  That is **not** ingress-interface enforcement: binding an address decides
  which address the kernel accepts requests on, not which interface a packet
  arrived from, and there is no firewall rule here. What actually keeps the page
  off the household network is that the address exists only while the access
  point does.
- The access point is `wpa-psk` with a random per-device password that is
  written only to the boot-partition note. It is kept in
  `/var/lib/debra/setup/setup-secret` (`0600`) so the note stays true when the
  access point is raised again, and it is deliberately absent from the status
  API, which anything that has joined can read. Anyone who can join the setup
  network can also submit the form; the password protects the setup window, not
  the household. The access point is raised from a profile this repository
  writes into NetworkManager's own store, so its key management is the one that
  was asked for and the password never appears in a command line. The profile's
  key management and the device's active connection are both read back after
  activation, and a mismatch takes the access point down. `nmcli device wifi
  hotspot` cannot be used for this at all, because with no password it generates
  one that nobody is shown, which is not an open network. `wpa-psk` is the
  setting; WPA2 is what NetworkManager's default `proto` makes of it, which this
  code does not pin - and all of it is unproven on a radio.
- The mode is a choice the page owns, not only the installer. It is kept in
  `/var/lib/debra/setup/setup-security` (`0600`) beside the password, deliberately
  not in `setup.json` whose schema is closed, and it wins over the installed flag
  from the first change onwards. Switching keeps the same profile: a deleted and
  recreated shared connection is handed the next subnet, which would move the
  address the page is already bound to.
- **Development mode, and today's default:** the setup network comes up open,
  with no password at all, and the page and the card note both say so. Typing a
  card password on every development boot is friction with no corresponding risk
  on a desk, so `DEFAULT_SETUP_SECURITY` in
  [`onboarding.py`](onboarding.py) is `"none"` until release planning says
  otherwise; that one line is the release decision. `--setup-security wpa`
  installs the protected mode, which stays implemented and tested, and the setup
  page can switch between them without a reinstall. The installer warns, and the
  installed flag is the mode a device starts in; from the first change on the
  page the stored choice is the one that is used. Never ship an image built that
  way.
- The service shuts the page down as soon as the device is online.

Port 80 rather than 8080 is the same kind of choice: the journey promises
`http://10.42.0.1/`, and a port suffix is one more thing a beginner has to be
told and can mistype. Root can bind it. `0.0.0.0` is not an option: the portal's
same-origin check compares the `Host` header with the address it was given, so a
wildcard bind would reject the pages it served.

## The phone should offer to open the page

Phones and laptops ask a well-known address whether they are behind a captive
portal: `/generate_204` on Android, `/hotspot-detect.html` on Apple devices,
`/connecttest.txt` and `/ncsi.txt` on Windows, `/canonical.html` on Firefox.
The portal answers each of those with a `302` to its own page, built from the
address it bound rather than from the request's `Host` header, so it cannot be
used as an open redirect. That is what makes the operating system show a "sign
in to network" sheet instead of the person having to read an address off the
card.

**Whether the probe ever arrives is unverified.** It depends on the setup
network resolving those names to the access point, which is the DNS that
NetworkManager's shared mode runs, not something Debra configures. If it does
not, the page is still reachable by typing the address from the card note, and
nothing is worse than before. On a device, this is the check:

```sh
# while the setup access point is up, from a phone or laptop joined to it
getent hosts connectivitycheck.gstatic.com   # should answer the AP address
curl -sI http://connectivitycheck.gstatic.com/generate_204 | head -3
```

A `302` with a `Location` on the setup network is the whole mechanism working.

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
path, the setup security, the retained previous unit (when upgrading) and
`changed`. It prepares files only. To make the service run at boot, after
reviewing the unit:

```sh
sudo systemctl daemon-reload
sudo systemctl enable --now debra-setup.service
```

`--root <directory>` prepares another tree instead of `/`; the unit it writes
still names the device paths (`/usr/local/lib/debra/setup/...`), so it is only
useful for inspection or imaging. `--restore <unit>` is the rollback below.

**`--setup-security` decides whether the setup network is open, and the default
today is `none`** - the development bypass, so the access point comes up open
with no password at all. That is a deliberate development-phase choice, not a
shipping posture: see the **Development mode** bullet under "Why this is a
system unit" above, and
`DEFAULT_SETUP_SECURITY` in [`onboarding.py`](onboarding.py), whose single line is
the release decision.

```sh
sudo python3 -B control/setup/install.py --python "$(command -v python3)" \
    --setup-security wpa
```

`--setup-security wpa` installs the protected setup network: a random per-device
password on the boot-partition note. Whatever is chosen is written into the unit
as an argument, so the mode a device runs is something the unit says and not a
default that a later change can reinterpret. The installer prints a warning when
the mode is `none`. The page can switch the running device between the two
without a reinstall, and that choice is kept in
`/var/lib/debra/setup/setup-security`.

## What it writes

| Path on device | Mode | Purpose |
| --- | --- | --- |
| `/usr/local/lib/debra/setup/releases/<sha256>/` | `0700` | Fixed payload, content-addressed; old releases retained |
| `/usr/local/lib/debra/setup/previous-units/` | `0700` | Previous generated units, retained for rollback |
| `/var/lib/debra/setup/setup.json` | `0600` | The setup state; no household passphrase and no setup-network password |
| `/var/lib/debra/setup/setup-secret` | `0600` | The setup-network password, so a re-raised access point matches the note |
| `/var/lib/debra/setup/setup-security` | `0600` | The mode chosen on the page (`wpa` or `none`); one word, read at every start |
| `/var/lib/debra/setup/baseline/` | `0700` | Baseline archive and manifest; contains secrets |
| `/etc/NetworkManager/system-connections/<id>.nmconnection` | `0600` | The household Wi-Fi profile, written by the join and kept; it is the only copy of that passphrase |
| `/etc/systemd/system/debra-setup.service` | `0644` | The rendered unit; no credential |
| `/boot/firmware/debra-setup.txt` | (boot partition) | Setup-network name and password, written at runtime |

`debra-setup.service` in this directory is the **template**: the installer
substitutes `@PYTHON@`, `@RUNNER@`, `@STATE@`, `@CARD_NOTE@` and `@SECURITY@`
with systemd-quoted values. It is copied into the release as well, so a re-install
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

1. **The Wi-Fi profile has never been loaded by a real NetworkManager.** The
   profile is written into `/etc/NetworkManager/system-connections` and loaded
   from there, because a keyfile anywhere else is not one the keyfile plugin
   will read again after a reboot. That the plugin accepts this file, that the
   profile survives a reboot, and that `connection modify ... autoconnect yes`
   takes effect are all untested. A profile that is not promoted leaves the
   device with no network at all on the next boot, so the join treats a failed
   promotion as a failed join and brings the setup network back.
2. **The portal's bind address is read from NetworkManager, with a fallback.**
   It asks for the access point interface's IPv4 and binds that, falling back to
   `10.42.0.1` when the read returns nothing. If the bind fails, the access
   point is taken back down and the phase is recorded as `failed`, so the device
   does not sit there offering a network with no page — but the person then has
   neither a page nor a setup network, and needs a console. Neither path has run
   against a real radio, and the listener is not rebound if a recreated access
   point lands on a different subnet.
3. **The 30-second uplink wait is a guess.** If NetworkManager takes longer than
   that to autoconnect on a slow card, a configured device raises a setup access
   point, and the household connection may not come up until the next boot. No
   boot has been timed.
4. **Only Wi-Fi uplinks count.** `nmcli`-based `active()` looks at Wi-Fi devices,
   so a device with working Ethernet and no Wi-Fi still raises the setup access
   point.
5. **Nothing has read a real root-only keyfile set.** The baseline has only ever
   run against a temporary root.
6. **The device name is applied with `hostnamectl`, which has never run.** The
   adapter refuses a name that would not resolve as `<name>.local`, and the name
   is applied again on every boot, so a failure is retried rather than
   remembered as done. No boot has applied one.
7. **The captive-portal redirect may never be asked for.** The probe paths are
   answered, but the setup network's DNS decides whether a phone reaches them;
   see [above](#the-phone-should-offer-to-open-the-page). Until that is measured
   on a phone, the card-note address is the reliable route.
8. **The network scan has never run against a radio.** It is issued once, before
   the access point is raised, because a scan with the access point up can drop
   the person's phone off it. Whether that window is clean on a real driver, and
   how long the scan takes, is untested. A failed or slow scan is not fatal, but
   it does delay the page appearing.
9. **If `/boot/firmware` is not mounted when the note is written**, the note is
   created on the root filesystem instead, where the person holding the card
   cannot see it. The service warns (`The setup note is not on a mounted boot
   partition`) and the access point still starts. Nothing refuses to run without
   that partition, and no boot has been tried with it absent.
10. **The unit has never been loaded by systemd.** The tests read the rendered
    unit as text; they do not run `systemd-analyze verify`, and they prove
    nothing about polkit, D-Bus or a radio.
11. **The cooldown is words, not a countdown.** The page says to wait ten
    minutes because the attempt counter lives in the state file and a power
    cycle does not clear it. There is no retry-after the page can count down.

## How the risky steps are kept small

These are the decisions that the tests defend, and the reasons they exist:

- **The page is answered before the radio is touched.** A submission reserves
  the attempt, writes the `202`, and only then does a worker stop the access
  point and associate. The reply is the last thing that can travel over the
  setup network. If the reply cannot be written at all — the phone dropped —
  the reservation is released, so the device is not left `connecting` for ever.
- **A reservation is identified by a token, not by a network name.** The same
  network can be retried with a corrected password, so the name cannot say which
  attempt a worker belongs to. The token is random because the timestamp beside
  it has one-second resolution.
- **Success means the profile that was just loaded is the active connection**,
  on the radio the page was reached over, with a routable address and a default
  route. A connected radio is not proof of any of that.
- **The country is set after the access point is down.** It is a radio change,
  and doing it before the reply could disrupt the only channel the person has.
- **A failed attempt deletes its profile and its file**, so a wrong password
  never leaves a profile competing with the household network.
- **A baseline is published, not overwritten.** Each file is written under a
  name nothing reads, flushed, and linked into place; `os.link` refuses to
  replace an existing file, and the manifest is published last. A same-second
  retry gets a suffix instead of overwriting. A capture never archives its own
  directory, a file is read whole before it is added to the archive, and
  `latest()` only returns a manifest whose archive still hashes to what it says.
- **The setup page prints the address it is served on**, not `<hostname>.local`:
  the same-origin check admits only that address, and the `.local` name returned
  `403`.

The offline checks behind this page:

```sh
python3 -B -m unittest tests.test_setup_install -v
python3 -B -m unittest tests.test_onboarding -v
```

They check the artifacts on disk, the boot decisions, and the page's own
behaviour in a real browser, all against a recorded fake NetworkManager. They do
not prove anything about a radio, a real keyfile read, systemd, or hardware. Each
of the guards above was also checked by breaking it and watching one of these
tests fail, except where the page below says otherwise.

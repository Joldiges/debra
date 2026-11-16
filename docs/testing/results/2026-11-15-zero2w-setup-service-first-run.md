# First device run of the setup service: it works, and it leaves two defects

**2026-11-15/16 — `control/setup/` installed and run on the Zero 2 W for the
first time.** The online path behaved as designed, the board renamed itself from
its hardware serial, and a baseline was captured. Two real defects were found,
both in what happens *around* the rename.

Author: OpenCode session, `openrouter/deepseek/deepseek-v4.1-flash-1017`, variant
not exposed by the host. Host: Fedora. Debra baseline `a90cfba`. Board: Pi Zero
2 W, `wlan0` `2c:cf:67:87:7b:f9`, serial `00000000468518d6`. Release
`f534bd1e5f55da5ec2787936b1ed9ce36e9133c23761799de27f1e6b7478e07e`.

## Install

The committed tree was transferred, not the working tree, and verified:

```
$ git archive HEAD control/setup | ssh debra@debra-lab.local 'tar -x -C ~/debra'
$ diff <local sha256sums> <device sha256sums>   # identical, 12 files
```

Before installing, the leftover cloud-init seed files (`user-data`,
`network-config`, `meta-data`, holding the household passphrase in clear on a FAT
partition) were removed. cloud-init had already consumed instance
`rpi-imager-1794791822499`, so this was cleanup, and a grep of `/boot/firmware`
afterwards found no credential text.

`install.py --python /usr/bin/python3` reported `changed: True`, release
`f534bd1e…`, `previous_unit: None`. The rendered unit's `ExecStart` names that
release, with `--state-dir /var/lib/debra/setup` and
`--card-note /boot/firmware/debra-setup.txt`.

## The uplink decision was checked before letting the service act

The unit runs at boot and would raise a setup access point if it decided there
was no uplink, which on a device reached over Wi-Fi means losing it. So the
decision input was exercised read-only first, by importing the release's own
modules:

```
active(): {'interface': 'wlan0', 'address': '192.168.0.99',
           'gateway': '192.168.0.1', 'routable': True, 'has_route': True}
active_connection(wlan0): home
name it would choose:     debra-8518d6
```

That predicted both the online path and the new name. Worth repeating as a
habit: this is the one place where a wrong answer costs the session.

## Result: the online path, exactly as documented

| Check | Observed |
| --- | --- |
| Exit | `status=0/SUCCESS`, `inactive (dead)`, 1.28 s, `Consumed 1.198s CPU time` |
| Journal | `INFO setup phase online, device name debra-8518d6` |
| Port 80 | nothing listening (`ss -ltn 'sport = :80'` empty) |
| Hostname | `debra-lab` → **`debra-8518d6`** in `/etc/hostname` and `hostnamectl --static` |
| Baseline | `baseline-20261116T044123Z.tar.gz`, 9449 bytes, 8 files, `0600 root`, plus a JSON manifest |
| State | `phase: online`, `address: 192.168.0.99`, `hostname: debra-8518d6`, `baseline` set, `last_error: null` |
| Enabled | `multi-user.target.wants/debra-setup.service` created |

The manifest captures the two NetworkManager keyfiles (the household profile and
the console one), `/etc/hostname`, `/etc/timezone`, three `wpa_supplicant` shell
helpers and `setup.json`, with `missing: []` and its own directory correctly
skipped. **That archive contains the household passphrase**; the manifest says so
itself.

**A rename on an online connection did not disturb the connection.** `home`
stayed `activated` on `wlan0`, the address stayed `192.168.0.99`, and the SSH
session that ran the command survived. That answers the open question the
[setup README](../../../control/setup/README.md) records: "no device test has
measured what an actual rename does to an online connection."

A second run changed nothing: `setup.json` kept the same sha256 and no second
baseline appeared. That is the idempotency the design claims.

## Defect 1: `/etc/hosts` still names the old device

```
$ hostname -f
hostname: Name or service not known
$ getent hosts debra-8518d6
(nothing)
$ grep debra-lab /etc/hosts
127.0.1.1 debra-lab debra-lab
```

The service applies the name through `hostnamectl` but does not touch
`/etc/hosts`, so the loopback alias keeps the old name. Every `sudo` call then
prints:

```
sudo: unable to resolve host debra-8518d6: Name or service not known
```

For a product whose promise is that the beginner never debugs Linux, a device
that emits that warning on every privileged command is a defect, not cosmetics.
`/etc/hosts` here is cloud-init-managed (`manage_etc_hosts`), and the file's own
header says changes belong in `/etc/cloud/templates/hosts.debian.tmpl`; whether
cloud-init repairs the line at the next boot is untested.

## Defect 2: mDNS kept advertising the old name

Immediately after the rename, from the Fedora host:

```
$ avahi-resolve -n debra-8518d6.local     → timeout
$ avahi-resolve -n debra-lab.local        → 192.168.0.99
```

After `systemctl restart avahi-daemon` on the device, the answers inverted:
`debra-8518d6.local` → `192.168.0.99`, `debra-lab.local` → timeout. So
`avahi-daemon` does not follow a live hostname change on this image.

At boot this is self-correcting, because `/etc/hostname` already holds the new
name before avahi starts. The gap is a **first run on an already-running
device**: the name the state and the journal report is not the name the device
answers to until it is restarted. Both defects are the same shape — the service
changes the name and stops, leaving the two consumers of the name behind.

## Smaller observations

- `ssid` is `null` in the state while the device is online. That is by design:
  the code only records a network name for a join the device performed, and this
  boot adopted an existing connection.
- `country` is `null`; `raspi-config nonint do_wifi_country` has never run on this
  board. The radio works, but the setup path that needs a country is unexercised.
- `systemctl is-enabled cloud-init` answers `not-found` on this image, which is
  **not** evidence that cloud-init is absent: 25.2 ships `cloud-init-main`,
  `cloud-init-network` and `cloud-init-local` instead of a unit called
  `cloud-init`. The package is installed (`25.2-1~bpo13+1+rpt20`) and its
  `result.json` reports `errors: []` with the `file:///boot/firmware` seed.

## Not done

- No reboot after install. The unit is enabled but has never run as part of a
  boot, so "runs at boot, after NetworkManager is up, and leaves the device
  online" is still unproven.
- The onboarding page, the access point, a join performed by Debra, the rename
  by a *first* boot, and a restore from the baseline are all still unexercised.

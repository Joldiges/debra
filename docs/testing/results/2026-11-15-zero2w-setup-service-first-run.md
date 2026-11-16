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

## Boot test: the unit runs at boot, and both defects are boot-transient

The board was rebooted with the unit enabled (`systemctl reboot`; it answered SSH
again about 16 s later).

| Check | Observed |
| --- | --- |
| Unit at boot | started `23:46:12`, `INFO setup phase online, device name debra-8518d6`, deactivated `23:46:15`, `Result=success`, `NRestarts=0`, 1.29 s |
| Port 80 | nothing listening |
| State | `setup.json` sha256 unchanged; still one baseline, no second archive |
| Network | `home` activated on `wlan0`, `192.168.0.99` |
| mDNS | `debra-8518d6.local` → `192.168.0.99`; `debra-lab.local` times out |
| `hostname -f` | `debra-8518d6` — works again |
| `sudo` | quiet — no "unable to resolve host" |

So the service does run correctly as part of a boot, decides online, and leaves
the device connected and unchanged.

**What fixed defect 1 was cloud-init, not Debra.** cloud-init 25.2 ran in that
same boot (finished 26.5 s in) and rewrote the file to:

```
127.0.1.1 debra-8518d6 debra-lab
```

That is why `hostname -f` and `sudo` work again — and why the previous name
survives as a secondary alias. Two consequences:

- the repair depends on cloud-init running on every boot, which is a property of
  this image and not something Debra controls. An image without cloud-init, or a
  device with it disabled, keeps the stale alias indefinitely;
- the service cannot assume the file is somebody else's problem. It renamed the
  device and left two consumers of the name behind, and only a reboot or another
  service repaired them.

Defect 2 is the same shape and also self-corrects: `avahi-daemon` starts after
`/etc/hostname` already holds the new name, so at boot it announces the right
one. Both defects are confined to the window between a rename and the next boot —
which is exactly the window a person installing this on a running device sits in.

## Fix

`Nmcli.set_hostname()` now applies the whole identity rather than the hostname
alone: it reads the current name with `hostnamectl --static`, renames, rewrites
the `127.0.1.1` line through a new pure function `hosts_naming()`, and restarts
`avahi-daemon.service` **only when the name actually changed**. The alias write
is in place, so the file keeps its owner, mode and any symlink; a failure in
either the alias write or the responder restart logs a warning and does not fail
the boot, because the name itself is applied and the device works.

Tests: `tests/test_setup_identity.py` (14 cases: file shapes, idempotency, the
restart only on change, invalid names writing nothing, and both failures staying
non-fatal). Full suite: 675 tests, the only two errors are in `control/web/`,
which this change does not touch.

## The fix, verified on the board

The fixed release
(`599cb2b09c91a002a6501622661952416a476373e2e4ab14b8a7de56dcd37fde`) was
installed over the first one; the previous unit was retained at
`/usr/local/lib/debra/setup/previous-units/20261116T045957998733Z.service`, so the
rollback path the installer promises exists on a real device now.

Installing it repaired the file the first release left behind:

```
127.0.1.1 debra-8518d6 debra-8518d6      # was: debra-8518d6 debra-lab
127.0.0.1 localhost
```

Then a **live rename** was forced by writing `debra-renametest` into
`setup.json` and restarting the unit — the same path a first boot would take,
without waiting for a boot:

| After the rename | Result |
| --- | --- |
| `hostnamectl --static` | `debra-renametest` |
| `/etc/hosts` | `127.0.1.1 debra-renametest debra-renametest`, rewritten in the same second |
| `hostname -f` | `debra-renametest` |
| `sudo` | silent, no "unable to resolve host" |
| `debra-renametest.local` from the host | `192.168.0.99`, immediately |
| `debra-8518d6.local` | timed out |
| Wi-Fi | `home` still activated, same address, SSH session survived |

Reverting to `debra-8518d6` reproduced the same result in reverse: alias, `-f`,
`sudo` and mDNS all followed within a second, with no reboot. **Both defects are
now fixed at the moment of the rename rather than at the next boot**, which is
the window a person installing this on a running device actually sits in.

## What tripped during that test: the start limit

The third restart inside five minutes was refused:

```
Job for debra-setup.service failed because start of the service was attempted too often.
```

`StartLimitBurst=3` / `StartLimitIntervalSec=300` is deliberate — a failing portal
must not loop on port 80 — but it applies to maintenance as well as to faults, so
`systemctl reset-failed debra-setup.service` is required before starting the unit
again. That was added to the install section of the
[setup README](../../../control/setup/README.md), because a person iterating on a
device will meet it.

The state file and the device disagreed for those few minutes: `setup.json` said
`debra-8518d6` while the device was still `debra-renametest`, because the service
never ran. Nothing reconciled them automatically — the next start did.

## Addendum after review: the shipped code is not the code this page describes

Added 2026-11-16. The two sections above were written in the same session that
found the defects, and they describe the **first draft** of the fix: a
`hostnamectl --static` change check, an in-place `/etc/hosts` write, and a
responder restart only when the name changed. An independent review rejected that
draft, and the shipped code is different in ways that matter:

| This page says | The code now does |
| --- | --- |
| alias written in place with `open(..., "w")` | staged temp file, fsync, `os.replace` on the resolved path, directory fsync — an interrupted write cannot leave a truncated `/etc/hosts` |
| `127.0.1.1` line rewritten, other names dropped | unchanged in intent, and `127.0.0.1 localhost` is now synthesised when absent, so a truncated file cannot come back unresolvable |
| responder restarted only when the name changed | reconciled on every run, gated on `systemctl is-active` and issued as `try-restart`, so a deliberately stopped responder is not started |
| 14 tests | 25 |
| unit ordered after `cloud-config.service`/`cloud-final.service` | ordered after `cloud-init.service` and `cloud-init-network.service`; the other two are after `network-online.target` and, for `cloud-final`, after `multi-user.target`, which this unit is wanted by — naming them would cycle or delay |

The device evidence above is real, and it verified the **behaviour**: a live
rename repaired the alias, `hostname -f` and `sudo` in the same second, mDNS
followed without a reboot, and the Wi-Fi connection survived. The *mechanism*
verified on the board was the first draft's. The atomic replace and the
unconditional reconcile have run only in tests.

Read [the setup README](../../../control/setup/README.md) for what the shipped
code does. This page is the record of how it was found and what was measured.

## The shipped ordering, verified on the board

The review rejected the first ordering line for a real reason: `cloud-final.service`
is itself `After=multi-user.target`, and this unit is `WantedBy=multi-user.target`,
so naming it is an ordering cycle. The shipped line orders after
`cloud-init.service` and `cloud-init-network.service` instead — the stage that
actually writes `/etc/hosts`, in both cloud-init eras.

Release `b72a508c4eb98be4c713213761fe3a70047017d42bb9c55c8646638f2117279d`
was installed and checked before any boot:

```
$ sudo systemd-analyze verify /etc/systemd/system/debra-setup.service
(no output, exit 0)
$ systemctl list-unit-files 'cloud-init*'
cloud-init-network.service   enabled
cloud-init-main.service      enabled
cloud-init-local.service     enabled
```

Then the board was rebooted and the boot journal read:

| Check | Result |
| --- | --- |
| `Found ordering cycle` | **0** occurrences |
| `cloud-init-network.service` | finished at 18.17 s |
| `debra-setup.service` | started at 24.31 s, `Result=success`, `NRestarts=0` |
| `setup phase online` | 27.88 s |
| Hostname / alias / `hostname -f` | `debra-8518d6` / `127.0.1.1 debra-8518d6 debra-8518d6` / `debra-8518d6` |
| Network | `home` activated, `192.168.0.99` |
| `debra-8518d6.local` | resolves to `192.168.0.99` |

So the shipped ordering is not a cycle on this image, and the unit runs after the
process that owns the file it edits. What this still does not prove is an image
whose cloud-init metadata pins a hostname: cloud-init would then rewrite the alias
to that name *before* Debra runs, and Debra would rewrite it back, which is the
right order but has not been seen.

## Not done

- The onboarding page, the access point, a join performed by Debra, the rename
  by a *first* boot, and a restore from the baseline are all still unexercised.
- The atomic write and the unconditional responder reconcile have not been on a
  board; the rename verification above used the first draft.
- The page's own latency is unmeasured, including the 30-second autoconnect wait
  plus cloud-init's network stage.

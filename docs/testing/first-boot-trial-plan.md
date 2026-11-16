# First-boot trial plan: one card, one Pi, no console

Status: **a plan, not an authorization.** Nothing here has been run. A trial
operates a real radio and a real household network, so it waits for James to
name the Pi and the card and to agree the recovery path below. Until then this
page is the list of what the run would show and what is still missing to make
the run possible.

Why it is worth planning before the card exists: the setup service has never
raised an access point, joined a network, applied a name or captured a baseline.
Every claim in [first boot](../design/first-boot.md) is offline evidence against
a recorded fake NetworkManager. The trial is the first test that can contradict
most of it.

## What one trial can prove, and what it cannot

A single run on one board can prove, for that board and that router:

- that Debra's name is derived, applied, and still there after a reboot;
- that the setup access point is raised when there is no uplink, and that the
  card note names a network and password the phone can actually use;
- that the page is reachable at the address it printed, and that the phone's
  captive-portal probe arrives or does not;
- that a submitted household network is joined, verified by address and default
  route, and that the access point stops and stays down;
- that the first baseline is captured, and what its manifest says;
- that a reboot rejoins the household network without raising the access point.

It cannot prove:

- that a Pi Zero W (ARMv6, 512 MB) behaves the same way — that needs its own run;
- that a second household or router works — SSID encoding, WPA3, hidden networks
  and 5 GHz-only access points are all separate evidence;
- anything about a device whose boot partition never mounted, or whose radio was
  off for want of a country.

## What is missing before the trial can start

The service is installed by an installer that runs **on the device**, as root,
and prepares files only. It does not enable the unit. That means a fresh card
today has no Debra on it. Three routes exist, and only one of them tests first
boot:

1. Boot Raspberry Pi OS Lite with Wi-Fi configured, install, enable, then delete
   the household profile and reboot. **Not a first boot in the sense that
   matters**: NetworkManager has already run with a working uplink, the country
   is already set, and `resume()` may adopt a profile the trial never made.
   Useful only as a smoke test of the page and the installer.
2. Install into a mounted card from a host with
   `python3 -B control/setup/install.py --root /path/to/card --python <card-python>`,
   then create `/etc/systemd/system/multi-user.target.wants/debra-setup.service`
   as a symlink to `../debra-setup.service`. The rendered unit names
   `/usr/local/lib/debra/setup/releases/<id>/install.py`, which is where the
   `--root` install puts it on the card, so the paths agree once booted. The
   README describes `--root` as "only useful for inspection or imaging"; this is
   the imaging case, and **neither the symlink nor the boot has been tried**.
   This is the only route that reaches the real first boot, and it is itself part
   of what the trial would test.
3. Build a distributable image. Does not exist. No Debra image has been built,
   nothing generates device identity in one, and there is no image release path.

Route 2 is the smallest honest step. It should not be described as supported
until it has worked once, which is why the trial's first pass/fail is "the
service runs at all".

## Prerequisites

- A named Pi and a named microSD card, and James's agreement for this run. The
  card is expected to be overwritten; nothing on it is evidence.
- Raspberry Pi OS Lite, version recorded at the time of the run, written with
  Raspberry Pi Imager.
- A phone that can join a WPA2 network and shows a captive-portal sheet.
- A recovery route that does not depend on Debra working. Any of:
  - a USB-TTL serial cable on the UART (best: it shows the boot log even when
    nothing else does);
  - HDMI and a USB keyboard.
- A household Wi-Fi name and password for the trial. **These never go into Git,
  a note, a screenshot or a support bundle.** The trial record names the
  network only as, for example, "the household 2.4 GHz network".

## Recovery, before anything is flashed

Written down because the whole point of the setup network is that a beginner has
no console, and the trial is where that is still false:

- **The page never appears.** Use the serial console or keyboard. `systemctl
  status debra-setup`, `journalctl -u debra-setup -b --no-pager`. The journal
  names the phase and, for the access point, the address it bound.
- **The access point is up but the phone will not join.** Re-read
  `/boot/firmware/debra-setup.txt` from the card or over SSH: the password is
  stable across reboots, so a password read after a reboot is still correct.
- **The device joined a network that cannot be reached.** Stop the unit
  (`sudo systemctl stop debra-setup`), and remove the profile:
  `sudo nmcli connection delete <id>`. The stale state is in
  `/var/lib/debra/setup/setup.json`; deleting that file is the reset, and it
  costs only the recorded attempt history and the setup-network password.
- **The whole run must be abandoned.** Re-flash the card. Do not try to repair
  the trial in place and then record a result from it.

## Run sheet

Each step records what was observed, not what was expected. A failed step stops
the run and is itself the result.

| # | Action | Observation to record | Passes when |
|---|---|---|---|
| 0 | Flash Route 2 onto the card, boot the Pi with no Ethernet | Serial/HDMI output; does `debra-setup` start | The unit is active and the journal names a phase |
| 1 | Read `/boot/firmware/debra-setup.txt` from a card reader afterwards, or over the console | File present, name, password length | The file names `Debra-Setup-<serial>` and a password |
| 2 | From the phone, look for the setup network and join it | SSID seen, security type shown by the phone, password accepted | The phone associates |
| 3 | Let the phone sit for 30 s | Does a "sign in to network" sheet appear by itself | Recorded either way; absence is the DNS question, not a bug in the page |
| 4 | Open the page at the address on the card note | Page loads, device name, network list | The page renders and names this device |
| 5 | Record the country step | Asked, adopted from the device, or missing | Recorded; a missing country with a dead radio is the known gap |
| 6 | Submit the household network | Handover card appears before the page goes away | The handover renders while the phone is still on the setup network |
| 7 | Wait, then reconnect the phone to the household network | `http://<name>.local:8787/` or the address, `ss -ltn 'sport = :80'` on the device | Port 80 is closed, the access point is gone |
| 8 | Check the state and the baseline | `sudo cat /var/lib/debra/setup/setup.json` (strip the password before quoting), `ls /var/lib/debra/setup/baseline/`, `cat` the manifest | Phase `online`, a manifest whose archive hash matches |
| 9 | Reboot | Does the access point return; is the name the same; is the baseline still there | No access point, same name, same baseline |
| 10 | Deliberate failure: boot with a wrong household password | The access point returns, the page says why, the same password still works | The retry path works with the password already saved by the phone |
| 11 | Power cut during step 6 | After the reboot, is the device usable without console help | The device admits a new submission (the r4 lockout, on real hardware) |

Steps 10 and 11 are the ones that cannot be tested anywhere else, and both are
recoveries a real person would depend on.

## Evidence to keep

Sanitized: the journal for the boot that ran the service, `nmcli -f all device
show wlan0`, the state file with `hotspot_password` and any SSID replaced, the
baseline manifest with paths kept but names generic, `ss -ltn`, and a phone
photo of each screen. The result record goes in
[`results/`](results/) with the date, the board, the image version, the exact
commands, and an explicit list of what was not observed.

## To have human confirm

- Whether the card-reader route (Route 2) and its wants symlink are acceptable
  as the trial mechanism, or whether the image build comes first.
- Whether the trial may use the real household network, or a dedicated test
  network with a separate access point. A test network isolates the run from a
  household that is currently working; it also means the trial has never been
  run against the real router.
- Whether a wrong-password attempt (step 10) is acceptable on the household
  access point, and how many attempts.

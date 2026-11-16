# The Zero 2 W joins the household network, and SSH works

**2026-11-15/16 — first successful join of the first Debra test board.** The
board is on `Oldiges WiFi`, reachable at `192.168.0.99` as `debra-lab.local`,
with key-only SSH. The join followed the
[WPA2-only downgrade of the SSID](../../notes/2026-11-15-wlan-wpa2-downgrade.md), which is
the change that made it possible.

Author: OpenCode session, `openrouter/deepseek/deepseek-v4.1-flash-1017`, variant
not exposed by the host. Host: Fedora. Debra baseline `5fa8948`. Board: Pi Zero 2
W, `wlan0` `2c:cf:67:87:7b:f9`; Seeed 2-Mics HAT v1 fitted, unused in this test.

## What was done

James reflashed the card, joined the network at the console after the SSID
change, and the board appeared on the LAN. The joining command was the one the
session gave him, so the profile is **`home`**, created by
`nmcli device wifi connect` — not by cloud-init and not by Debra.

## Observed

| Check | Result |
| --- | --- |
| mDNS | `debra-lab.local` → `192.168.0.99` |
| ICMP | 2/2, 16 ms average |
| TCP 22 | open; server offered `publickey,password` |
| Key login | `debra@debra-lab` with `~/.ssh/id_ed25519` (james@framework-w11), after the public key was appended to `authorized_keys` |
| Active profile | `home`, type `wifi`, device `wlan0`, **activated** |
| Scan | `Oldiges WiFi` advertised as **WPA2** only |
| Clock | `NTPSynchronized=yes`, `Mon 16 Nov 04:34 UTC 2026` — real time, so an uplink exists |
| Route | `1.1.1.1 via 192.168.0.1 dev wlan0 src 192.168.0.99` |

Device facts, for later comparisons: `Linux 6.18.50+rpt-rpi-v8 aarch64`, Debian
GNU/Linux 13 (trixie), 415 MiB usable RAM, `/` 2.3 G used of 28 G, static
hostname `debra-lab`. `python3`, `iw`, `raspi-config`, `nmcli` and
`/boot/firmware` are all present, which is what `control/setup/` requires.
`sudo` needs a password; James holds the lab credential and it is deliberately
not recorded in this repository.

## The `wpasupplicant` version question, answered against what was claimed

The board carries **`wpasupplicant 2:2.10-24+rpt3`** — the exact version that
[raspberrypi/trixie-feedback#107](https://github.com/raspberrypi/trixie-feedback/issues/107)
names as breaking this board — and it joined without trouble once the AP stopped
offering WPA3.

So the claim made in conversation, that `+rpt3` breaks this board *independently
of the access point's security mode*, is **not supported by this observation**.
What this run does support is the narrower reading that matches
[#7634](https://github.com/raspberrypi/linux/issues/7634): the failure needs a
WPA2/WPA3 **transition** access point, because that is what makes NetworkManager
select SAE on a BCM43430 that cannot complete it. Nothing here establishes what
`+rpt3` changes relative to `2:2.10-24`, and a downgrade of the package was not
needed and was not attempted.

Practical consequence: do not spend a future session pinning `wpasupplicant` to
fix a join failure until the AP is known to be WPA2-only. The cheap test is the
`SECURITY` column of `nmcli device wifi list`.

## The Imager-Wi-Fi path is still broken, and this run did not test it

The working profile came from a console `nmcli` command. Cloud-init's own Wi-Fi
has still never connected on this image, and the reason recorded in the
[first-boot note](2026-11-15-zero2w-first-boot.md) stands unchanged: the netplan
renderer is selected and `cc_netplan_nm_patch` is absent. This board therefore
does not yet tell us whether Debra's own approach works — the setup service
writes a NetworkManager keyfile directly rather than going through netplan, and
that is the untested shape.

## Left behind on the boot partition

The card is the flash from 15:17 (`instance-id: rpi-imager-1794791822499`), and
its seed files are still in place: `user-data`, `meta-data`, `network-config`.
No `[REDACTED]` mask is present this time.

The household passphrase from the Imager Wi-Fi section **is still in clear on
that FAT partition**, where anyone holding the card can read it. cloud-init has
already consumed this instance, so removing the three files is safe and is a
pending cleanup, not a functional change. It was not done because the board went
off the network before the cleanup.

That is also a live precedent for Debra's own design: the setup service writes
the *setup network's* password to `/boot/firmware/debra-setup.txt` for the same
reason (a person has to be told it), so "a credential on the boot partition" is
a property of the design, not only of this flash.

## Not done

- `control/setup/` was **not** installed. `install.py` was read, the payload was
  confirmed self-contained (12 files, 187 kB, clean in the working tree), and the
  device prerequisites were checked — then the board left the network.
- No unit enabled, no service run, no baseline captured, no onboarding page
  served, no rename exercised.
- The SSH host key was accepted on first use into an ephemeral
  `/tmp/opencode/known_hosts_zero2w`; its fingerprint was not recorded, so the
  next session will accept a new host key again.

## Next

1. Power the board at the lab bench, confirm it rejoins `home` unattended — that
   is itself the first evidence about autoconnect surviving a power cycle.
2. Install: `sudo python3 -B control/setup/install.py --python "$(command -v python3)"`
   from a checkout on the device, then `daemon-reload` and `enable --now`.
3. Verify the **online** path: unit `inactive (dead)` with `status=0/SUCCESS`,
   journal `setup phase online`, nothing listening on port 80, `setup.json`
   written, baseline adopted or captured.
4. The captive portal still needs the Zero W v1.1 with no profile at all; a board
   that already has `home` will never raise the access point.

# The Zero 2 W's first boot: the seed ran, the Wi-Fi did not

**2026-11-15 — one boot, executed, no console.** James flashed the card, powered
the board and reported no device on the Wi-Fi. The card was mounted afterwards
and its logs read. The seed worked; the join failed, and the reason is a missing
Raspberry Pi cloud-init module rather than anything Debra wrote.

Author: OpenCode session, `openrouter/deepseek/deepseek-v4.1-flash-1017`, variant
not exposed by the host. Host: Fedora. Debra baseline `ce630e5`. Board: Pi Zero 2
W, `wlan0` at `2c:cf:67:87:7b:f9`; Seeed 2-Mics HAT v1 fitted but unused. Image:
Raspberry Pi OS Lite 64-bit, reference 2026-10-06, Debian 13.7; cloud-init 25.2.
The [card inspection](2026-11-15-zero2w-card.md) is the companion record.

## What the boot did

| Stage | Time (board clock) | Result |
| --- | --- | --- |
| `init-local` | 00:27:58, up 28 s | DataSourceNoCloud from `file:///boot/firmware` — the seed was found; no mount race |
| `init` | 00:28:23, up 53 s | account, `write_files`, hostname |
| `modules:config` | 00:28:57, up 87 s | packages, runcmd |
| `modules:final` | 00:29:02, up 92 s | finished 00:30:44, up 194 s |
| Cloud-init verdict | — | `errors: []`, `result.json` empty of errors |

The clock stayed at the fake image time (`2026-10-06 00:2x` UTC) through the whole
boot, which is itself evidence: systemd-timesyncd never reached a server, because
there was never an uplink.

Everything Debra depends on arrived:

- `debra:x:1000:1000:Raspberry Pi OS:/home/debra:/bin/bash` — the
  `userconf-pi` rename path, as predicted in the card inspection.
- `/etc/hostname` still `debra-lab` (the setup service is not installed, so
  nothing renames it yet).
- `debra-wifi.nmconnection` written at 00:28:05 by `write_files`, `257` bytes,
  mode `[600]`, ownership changed to `0:0`.
- The empty `ssh` marker was consumed: `sshswitch.service` enabled SSH, and the
  `runcmd` `systemctl enable --now ssh` also ran.

## The failure

```
Passwords or encryption keys are required to access the wireless network 'Oldiges WiFi'.
Warning: password for '802-11-wireless-security.psk' not given in 'passwd-file' and
nmcli cannot ask without '--ask' option.
Error: Connection activation failed: Secrets were required, but not provided
Hint: use 'journalctl -xe NM_CONNECTION=6d1f4c6a-2b7e-4c1e-9a3d-5f0b8c22d001 + NM_DEVICE=wlan0
```

The connection UUID in the hint is the keyfile's, so NetworkManager loaded the
profile and then found no `psk` in it. The file was not at fault: it is
byte-for-byte what the generator produced (257 bytes), and loading those same
bytes through GLib returns `key-mgmt=wpa-psk` and a `psk` of the expected length.
The discrepancy is in NetworkManager's read path, not the card.

## Why the seed's own Wi-Fi never had a chance

```
distros[DEBUG]: Selected renderer 'netplan' from priority list: ['netplan', 'network-manager']
modules.py[WARNING]: Could not find module named cc_netplan_nm_patch
```

Debian's `/etc/cloud/cloud.cfg` puts netplan first, `python3-netplan` is
installed, and Raspberry Pi OS therefore renders the Wi-Fi through netplan — while
`NetworkManager.service` is the only manager enabled and `systemd-networkd` is
not. Pi OS's own configuration expects a module called `cc_netplan_nm_patch` to
bridge that; **nothing in the image ships it**, and a repository-wide search of
the root filesystem finds the name only in `etc/cloud/cloud.cfg`. This is the
OS-side half of the [N06](../../roadmap.md) report, and it is a missing module,
not the FAT-vs-cloud-init mount race that the roadmap recorded as the suspect.

By the end of the boot `/etc/netplan/` held two files named
`90-NM-<uuid>.yaml` (UUIDs `200cb0fd…` and `75a1216a…`, neither the keyfile's),
which suggests something still mirrors NetworkManager connections back into
netplan. What wrote them, and whether they later override a keyfile, is unproven.

## My own mistake, recorded

`runcmd` ran `nmcli connection reload && (nmcli connection up id 'Oldiges WiFi' || true)`.
The `|| true` swallowed the failure, so cloud-init reported a clean run while the
join had failed. A deliberate fallback in a diagnostic path is now known to hide
exactly the evidence the next round needed. Do not swallow activation errors.

## Consequences for Debra

- First-boot Wi-Fi via Imager-style cloud-init is **not** a usable path on this
  image, and Debra's own plan (write a NetworkManager keyfile) is the right shape
  but did not activate on this first attempt.
- The setup service's premise is unaffected: it uses `nmcli` against
  NetworkManager directly rather than cloud-init. That remains unproven on a
  device, and the keyfile question above matters to it, because the service
  writes the household profile the same way.
- A device with no uplink produced no persisted journal (`/var/log/journal` has no
  files), so a headless failure leaves only cloud-init's own logs. Any diagnostic
  run on a board without a console has to capture its evidence during that boot,
  to a partition the host can read.

## Pending

A diagnostic boot (`instance-id: debra-diag-1`) re-attempts the keyfile
activation and then lets NetworkManager create the profile itself with
`nmcli device wifi connect`, dumping the journal, both keyfiles and the netplan
state to `/boot/firmware/diag.txt`. Its result decides whether the radio and
passphrase are sound and the keyfile format is the problem, or the join fails for
an unrelated reason.

---
title: Assigning a unique device identity on first boot (Raspberry Pi appliance image)
date: 2026-11-15
type: project-learning
status: unreviewed
task: N02 (research input only; no task claim taken)
author: OpenCode agent
author_model: openrouter/deepseek/deepseek-v4.1-flash-1017
author_variant: unknown
sources:
  - systemd 262, machine-id(5), systemd-firstboot(1), systemd.unit(5), hostname(5), hostnamectl(1), systemd.network(5), networkd.conf(5), systemd-machine-id-setup(1), systemd-machine-id-commit.service(8) — https://www.freedesktop.org/software/systemd/man/latest/ (checked 2026-11-15)
  - systemd project, "Safely Building Images" — https://systemd.io/BUILDING_IMAGES (checked 2026-11-15)
  - systemd source, src/shared/machine-id-setup.c and src/libsystemd/sd-id128/id128-util.c — https://github.com/systemd/systemd/tree/main/src (checked 2026-11-15)
  - Raspberry Pi documentation, OTP register and bit definitions; revision codes; configuration reference (firmware parameters); network boot; getting started/install; find your IP address — https://github.com/raspberrypi/documentation/tree/master/documentation/asciidoc (checked 2026-11-15)
  - RPi-Distro/pi-gen, stage2/01-sys-tweaks/01-run.sh and export-image/05-finalise/01-run.sh, master 6e3ff62 — https://github.com/RPi-Distro/pi-gen (checked 2026-11-15)
  - RPi-Distro/raspberrypi-sys-mods, regenerate_ssh_host_keys unit, imager_custom, debian/rules, commit 51125c7 — https://github.com/RPi-Distro/raspberrypi-sys-mods (checked 2026-11-15)
  - RPi-Distro/raspi-config, do_hostname(), do_ssh() — https://github.com/RPi-Distro/raspi-config (checked 2026-11-15)
  - raspberrypi/rpi-imager, src/customization_generator.cpp — https://github.com/raspberrypi/rpi-imager (checked 2026-11-15)
  - OpenSSH portable, sshd.c and sshconnect.c; ssh-keygen(1) — https://github.com/openssh/openssh-portable and https://man.openbsd.org/ssh-keygen.1 (checked 2026-11-15)
  - Avahi, avahi-daemon main.c, avahi-common/alternative.c, avahi-core/domain-util.c, avahi-daemon.conf(5) — https://github.com/avahi/avahi (checked 2026-11-15)
  - Debian packages: openssh-server 9.2p1-2+deb12u10 (bookworm) and 10.0p1-7+deb13u4 (trixie), systemd 252.39-1~deb12u2 — https://packages.debian.org/ (inspected from the .deb archives in /tmp/opencode/debs, 2026-11-15)
  - RFC 6762 (mDNS), RFC 2132 (DHCP options), RFC 1123, RFC 1035 — https://www.rfc-editor.org/ (checked 2026-11-15)
  - NetworkManager reference, settings-ipv4 and settings-ipv6 — https://networkmanager.dev/docs/api/latest/ (checked 2026-11-15)
  - Repository: docs/design/device-discovery.md, docs/roadmap.md (N02, I02), docs/guides/getting-started.md, AGENTS.md (read 2026-11-15)
supersedes: []
---

# Assigning a unique device identity on first boot (Raspberry Pi appliance image)

## Summary

Three different things are usually called "the device ID", and most of the
confusion in this area comes from mixing them:

1. **The installation identity** — `/etc/machine-id`, 128 random bits written by
   the OS at install or first boot. Unique per *installation*, replaced by a
   reflash, and identical on every card if it is baked into an image.
2. **The board identity** — the OTP serial number (and the firmware's
   `rpi-machine-id`, a hash of the serial and, on Pi 4/5, the factory Ethernet
   MAC). Programmed once at manufacture. It survives a reflash of the card and is
   unaffected by which card is installed, because it belongs to the board rather
   than the installation.
3. **The name people see** — `/etc/hostname`, which becomes the `.local` mDNS
   name through Avahi and the DHCP option-12 host name through NetworkManager.

A clone-safe appliance needs the name derived from (2), never from (1), and needs
SSH host keys regenerated on the device under a rule that does not accidentally
depend on (1). Raspberry Pi OS and pi-gen already do more of this than is
commonly assumed, but the pieces are version-dependent and the guarantee breaks
silently if an image is built with a *populated* `machine-id`.

Limitation up front: **nothing in this note was tested on hardware.** There was
no device contact, no flash and no installation. Every statement is a reading of
upstream documentation, upstream source, or Debian package contents; the only
arithmetic is labelled `computed`. Section 5 lists what a real Pi has to prove
before any of this is called working.

`docs/design/device-discovery.md` already records that a machine-id hash cannot
be a stable device ID; this note supplies the mechanisms behind that conclusion
and adds one it does not cover — that a baked machine-id also disables the
first-boot host-key regeneration on current Raspberry Pi OS.

## Label legend and source register

| Label | Meaning |
| --- | --- |
| `documented` | Stated in upstream documentation or a man page (task label D). |
| `source` | Read directly in upstream source code or a shipped unit/script (also D, but not prose). |
| `reported` | Plausible and widely repeated, but I found no upstream statement (task label R). |
| `hypothesis` | My inference; not stated upstream, not tested (task label U). |
| `unknown` | Not established either way (task label U). |
| `computed` | Arithmetic on the scheme in this note, not an external claim. |
| `tested` | Observed on hardware by me. **No row in this note is `tested`.** |

| Key | Source (full URL) |
| --- | --- |
| S1 | machine-id(5), systemd 262 — https://www.freedesktop.org/software/systemd/man/latest/machine-id.html |
| S2 | systemd-firstboot(1) — https://www.freedesktop.org/software/systemd/man/latest/systemd-firstboot.html |
| S3 | systemd.unit(5), `ConditionFirstBoot=` — https://www.freedesktop.org/software/systemd/man/latest/systemd.unit.html |
| S4 | hostname(5) — https://www.freedesktop.org/software/systemd/man/latest/hostname.html |
| S5 | hostnamectl(1) — https://www.freedesktop.org/software/systemd/man/latest/hostnamectl.html |
| S6 | systemd.network(5), `IPv6StableSecretAddress=` — https://www.freedesktop.org/software/systemd/man/latest/systemd.network.html |
| S7 | networkd.conf(5), `DUIDType=` — https://www.freedesktop.org/software/systemd/man/latest/networkd.conf.html |
| S8 | systemd, "Safely Building Images" — https://systemd.io/BUILDING_IMAGES |
| S9 | systemd, src/shared/machine-id-setup.c — https://github.com/systemd/systemd/blob/main/src/shared/machine-id-setup.c |
| S10 | systemd, src/libsystemd/sd-id128/id128-util.c, `id128_get_product()` — https://github.com/systemd/systemd/blob/main/src/libsystemd/sd-id128/id128-util.c |
| S11 | systemd-machine-id-setup(1) — https://www.freedesktop.org/software/systemd/man/latest/systemd-machine-id-setup.html |
| S12 | Raspberry Pi, OTP register and bit definitions — https://github.com/raspberrypi/documentation/blob/master/documentation/asciidoc/computers/raspberry-pi/otp-bits.adoc |
| S13 | Raspberry Pi, revision codes — https://github.com/raspberrypi/documentation/blob/master/documentation/asciidoc/computers/raspberry-pi/revision-codes.adoc |
| S14 | Raspberry Pi, configuration reference, firmware parameters (`rpi-machine-id`, `rpi-serial64`) — https://github.com/raspberrypi/documentation/blob/master/documentation/asciidoc/computers/configuration/reference.adoc |
| S15 | Raspberry Pi, network boot (MAC programmed at manufacture, not linked to serial on Pi 4+) — https://github.com/raspberrypi/documentation/blob/master/documentation/asciidoc/computers/remote-access/network-boot-raspberry-pi.adoc |
| S16 | Raspberry Pi, getting started / install (Imager hostname character rule, mDNS) — https://github.com/raspberrypi/documentation/blob/master/documentation/asciidoc/computers/getting-started/install.adoc |
| S17 | Raspberry Pi, find your IP address (default hostname `raspberrypi`; Avahi and `.local`) — https://github.com/raspberrypi/documentation/blob/master/documentation/asciidoc/computers/remote-access/find-your-ip-address.adoc |
| S18 | Raspberry Pi Connect, get started (serial number identifies the device; moving the SD card signs out) — https://github.com/raspberrypi/documentation/blob/master/documentation/asciidoc/services/connect/get-started.adoc |
| S19 | pi-gen, stage2/01-sys-tweaks/01-run.sh — https://github.com/RPi-Distro/pi-gen/blob/master/stage2/01-sys-tweaks/01-run.sh |
| S20 | pi-gen, export-image/05-finalise/01-run.sh — https://github.com/RPi-Distro/pi-gen/blob/master/export-image/05-finalise/01-run.sh |
| S21 | raspberrypi-sys-mods, regenerate_ssh_host_keys.service (HEAD) — https://github.com/RPi-Distro/raspberrypi-sys-mods/blob/master/debian/raspberrypi-sys-mods.regenerate_ssh_host_keys.service |
| S22 | raspberrypi-sys-mods, commit 51125c7 (ordering before `sshd-keygen.service`; power-loss rationale) — https://github.com/RPi-Distro/raspberrypi-sys-mods/commit/51125c79618e7f1618ba4413a77bec3a3b1f90ab |
| S23 | raspberrypi-sys-mods, `imager_custom set_hostname` — https://github.com/RPi-Distro/raspberrypi-sys-mods/blob/master/usr/lib/raspberrypi-sys-mods/imager_custom |
| S24 | raspi-config, `do_hostname()` and `do_ssh()` — https://github.com/RPi-Distro/raspi-config/blob/master/raspi-config |
| S25 | rpi-imager, src/customization_generator.cpp (`set_hostname "$IMAGER_HOSTNAME"`) — https://github.com/raspberrypi/rpi-imager/blob/main/src/customization_generator.cpp |
| S26 | OpenSSH, ssh-keygen(1) `-A` — https://man.openbsd.org/ssh-keygen.1 |
| S27 | OpenSSH, sshd.c ("no hostkeys available -- exiting") — https://github.com/openssh/openssh-portable/blob/master/sshd.c |
| S28 | OpenSSH, sshconnect.c ("REMOTE HOST IDENTIFICATION HAS CHANGED") — https://github.com/openssh/openssh-portable/blob/master/sshconnect.c |
| S29 | Debian trixie openssh-server 10.0p1-7, `sshd-keygen.service` (file list; unit read from the .deb) — https://packages.debian.org/trixie/amd64/openssh-server/filelist |
| S30 | Debian bookworm openssh-server 9.2p1-2, `ssh.service` and file list — https://packages.debian.org/bookworm/amd64/openssh-server/filelist |
| S31 | Avahi, avahi-daemon/conf `host-name`, `host-name-from-machine-id` — https://github.com/avahi/avahi/blob/master/man/avahi-daemon.conf.5.xml.in |
| S32 | Avahi, avahi-daemon/main.c (collision path, inotify watches) — https://github.com/avahi/avahi/blob/master/avahi-daemon/main.c |
| S33 | Avahi, avahi-common/alternative.c (`-2` suffix, increment) — https://github.com/avahi/avahi/blob/master/avahi-common/alternative.c |
| S34 | Avahi, avahi-core/domain-util.c (`gethostname`, `strip_bad_chars`) — https://github.com/avahi/avahi/blob/master/avahi-core/domain-util.c |
| S35 | RFC 6762, §9 conflict resolution and §16 character set — https://www.rfc-editor.org/rfc/rfc6762.txt |
| S36 | RFC 2132, §3.14 Host Name option — https://www.rfc-editor.org/rfc/rfc2132.txt |
| S37 | RFC 1123, §2.1 Host Names and Numbers — https://www.rfc-editor.org/rfc/rfc1123.txt |
| S38 | RFC 1035, §2.3.4 Size limits — https://www.rfc-editor.org/rfc/rfc1035.txt |
| S39 | NetworkManager, settings-ipv4 (`dhcp-send-hostname`, default TRUE) — https://networkmanager.dev/docs/api/latest/settings-ipv4.html |
| S40 | NetworkManager, settings-ipv6 (`addr-gen-mode`) — https://networkmanager.dev/docs/api/latest/settings-ipv6.html |
| S41 | Debian systemd versions, bookworm 252.39 and trixie 257.13 — https://packages.debian.org/bookworm/systemd and https://packages.debian.org/trixie/systemd |
| S42 | Debian systemd package: `systemd-firstboot.service` enabled in `sysinit.target.wants`, `ExecStart=systemd-firstboot --prompt-locale --prompt-timezone --prompt-root-password` (unit read from the bookworm .deb) — https://packages.debian.org/bookworm/amd64/systemd/filelist |
| S43 | systemd, src/libsystemd-network/sd-dhcp-duid.c, `dhcp_identifier_set_iaid()` — https://github.com/systemd/systemd/blob/main/src/libsystemd-network/sd-dhcp-duid.c |
| S44 | systemd.journal-fields(7), `_MACHINE_ID=` — https://www.freedesktop.org/software/systemd/man/latest/systemd.journal-fields.html |
| S45 | machine-info(5), `PRETTY_HOSTNAME=` — https://www.freedesktop.org/software/systemd/man/latest/machine-info.html |
| S46 | Raspberry Pi, configuring networking (`nmcli`, `/etc/NetworkManager/system-connections`) — https://github.com/raspberrypi/documentation/blob/master/documentation/asciidoc/computers/configuration/configuring-networking.adoc |
| R1 | Repository, docs/design/device-discovery.md — https://github.com/Joldiges/debra/blob/main/docs/design/device-discovery.md |
| R2 | Repository, docs/roadmap.md, N02 and I02 — https://github.com/Joldiges/debra/blob/main/docs/roadmap.md |
| R3 | Repository, AGENTS.md, "public images must generate their own device identities and SSH host keys" — https://github.com/Joldiges/debra/blob/main/AGENTS.md |

## 1. Stable device identity

### 1.1 What is actually unique, and to what

| Candidate | Unique to | Survives reflash of the same card | Survives moving the card to another board | Source | Label |
| --- | --- | --- | --- | --- | --- |
| `/etc/machine-id` (32 lowercase hex chars, 128 bits) | the OS installation | **No** — regenerated when the image is fresh | **Yes** (it travels on the card) | "usually generated from a random source during system installation or first boot and stays constant for all subsequent boots" [S1] | `documented` |
| OTP serial (32-bit ≤ Pi 4 era, 64-bit on BCM2712) | the SoC/board | **Yes** | **No** — the new board has its own | OTP rows 28/29 (and 31/35 on BCM2712); "All SoCs used by the Raspberry Pi range have a inbuilt one-time programmable (OTP) memory block. A few locations have factory-programmed data" [S12]; shown as `Serial` in `/proc/cpuinfo` [S13] | `documented` |
| `/proc/device-tree/serial-number` | the board | **Yes** | **No** | "The full 64 bit serial number is available in `/proc/device-tree/serial-number`" (BCM2712 section) [S12]; "the normal serial number (`/proc/device-tree/serial-number`)" [S14] | `documented` |
| `/proc/device-tree/chosen/rpi-machine-id` | the board | **Yes** (derived, not stored) | **No** | "A 128-bit machine identifier … generated from a hash of the 64-bit serial number and, on Raspberry Pi 4 and Raspberry Pi 5, the Ethernet MAC address provisioned at manufacture. This provides a stable, unique identity suitable for use in automated or provisioning systems" [S14] | `documented` |
| Ethernet MAC | the board | **Yes** | **No** | "On Raspberry Pi 4 and later flagship models, the MAC address is programmed at manufacture and there is no link between the MAC address and serial number" [S15] | `documented` |
| `/etc/hostname` | whatever wrote it | only if re-derived | only if re-derived | see §3 | `documented` |
| SSH host keys | the installation | **No** (regenerated) | **Yes** — they live on the card and move with it | see §2 | `source` |
| `/var/lib/systemd/random-seed` | the installation | **No** if reset; **shared** if shipped | travels on the card | "Remove … `/var/lib/systemd/random-seed` … every instance will seed its random pool with the same random data" [S8] | `documented` |

Two consequences that matter for the naming scheme:

- The serial is the only identifier here that is **per board, stable across
  reflash, and available before anything is generated on the card**. Raspberry
  Pi's own Connect service treats the board as the identity: "Connect identifies
  your device by its serial number. If you move your microSD card to a different
  Raspberry Pi, the Connect client signs out" [S18].
- `rpi-machine-id` is attractive because it is already a 128-bit hash of the
  same inputs, but it is a *firmware-provided device-tree property*, not the OS
  machine-id, and I found no statement of which firmware versions provide it,
  nor of the hash it uses [S14]. Treat it as a cross-check/diagnostic, not as
  the primary input, until §5 item 8 is run.

`machine-id` and the OTP serial are not interchangeable even though both are
"unique": machine-id(5) says the machine ID "does not change based on local or
network configuration or when hardware is replaced" [S1] — i.e. it deliberately
does **not** follow the board.

### 1.2 Cloning an image with a baked machine-id

machine-id(5) is explicit that this is not a supported configuration: for
"operating system images which are created once and used on multiple machines …
`/etc/machine-id` should be either missing or an empty file in the generic file
system image" [S1]. The systemd image guide repeats it and lists the other
seeded state to reset: "Only when it is reset it will be auto-generated on first
boot and thus be truly unique. If this file is not reset, and carries a valid ID
every instance of the system will come up with the same ID and that will likely
lead to problems sooner or later, as many network-visible identifiers are
commonly derived from the machine ID, for example, IPv6 addresses or transient
MAC addresses" [S8].

What specifically collides, with sources:

| Effect of a shared machine-id | Mechanism | Source | Label |
| --- | --- | --- | --- |
| Every card reports the same DHCP DUID | systemd-networkd's default `DUIDType=vendor` generates the DUID from "hashed contents of machine-id(5)". The IAID is derived separately, from the interface's persistent name or its MAC, so the full DHCPv4 client ID is not necessarily identical — only the DUID is | [S7], [S43] | `documented` + `source` |
| Same IPv6 stable-privacy interface identifier per prefix/interface name (systemd-networkd only) | "an application specific ID generated with the system's machine-ID will be used as the secret key" when `IPv6StableSecretAddress=` is unset | [S6] | `documented` |
| Same value from any `sd_id128_get_machine_app_specific()` use | documented hashing of the machine ID with an app key | [S1] | `documented` |
| **Both `ConditionFirstBoot=yes` units are skipped, so SSH host keys are never regenerated** | "This condition … roughly means that `/etc/` was unpopulated when the system started booting"; a valid ID means "not a first boot" | [S3], [S1], [S21], [S29] | `documented` |
| Shared kernel randomness at first boot, including the entropy pool that key generation draws from | shipped `random-seed`; "possibly generate random data that is more similar to other instances booted off the same image than advisable" | [S8] | `documented` |
| Same journal `_MACHINE_ID` on every card | `_MACHINE_ID=` is "The machine ID of the originating host" [S44], so log entries from different devices carry the same machine identifier | [S44] | `documented` |

Scope note on the IPv6 row: it is a **systemd-networkd** behaviour. NetworkManager —
which the Raspberry Pi OS networking documentation uses throughout (`nmcli`,
`/etc/NetworkManager/system-connections`) [S46] — generates RFC 7217 addresses by
hashing "a host specific key (see NetworkManager(8) manual), the interface name,
the connection's `connection.stable-id` property and the address prefix" — its own
per-installation key, not the machine-id [S40]. So on a NetworkManager image the
IPv6 address consequence is weaker than the DHCP DUID one, and neither is a
substitute for a unique name.

The fourth row is the one this repository has not recorded anywhere: **baking a
machine-id is not just a naming problem, it silently turns off the mechanism
that guarantees per-device SSH host keys on current Raspberry Pi OS.** That is a
security regression disguised as a reproducibility convenience.

Note also that machine-id(5) calls the ID "confidential" and says it "must not be
exposed in untrusted environments, in particular on the network", recommending a
keyed hash for any application-specific use [S1]. Avahi repeats the warning for
its `host-name-from-machine-id` option [S31]. So the raw 32-hex machine-id should
never be the public name either.

### 1.3 Returning an image to first-boot state at build time

Three documented ways, only one of which is right for a golden image:

| Tool | What it does | Use for a golden image? |
| --- | --- | --- |
| pi-gen's own finalise step: `rm /var/lib/dbus/machine-id; echo uninitialized > /etc/machine-id` | leaves the file in the exact state the first-boot logic recognises [S20][S1] | **yes** — this is what Raspberry Pi OS does |
| `systemd-machine-id-setup` | "may be used by system installer tools to initialize the machine ID … at install time, with a provisioned or randomly generated ID" [S11] | only for a single-machine install, not a multi-card image |
| `systemd-firstboot --reset` | "all existing files that are configured by systemd-firstboot are removed" … "This operation ensures that the next boot of the image will be considered a first boot" [S2] | yes, where available — but `--reset` is version 254+, so not on bookworm's 252 [S2][S41] |

The `uninitialized` string is not cosmetic: it is rule 3 in the documented
first-boot rules, and rule 4 says an **empty** `/etc/machine-id` is *not* a first
boot at all [S1]. An image builder that truncates the file instead of writing
`uninitialized` therefore produces a device that will never run a
`ConditionFirstBoot=yes` unit. Label: `documented`.

## 2. SSH host keys on first boot

### 2.1 What the image build already does (pi-gen)

pi-gen — "Tool used to create Raspberry Pi OS images" [S19] — does two relevant
things:

- `stage2/01-sys-tweaks/01-run.sh`: `rm -f "${ROOTFS_DIR}/etc/ssh/"ssh_host_*_key*`
  — the image ships **without** host keys [S19].
- `export-image/05-finalise/01-run.sh`: removes `/var/lib/dbus/machine-id` and
  writes `uninitialized` into `/etc/machine-id` — the image ships in
  first-boot state [S20].

Both are on `master` (32-bit) and `arm64`; I checked both branches' copies of
those two files. So a stock Raspberry Pi OS image is, by construction, in the
good state: no keys, uninitialised machine-id.

### 2.2 What Raspberry Pi OS does at boot (version-dependent)

Current `raspberrypi-sys-mods` (changelog head `1:20260914`) ships this unit,
installed and **enabled** (`dh_installsystemd --name=regenerate_ssh_host_keys`,
no `--no-enable`):

```
[Unit]
Description=Regenerate SSH host keys
Before=first-boot-complete.target ssh.service sshd-keygen.service
After=systemd-remount-fs.service
Wants=first-boot-complete.target
ConditionPathIsReadWrite=/etc
ConditionFileIsExecutable=/usr/bin/ssh-keygen
ConditionFirstBoot=yes
...
[Service]
Type=oneshot
RemainAfterExit=yes
ExecStartPre=/usr/bin/rm -f /etc/ssh/ssh_host_*_key*
ExecStart=/usr/bin/ssh-keygen -A

[Install]
WantedBy=sysinit.target
```
[S21]

So on current images: on first boot, **delete whatever keys are there, then
generate all default types**, before `ssh.service` and before Debian's own
`sshd-keygen.service`. The maintainer's commit message gives the reason and
mentions the power-loss case: "SSH also provides its own ssh keygen service
which only runs `ssh-keygen -A`. Our implementation deals with unexpected power
loss a bit better, so we want to run first. Since `ssh-keygen -A` doesn't do
anything if all the keys are already there, this should be enough." [S22]

The `rm -f` before generation is the part that matters for images: OpenSSH's
`ssh-keygen -A` generates keys "if they do not already exist" [S26], so
`ssh-keygen -A` alone **never removes a key that was baked into an image**.

Older paths, still present in the tree: `raspi-config`'s `do_ssh()` runs
`ssh-keygen -A` when SSH is enabled [S24] (generation only, no delete), and a
standalone helper script `usr/lib/raspberrypi-sys-mods/regenerate_ssh_host_keys`
still exists in the package. Which of these ran on a given release is a
version question — see the matrix in §2.6 and §5.

### 2.3 What Debian's OpenSSH package adds (and when)

| Debian release | `sshd-keygen.service` | Content |
| --- | --- | --- |
| bookworm, openssh-server 9.2p1-2 | **absent** [S30] | `ssh.service` is just `ExecStartPre=/usr/sbin/sshd -t` + `ExecStart=/usr/sbin/sshd -D` |
| trixie, openssh-server 10.0p1-7 | present [S29] | `ConditionFirstBoot=yes`, `ExecStart=ssh-keygen -A`, `Before=ssh.service sshd.service sshd@.service`, `WantedBy=ssh.service …` |

Read from the .deb archives in `/tmp/opencode/debs`. Two observations: the unit is
again gated on first boot, and it does **not** delete pre-existing keys — it only
creates missing ones [S26][S29].

### 2.4 What systemd-firstboot does: nothing for SSH

`systemd-firstboot` initialises exactly these settings: machine ID, locale,
keymap, timezone, hostname, machine tags, kernel command line, root password and
shell [S2]. Host keys are not in the list, and the Debian unit's `ExecStart` only
prompts for locale, timezone and root password [S42]. **Do not treat
`systemd-firstboot` as any part of the host-key story.**

Two related facts worth keeping:

- Debian ships `systemd-firstboot.service` enabled in `sysinit.target.wants`, and
  it is ordered `Before=sysinit.target` with `StandardInput=tty` [S42] (read from
  the bookworm package; the trixie package was not inspected). On a
  headless appliance that only stays harmless because every prompted field is
  already initialised in the image — "If a setting is already initialized, it
  will not be overwritten and the user will not be prompted" [S2]. Ship an image
  with an unset locale/timezone/root password and you get an interactive prompt
  holding up `sysinit.target` on a device with no keyboard. Label: `source` for
  the unit, `hypothesis` for the practical hang (not observed).
- `systemd.machine_id=firmware` does **not** pick up the Pi's
  `rpi-machine-id`. The man page says the firmware value will be used [S1], but
  the implementation's firmware path is `machine_id_from_firmware` → `id128_get_product()`,
  which reads only `/sys/class/dmi/id/product_uuid`, `/proc/device-tree/vm,uuid`
  and `/sys/hypervisor/uuid` [S9][S10]. A Pi has no SMBIOS and does not document
  a `vm,uuid` node, so the call fails and systemd falls through to a random ID
  [S9]. Label: `source` for the lookup list, `hypothesis` for "does nothing on a
  Pi" until §5 item 8 checks `/proc/device-tree/vm,uuid` on the board.

### 2.5 How to actually guarantee no image ships shared host keys

Ordered by strength, all cheap:

1. **Build-time assertion.** Fail the build if the image contains
   `etc/ssh/ssh_host_*_key*`, any `authorized_keys`, any
   `/etc/NetworkManager/system-connections/` profile (those carry Wi-Fi keys and
   can pin a client ID), `/var/lib/systemd/credential.secret` [S8], or a
   non-`uninitialized` `/etc/machine-id`. pi-gen already removes the keys [S19];
   an assertion turns "already removed" into "cannot regress".
2. **First-boot regeneration keyed on a sentinel, not on first-boot state.** The
   current Pi OS unit and Debian's unit both use `ConditionFirstBoot=yes`
   [S21][S29]. That couples key regeneration to machine-id state: commit the
   machine-id (or let `first-boot-complete.target` be reached) while keys are
   missing or half-written, and nothing regenerates them again. A Debra unit
   should instead be: `ConditionPathExists=!/etc/debra/ssh-hostkeys.done`, run
   `rm -f /etc/ssh/ssh_host_*_key*`, `ssh-keygen -A`, verify the expected private
   keys exist, then create the sentinel. Interruption then repeats the whole
   delete-and-generate instead of leaving a mixed set.
3. **Ordering.** `Before=ssh.service ssh.socket` (and before anything that
   consumes the key), plus `After=local-fs.target`. sshd exits if it finds no
   key: "sshd: no hostkeys available -- exiting." [S27].
4. **Runtime evidence, per device.** `ssh-keygen -lf /etc/ssh/ssh_host_ed25519_key.pub`
   on two cards from the same image must differ. There is no way for one device
   to prove fleet-wide uniqueness; only cross-device comparison does that.

The same rule applies to the Debra bearer key and any `authorized_keys`: "Never
put Wi-Fi passwords, private keys, pairing credentials, populated device configs,
or credential-bearing snapshots in Git, example files, public logs, or
distributable images. Public images must generate their own device identities and
SSH host keys." [R3]

### 2.6 Version matrix (what to assume for a given image)

| Image | Keys removed at build | Regenerated at boot by | Gated on first boot | Deletes pre-existing keys |
| --- | --- | --- | --- | --- |
| Pi OS built with pi-gen (either branch) | yes [S19] | sys-mods unit, since release `pios/1 20250929` [S21][S22] | yes [S21] | yes [S21] |
| Pi OS older than that release | yes [S19] | raspi-config `do_ssh()` [S24] and/or the helper script | no (on SSH enable) | helper script: yes |
| Debian trixie + openssh-server 10.0p1 | n/a | `sshd-keygen.service` [S29] | yes | **no** |
| Debian bookworm + openssh-server 9.2p1 | n/a | nothing in the package [S30] | — | — |
| Image with baked machine-id | maybe | **nothing** (`ConditionFirstBoot` false) | — | — |

"Pi OS older than that release" is the weakest row: the helper script and the
`firstboot` init path both exist in the tree, but I could not establish from
public source which one ran on which release. Label: `unknown`; resolve with §5
item 4 (`dpkg -s raspberrypi-sys-mods`, `systemctl cat
regenerate_ssh_host_keys.service` on the device).

## 3. From identity to the name the user sees

### 3.1 The chain

```
/proc/device-tree/serial-number
        │  (Debra identity unit, root, early boot)
        ▼
/etc/hostname  ──►  kernel hostname  ──►  Avahi  ──►  debra-xxxxxx.local   (mDNS)
        │
        └────────►  NetworkManager ──►  DHCP option 12  ──►  router DNS (often debra-xxxxxx.lan)
```

Evidence for each link:

- Avahi takes its name from `gethostname()`, then applies `strip_bad_chars()` —
  truncating at the first dot and keeping only `[A-Za-z0-9-]` [S34]. If the
  result is `localhost` or empty it warns "System host name is set to
  'localhost'. This is not a suitable mDNS host name, looking for alternatives"
  and falls back to the OS name from `/etc/os-release` [S34].
- NetworkManager sends the host name by default: `dhcp-send-hostname` defaults to
  `TRUE`, and "Some DHCP servers use this hostname to update DNS databases,
  essentially providing a static hostname for the computer" [S39]. This holds
  only if NetworkManager is the DHCP client on the image, which the Raspberry Pi
  networking documentation implies [S46] but which should be confirmed on the
  device (`nmcli -f ipv4.dhcp-send-hostname con show …`, or `networkctl` if
  systemd-networkd is in use).
- Raspberry Pi documents the user-visible result: "The default hostname on a
  fresh Raspberry Pi OS install is `raspberrypi`, so by default any Raspberry Pi
  running Raspberry Pi OS responds to `raspberrypi.local`" [S17].
- Imager writes the name the human types at write time into the card:
  `/usr/lib/raspberrypi-sys-mods/imager_custom set_hostname "$IMAGER_HOSTNAME"`
  [S25], and `imager_custom set_hostname` calls `raspi-config nonint do_hostname`
  plus `echo "$HOSTNAME" > /etc/hostname` [S23].

So today, **all cards written from one Imager configuration get the same name**.
Nothing in the OS derives it from the board.

`raspi-config do_hostname` is also the reference implementation to copy: it sets
the hostname via `hostnamectl hostname` (falling back to writing `/etc/hostname`),
then rewrites the `127.0.1.1` line in `/etc/hosts` with `sed`, and flags that a
reboot is wanted [S24]. Skipping the `/etc/hosts` step is the usual cause of
"sudo: unable to resolve host …" — label `reported`, since I did not reproduce it.

### 3.2 Which characters are safe (sources disagree)

| Rule set | Says | Source | Label |
| --- | --- | --- | --- |
| RFC 1123 §2.1 | host names are RFC 952 syntax relaxed so the first character may be a letter **or a digit**; software must handle up to 63 characters | [S37] | `documented` |
| RFC 1035 §2.3.4 | labels ≤ 63 octets, whole name ≤ 255 | [S38] | `documented` |
| systemd hostname(5) | up to **64** 7-bit ASCII lower-case alphanumerics or hyphens, "forming a valid DNS domain name"; strongly recommends a single label; invalid characters "will be filtered out" | [S4] | `documented` |
| systemd hostnamectl(1) | static/transient hostnames "limited to the usually accepted characters of Internet domain names, and 64 characters at maximum" | [S5] | `documented` |
| Raspberry Pi Imager UI | "a name … that includes only letters, numbers, and hyphens" | [S16] | `documented` |
| Avahi | accepts any non-empty single label < 64 bytes (`avahi_is_valid_host_name` only rejects dots/empties), but at runtime strips everything outside `[A-Za-z0-9-]` and truncates at the first dot | [S34] | `source` |
| **RFC 6762 §16** | mDNS names "MUST be encoded as precomposed UTF-8", explicitly *not* restricted to letters/digits/hyphen | [S35] | `documented` |

This is a genuine disagreement, and the safe reading is the intersection:
**`[a-z0-9-]`, starting with a letter, not ending with `-`, one label, ≤ 63
characters, lower case.** RFC 6762 permits far more, but DHCP option 12 defers
character-set questions to RFC 1035 [S36], Avahi silently rewrites what it does
not like [S34], and a browser URL is involved. Underscore is *not* safe in a host
label even though DNS-SD service types use it; capitals survive in Avahi but are
case-insensitive everywhere else, so they only create confusion.

### 3.3 A derivation that satisfies the constraints (proposal, not implemented)

```
serial := contents of /proc/device-tree/serial-number, NUL-trimmed, lower-case hex
id     := first 6 hex chars of sha256("debra-id-v1:" + serial)
name   := "debra-" + id          # 12 characters, e.g. debra-3c6b3f
```

Why this shape:

- **Input.** The serial is the only per-board value available before the card has
  any state [S12][S14], and it is the identifier Raspberry Pi's own services use
  to recognise a board [S18].
- **Hash, not truncation of the serial.** Pi serials are small integers: the
  documented example is `Serial : 00000000765fc593` [S13]. Slicing the serial's
  own hex digits would either collide massively (high-order zeros) or be
  guessable; a hash spreads the bits.
- **Six hex characters** = 24 bits. For a household-sized fleet the collision
  chance is negligible; systemd's own generated-hostname feature notes that
  "collisions follow the birthday bound" and suggests appending characters "for
  extra entropy when uniqueness across a large fleet matters" [S4]. The exact
  probability for a chosen fleet size is arithmetic, `computed`, not a source.
- **Fixed prefix and version string.** `debra-id-v1:` makes the derivation
  explicit and re-implementable. If that string or the length ever changes, every
  device is renamed, so it must be treated as a compatibility constant.
- **Not a credential.** The serial is printed on the board and visible in the
  device tree; a 24-bit hash of it is trivially brute-forceable. Document it as an
  identifier, exactly as `docs/design/device-discovery.md` already requires [R1].

Naming it after the *board* also means: reflash → same name; move the card to a
different Pi → different name. That is a product decision, not a technical
necessity; the alternative (name follows the card) has the opposite trade-off and
is worse here because the card is the disposable part.

Missing-input handling, which N02 explicitly requires ("Cloned machine-id or
literal `unknown` must not generate a fleet of indistinguishable devices" [R2]):

| Situation | Behaviour |
| --- | --- |
| serial present | `debra-<hash>` |
| serial absent, `rpi-machine-id` present | derive from it, log that the primary source was missing |
| both absent | do **not** fall back to a literal `unknown`; use `debra-unassigned-<last 4 of MAC>` and log an error so the condition is visible on the device page and in the journal |
| serial present but malformed (non-hex, empty after trim) | treat as absent |

**The upstream alternative, and why it is the wrong tool here.** systemd 262
added a generated-hostname feature: in `/etc/hostname`, each `?` "is
automatically substituted by a hexadecimal character derived from the
machine-id", and `$` picks a word from a word list, so the documented example
`foobar-????-????` expands to something like `foobar-92a9-061c`; the same page
notes that "collisions follow the birthday bound" and recommends appending
characters when fleet-wide uniqueness matters [S4]. The docs prefer supplying the
pattern through the `firstboot.hostname` credential so it is resolved once and
persisted, rather than leaving it in `/etc/hostname`, where it is "re-evaluated on
every boot" [S4].
Two reasons not to build Debra on it: it is derived from the **machine-id**, so
every reflash renames the device and a cloned image renames every card anyway;
and it does not exist on either current Raspberry Pi OS base — systemd 262 is
newer than Debian bookworm's 252 and trixie's 257 [S41], and the
`firstboot.hostname` credential was added in 261 [S2]. Label: `documented`,
version-scoped.

### 3.4 Setting it: ordering, idempotency, persistence

Proposal (label `hypothesis` until §5 passes):

- A oneshot unit in `sysinit.target.wants`, `ConditionPathExists=!/etc/debra/identity.done`,
  `After=local-fs.target`, `Before=network-pre.target avahi-daemon.service ssh.service`,
  `ConditionPathIsReadWrite=/etc` (mirroring the Pi OS host-key unit [S21]).
- The unit writes `/etc/hostname`, calls `hostnamectl set-hostname`, rewrites the
  `127.0.1.1` line in `/etc/hosts` [S24], then touches the sentinel as its last
  act. Re-running it is harmless because the output is a pure function of the
  serial.
- Because the name is derived and not generated, an interrupted run converges on
  the next boot with the *same* name. That is the main reason to prefer
  derivation over "generate a random ID once and store it": a random scheme that
  is interrupted between generating and persisting produces a different name on
  every attempt, and one interrupted between persisting and marking done risks
  regenerating a name the user has already written down.
- Restart Avahi after the change (`systemctl try-restart avahi-daemon.service`) —
  see the disagreement in §4.4. Do not restart it if it was not running.

The friendly name ("Lab Pi 5") stays out of the hostname. It belongs in
`/etc/machine-info` (`PRETTY_HOSTNAME=` [S45]) or the app's own metadata/TXT
record [`docs/design/device-discovery.md`, R1]; the hostname is identity and must
not be edited by users without accepting that bookmarks and DHCP reservations
break.

## 4. Failure modes

### 4.1 Two devices claiming one name

What is documented vs what is not:

- **mDNS:** the loser of probing "MUST cease using the name, and reconfigure"; the
  recommended action is to add identifying information or append/increment a
  number and probe again [S35]. Avahi implements exactly that: on
  `AVAHI_SERVER_COLLISION` it logs "Host name conflict, retrying with %s" and
  sets the alternative name [S32], where the alternative is `name-2`, or
  `name-<n+1>` if the name already ends in a number [S33]. Result: the device the
  user sees at `debra-3c6b3f.local` may actually be `debra-3c6b3f-2.local`,
  **while `/etc/hostname`, the DHCP host name and the device's own UI still say
  `debra-3c6b3f`.** The rename is runtime-only and is not written back.
- **DHCP/router DNS:** RFC 2132 defines the option and its length but says
  nothing about collisions [S36]; what a router does with two clients claiming
  one name is vendor behaviour, and NetworkManager's description ("some DHCP
  servers use this hostname to update DNS databases" [S39]) does not describe a
  conflict rule. Label: `unknown`; needs §5 item 5.
- **Debra's own advertisement:** the `_debra._tcp` browse shows the `name` and
  `label` from the device's metadata (R1, "As built"), so two devices can present
  identical entries even when mDNS has disambiguated the host names. A
  discovered-device list keyed on the advertised name will show a duplicate.
- **SSH:** two devices behind one name with different keys means the second one
  triggers "WARNING: REMOTE HOST IDENTIFICATION HAS CHANGED!" and, with
  `StrictHostKeyChecking=yes`, a hard refusal [S28]. That is correct behaviour and
  should be surfaced, not suppressed.

### 4.2 Identity that changes after a reflash

| What changes | Consequence | Mitigation |
| --- | --- | --- |
| machine-id | anything derived from it (DUID [S7], app-specific IDs [S1]) changes; a name derived from it would change | do not derive the name from it |
| SSH host keys (by design, §2) | the client's `known_hosts` entry for `debra-3c6b3f` no longer matches the same name → warning/refusal [S28] | tell the user the reflash changes the fingerprint; the name staying stable makes this *more* likely to be hit, so the device page should show its fingerprint |
| the Debra bearer key, if stored only on the card | the browser's saved key stops working after reflash | out of scope here; state it in the reflash procedure |
| Home Assistant / Music Assistant device registry | new device entries, or stale entities for the old one | out of scope here; the reflash procedure has to cover it |

The asymmetry is the important bit: **a stable name plus regenerated keys produces
a host-key warning; an unstable name plus regenerated keys produces a silently
"new" device.** Choose the first, and document the warning.

### 4.3 An interrupted first boot

| Interrupted at | State left behind | Next boot |
| --- | --- | --- |
| before `/etc/machine-id` is committed | file still contains `uninitialized`; the real ID was only bind-mounted [S1] | still a first boot; a **new** random ID is generated [S1][S8] — anything already derived from the old value is now wrong |
| after a name was written, before the sentinel | valid `/etc/hostname` | derived scheme: same name, sentinel created. Random scheme: ambiguous |
| mid host-key generation | some keys present, some missing, no sentinel | current Pi OS: reruns only if still in first-boot state [S21]; Debra sentinel scheme: deletes and regenerates everything |
| after `first-boot-complete.target` with keys missing | not a first boot any more [S8] | Debian's unit and Pi OS's unit will not run [S21][S29]; sshd exits [S27] — this is the concrete reason to key on a sentinel instead |
| before Avahi restarted | mDNS serves the old name until restart | restart step must be idempotent and re-run at boot, or place the rename before Avahi starts |

`first-boot-complete.target` is the documented tool for exactly this: "if the
first boot process is aborted before this target is reached, the following boot
process will be considered a first boot, too" [S8]. But note what it does *not*
buy: it protects first-boot *units*, not the *values* already written, and it
stops protecting anything once reached.

### 4.4 Where the sources disagree

1. **mDNS character set.** RFC 6762 §16 explicitly allows UTF-8 names and says
   the LDH restriction is a legacy assumption [S35]; RFC 1123, systemd, the Imager
   UI and Avahi's runtime filtering all assume LDH [S37][S4][S16][S34]. Follow
   LDH.
2. **"Avahi updates the .local address when the hostname changes."** Raspberry Pi
   documents this [S17]. The daemon source I read takes the name from
   `gethostname()` at startup [S34] and its inotify watches are on its own
   service and configuration directories, not on `/etc/hostname` [S32]. There is a
   D-Bus `SetHostName` method that something could call [S32]. So either some
   Raspberry Pi OS component calls it, or the documentation is describing the
   next boot. Label: `unknown` — test with §5 item 6; until then, restart Avahi
   explicitly after a rename.
3. **Whether the first boot even regenerates keys** depends on the distro release
   (§2.6): bookworm's openssh has no such unit [S30], trixie's does [S29], and
   Pi OS adds its own [S21]. Any claim of the form "Raspberry Pi OS always
   regenerates host keys" is false without a version.
4. **`systemd.machine_id=firmware`** reads as if it would use the Pi's firmware
   ID [S1], but the implementation's lookup list does not include
   `rpi-machine-id` [S10].

## 5. What a real Pi must prove before this is claimed working

None of the following was run. Each is cheap and each can falsify something
above.

1. **Two cards, one image.** Flash the same image to two cards, boot both, and
   compare: `cat /etc/machine-id` (must differ), `hostname` (must differ),
   `ssh-keygen -lf /etc/ssh/ssh_host_ed25519_key.pub` (must differ),
   `ls -l /etc/ssh/ssh_host_*` (must be first-boot timestamps),
   `cat /etc/debra/*.done` if the sentinel design is used.
2. **Reflash one card.** Same board, fresh image: `hostname` must be unchanged,
   `/etc/machine-id` must change, the host-key fingerprint must change, and the
   `ssh` client must produce the identification-changed warning [S28].
3. **Baked-machine-id negative test.** Build one image with a populated
   `/etc/machine-id` and the keys left in place. Boot two cards and confirm the
   keys are *identical* and `systemctl status regenerate_ssh_host_keys` shows the
   condition failed. This proves the §1.2/§2.5 coupling on the actual release.
4. **Which mechanism exists on the release under test.** `dpkg -s
   raspberrypi-sys-mods | grep Version`, `systemctl cat
   regenerate_ssh_host_keys.service`, `systemctl cat sshd-keygen.service`,
   `systemctl is-enabled regenerate_ssh_host_keys.service`. Resolves the
   `unknown` row in §2.6.
5. **Duplicate-name behaviour.** On an isolated LAN (not the household network),
   force two devices to the same hostname and record: Avahi's journal line and
   the resulting `.local` name [S32], whether `avahi-resolve -n` returns one or
   both, and what the router's lease/DNS table shows. Do not do this on the live
   network.
6. **Runtime rename.** With Avahi running, `hostnamectl set-hostname debra-test1`,
   then immediately `avahi-resolve -n debra-test1.local` and
   `avahi-resolve -n <old>.local`. Settles §4.4 item 2.
7. **Hostname characters.** Set names containing an underscore, a dot, capitals,
   a leading hyphen and a 64-character label; record what `hostname`,
   `avahi-resolve` and the router's DHCP table each show. Confirms the
   intersection rule in §3.2 empirically.
8. **Identity sources on each target board** (Pi 5, Pi Zero 2 W, Pi Zero W):
   presence and readability of `/proc/device-tree/serial-number`,
   `/proc/device-tree/chosen/rpi-machine-id`, `/proc/device-tree/vm,uuid`, and
   whether `/proc/cpuinfo` still has a `Serial` line. Also record firmware
   version (`vcgencmd version`) since `rpi-machine-id` availability is
   undocumented [S14]. This also settles whether `systemd.machine_id=firmware`
   could ever work (§2.4).
9. **Interrupted first boot.** Cut power at three points (early boot, during key
   generation, after `first-boot-complete.target`) and confirm the device
   converges to one name and a complete key set within a bounded number of boots,
   with no duplicate name left on the network.
10. **First DHCP lease.** Watch `journalctl -u NetworkManager` and the router's
    lease table on a first boot: does the very first lease already carry
    `debra-xxxxxx`, or is there a lease with the previous/empty name? This tests
    the `Before=network-pre.target` ordering claim in §3.4.

## 6. Handoff

Research input for N02. No task claim taken, no device contacted, no software
installed, no image built, nothing promoted.

### Findings

| # | Claim | Label | Source | Limits |
| --- | --- | --- | --- | --- |
| 1 | machine-id is random per installation and replaced by a reflash | `documented` | https://www.freedesktop.org/software/systemd/man/latest/machine-id.html | — |
| 2 | the serial lives in factory-programmed, write-once OTP memory; exposed at `/proc/device-tree/serial-number` (64-bit on BCM2712) | `documented` | https://github.com/raspberrypi/documentation/blob/master/documentation/asciidoc/computers/raspberry-pi/otp-bits.adoc | docs only, not a board |
| 3 | `rpi-machine-id` is a firmware hash of the serial (+MAC on Pi 4/5) | `documented` | https://github.com/raspberrypi/documentation/blob/master/documentation/asciidoc/computers/configuration/reference.adoc | firmware versions unknown |
| 4 | multi-machine images must ship machine-id missing or empty | `documented` | https://systemd.io/BUILDING_IMAGES | — |
| 5 | pi-gen removes host keys and writes `uninitialized` machine-id | `source` | https://github.com/RPi-Distro/pi-gen/blob/master/stage2/01-sys-tweaks/01-run.sh | both branches; not a release image |
| 6 | current Pi OS deletes then regenerates host keys on first boot, before ssh | `source` | https://github.com/RPi-Distro/raspberrypi-sys-mods/blob/master/debian/raspberrypi-sys-mods.regenerate_ssh_host_keys.service | since `pios/1 20250929` |
| 7 | a baked machine-id disables that regeneration | `documented` | https://www.freedesktop.org/software/systemd/man/latest/systemd.unit.html | logic documented; fleet effect untested |
| 8 | `ssh-keygen -A` never overwrites existing keys | `documented` | https://man.openbsd.org/ssh-keygen.1 | — |
| 9 | bookworm openssh has no keygen unit; trixie ships `sshd-keygen.service` (first boot, no delete) | `source` | https://packages.debian.org/trixie/amd64/openssh-server/filelist | read from the .debs |
| 10 | systemd-firstboot covers machine-id, hostname, locale, keymap, timezone, root password — never SSH keys | `documented` | https://www.freedesktop.org/software/systemd/man/latest/systemd-firstboot.html | — |
| 11 | Debian prompts for locale/timezone/root password before `sysinit.target` on first boot | `source` | https://packages.debian.org/bookworm/amd64/systemd/filelist | skipped when pre-set; stall untested |
| 12 | `systemd.machine_id=firmware` cannot read `rpi-machine-id` | `source`+`hypothesis` | https://github.com/systemd/systemd/blob/main/src/libsystemd/sd-id128/id128-util.c | Pi effect inferred |
| 13 | default hostname is `raspberrypi`; Imager writes the user's chosen name at write time | `documented`+`source` | https://github.com/raspberrypi/documentation/blob/master/documentation/asciidoc/computers/remote-access/find-your-ip-address.adoc | — |
| 14 | Avahi renames a conflict to `-2`/`-<n+1>` at runtime only | `source` | https://github.com/avahi/avahi/blob/master/avahi-common/alternative.c | code only |
| 15 | a safe label is `[a-z0-9-]`, letter first, ≤63 | `documented` (disagreement) | https://www.rfc-editor.org/rfc/rfc1123.txt | RFC 6762 §16 allows UTF-8 |
| 16 | NetworkManager sends the host name as DHCP option 12 by default | `documented` | https://networkmanager.dev/docs/api/latest/settings-ipv4.html | router duplicates unknown |
| 17 | cloned machine-id gives identical DUIDs under networkd's default `DUIDType=vendor` | `documented` | https://www.freedesktop.org/software/systemd/man/latest/networkd.conf.html | networkd only; IAID is MAC-derived |
| 18 | `debra-<6 hex of sha256("debra-id-v1:"+serial)>` is unique per board and stable across reflash | `hypothesis` | §3.3, inputs rows 2–3 | untested |

### Traps

1. **Baking a machine-id** looks like image hygiene and instead disables first-boot
   host-key regeneration, presets and `systemd-firstboot` (rows 6–7).
2. **`ssh-keygen -A` alone is not a guarantee** — it skips existing keys (row 8).
   Only delete-then-generate or a build assertion removes a baked-in key.
3. **Gating regeneration on `ConditionFirstBoot=yes`** (both Pi OS and Debian do)
   leaves missing keys with no recovery once the machine-id is committed.
4. **mDNS and `/etc/hostname` diverge after a conflict** (row 14): the LAN name is
   not the name the device reports.
5. **A dot in the hostname** is silently truncated by Avahi's `strip_bad_chars`.
6. **Stable name + regenerated host keys** guarantees a client-side warning after
   every reflash. Correct, but the reflash procedure must say so.
7. **`/etc/hosts` is not updated** by the hostname change unless done explicitly;
   `raspi-config` does it, so copy that step.
8. **A shipped `random-seed`** gives every card the same starting entropy state —
   precisely around key generation.

### Unknowns and blocked

- Does Avahi pick up a rename without a restart? Docs say yes; the daemon source
  shows no `/etc/hostname` watch. Blocked on a device (§5 item 6).
- Router behaviour with two identical DHCP host names. Blocked; needs an isolated
  LAN (§5 item 5).
- Which host-key mechanism ran on Pi OS releases before `pios/1 20250929` —
  helper script, `firstboot` init or `raspi-config`? Needs `dpkg -s` and
  `systemctl cat` on an image (§5 item 4).
- Availability and hash definition of `rpi-machine-id` per board and firmware.
- `/proc/cpuinfo` `Serial` on Pi 5: documented for the range, unverified for BCM2712.
- Whether `systemd-firstboot` stalls a headless boot when a prompted field is
  unset. Ordered before `sysinit.target`, but unobserved.
- Not researched: how Home Assistant and Music Assistant react to a device that
  returns with a new host key and the same name; whether the `_debra._tcp` browse
  should key on the derived ID instead of the display name.

### One next bounded check

**§5 item 1 on its own**: flash one image to two cards, boot both, and diff
`/etc/machine-id`, `hostname` and `ssh-keygen -lf` fingerprints. It needs two
cards, one board, the image, and no network changes, and it is the smallest test
that falsifies or confirms the core of this note.

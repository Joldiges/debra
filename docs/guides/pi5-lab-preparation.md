# Prepare the first Pi 5 lab device

**Preparation plan, 2026-11-15 UTC; not yet device-tested.** James prioritized
a Raspberry Pi 5 with a ReSpeaker 2-Mics Pi HAT v2 for development. The first
milestone is **stock OS, reliable SSH access, and demonstrated recovery**—not
voice/music installation. Pi 5 results will not establish original Zero W support.

No card has been written, key generated, Pi contacted or driver installed by
this work. Confirm the physical target, media and allowed operations before
following the imaging or on-device stages below. Do not overwrite an existing
working card or key. The [lab/access packets](../roadmap.md#lab-fleet-and-access)
remain open.

## What James needs to confirm first

1. **Hardware:** Pi 5 RAM size, power supply and cooling; a photo of the HAT's
   markings/component layout, with serials or other identifiers covered. Compare
   it with [Seeed's v1/v2 identification picture][revisions]; similar outlines
   are not revision proof. Never fit or remove a HAT while power is connected.
2. **Recovery supplies:** a specifically identified disposable microSD, a spare
   card for a restore rehearsal, and a card reader. Say if any contains data to
   preserve. Also identify space on another machine for a protected card image;
   equal printed card capacities do not guarantee equal usable sizes.
3. **Access:** whether Ethernet is available, and whether a local monitor/keyboard
   is available for first-host verification/recovery. Wi-Fi is possible, but
   enter its credentials locally rather than sending them in chat or Git.
4. **Workstation:** which Linux/Windows machine will run Imager and SSH, and
   whether to use an existing login key or prepare a dedicated one. Do not send
   its private key or an account password. Agent access/sudo authority is a
   separate scope decision, not implied by enabling SSH.

The official [power guidance][power] recommends the 27 W USB-C supply for Pi 5.
That is not a demand to buy one without checking the available supply/load.
Cooling/HAT clearance and spare-media availability remain unverified.

## Stage 1: stock OS and SSH, once the target is agreed

- Use Raspberry Pi Imager on the chosen workstation. Select **Raspberry Pi 5**
  first, then a compatible **Raspberry Pi OS Lite (64-bit)** image. This is the
  proposed lab starting point, not a claim that Pi 5 requires 64-bit or that this
  HAT works with every current kernel. Record the actual image release/date and
  checksum/provenance before writing; no exact image release is selected here.
- Follow the official [Imager procedure][install]. Confirm the destination by
  its identity as well as capacity: **writing erases that selected medium**.
  Configure a distinctive temporary lab hostname, a chosen user, region/time
  settings, and networking if needed. This temporary hostname does not implement
  Debra's future hardware-derived identity helper. Leave optional cloud-remote
  access/enrollment off unless separately wanted.
- In **Customisation → Remote Access**, enable SSH and select **Use public key
  authentication**. Check which public key Imager actually selected; do not
  assume its prefilled key is the intended one. The chosen workstation must
  possess the matching private key. Keep any local account password private;
  SSH-key login and the local account/sudo policy are different settings.
- Prefer Ethernet for the first connection if available. Complete Imager's
  write/verification flow, safely eject, and boot the agreed Pi. Record any
  unexpected first-boot step or Wi-Fi failure rather than applying guessed fixes.
- Verify the Pi's host identity as described below, then confirm key-based SSH,
  actual board/OS/kernel/architecture, hostname/address discovery and reconnect
  after a controlled reboot. Keep operational addresses and fingerprints in
  owner-only `.local/access/`, not a tracked example. Do not change HA, music
  servers or household-router settings to make this test pass.

Do not add overlays or run the legacy ReSpeaker installer during this stage.
If the HAT is not already fitted, leave fitting it for the powered-off hardware
stage; if it is fitted, report that state rather than disturbing it unnecessarily.

## Two different SSH keys

**Your login key** proves you to the Pi. Only its **public** half goes into
Imager/the Pi's authorized login keys. The matching **private** half stays on the
chosen workstation, protected by appropriate permissions and preferably a
passphrase. Do not overwrite an existing key when preparing a new one. The
official [SSH guide][ssh] explains Imager's public-key option.

**The Pi's host key** proves which server you reached. Before accepting the first
SSH prompt, obtain its fingerprint through a trusted local-console path on that
physical Pi. A proposed read-only console check is:

```sh
ssh-keygen -lf /etc/ssh/ssh_host_ed25519_key.pub
```

Compare the Ed25519 fingerprint with the same key type in the workstation's SSH
prompt. If the file is absent or the values differ, stop and investigate. A
network key scan alone does not authenticate the Pi. A reflash **can** change
host keys; a cloned personal recovery image can preserve them. Never dismiss a
changed-key warning or clear the saved key without verifying the reason. See
[`ssh-keygen -l/-f`][keygen] for fingerprint semantics.

Without a local console, agree another trusted first-host verification method
before first login; hostname/IP/controller labels alone are not identity proof.

## Recovery gate before HAT changes

Retain the fresh OS reference, then capture the configured stock baseline to
protected off-device storage using a separately reviewed procedure. Restore it
to the identified spare card and actually check boot, SSH, networking and intended
identities before risking the working card. Treat the backup as credential-bearing.
Do not boot two clones with the same identities on the network simultaneously.

**No verified Debra snapshot/restore command exists yet.** The historical
`backups/*.sh` scripts are not this procedure and must not be used as tests.
An image hash or a successful capture message is not restoration evidence;
same-card rollback is not independent backup. Do not prune or overwrite baselines.

Only after that gate: agree a pinned v2 overlay installation, exact kernel/image,
safe audio levels, configuration rollback and one device owner. [Seeed's v2
guide][hat] names `respeaker-2mic-v2_0` and warns against the old v1 method; its
“latest OS” wording includes a 2024-11-19 note and is **not a current compatibility
matrix**. Its Pi 5 button-demo caveat concerns `RPi.GPIO`; it neither proves nor
disproves the complete audio stack. Removing an overlay line may undo that
specific setting, but is not a substitute for restoring coherent boot/root state.

## Evidence and limits

Author: `openrouter/openai/gpt-6.1-sol#flex-xhigh`; bounded source preparation by
`openrouter/deepseek/deepseek-v4.1-flash-1017#high`. Coordinator re-read the
official Imager/SSH/power sources and Seeed revision/v2 guides on 2026-11-15 UTC.
The OS downloads page returned HTTP 403, so no current image/version claim was
derived from it. The worker's 2026-11-14 date is not the UTC capture date.

The overlay file at research commit `c513c914adb440568a26420592fafa3b9a723e4f`
was inspected as text; it is **not an adopted full-build pin** or a compatibility
test. Current build inputs, exact specimen revision and physical fit remain
unverified. No boot, audio, login, imaging or restoration result is claimed here.
This guide does not close L01/N05/B03 or authorize live operations.

[install]: https://github.com/raspberrypi/documentation/blob/c6a64966af136da21a1e55551c5a395cb6987fce/documentation/asciidoc/computers/getting-started/install.adoc
[ssh]: https://github.com/raspberrypi/documentation/blob/c6a64966af136da21a1e55551c5a395cb6987fce/documentation/asciidoc/computers/remote-access/ssh.adoc
[power]: https://github.com/raspberrypi/documentation/blob/c6a64966af136da21a1e55551c5a395cb6987fce/documentation/asciidoc/computers/raspberry-pi/power-supplies.adoc
[revisions]: https://wiki.seeedstudio.com/how-to-distinguish-respeaker_2-mics_pi_hat-hardware-revisions/
[hat]: https://wiki.seeedstudio.com/respeaker_2_mics_pi_hat_raspberry_v2/
[keygen]: https://man.openbsd.org/ssh-keygen

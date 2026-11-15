# Backing up the lab Pi

**Current scope and historical archive evidence, updated 2026-11-15.**

James clarified that **on-target file-based backup/restore is sufficient now**.
Whole-SD imaging, replacement-media testing and a second backup destination are
deferred, not prerequisites for browser controls or unrelated engineering.
Demonstrate restoration of the files a change affects; do not confuse archive
creation/extraction with a successful device restore.

James reports that changing the supply mostly resolved the instability.
Earlier brownouts remain historical evidence, not a current fault diagnosis.
An undervoltage warning alone should not trigger a reset; extensive Pi-5-only
hardening is not the current priority.

## What is actually at risk

The lab Pi is not reproducible from this repository. `tools/device/lab-pi5/`
records the *intent*, but the device was built by hand and corrected in place:

| On the device | Recorded in the repo? |
| --- | --- |
| Raspberry Pi OS Lite 64-bit Trixie, 2026-10-06, cloud-init Wi-Fi and user | no — an image and a first-boot file |
| linux-voice-assistant at `v1.1.18`, plus a 169 MB Python venv | version yes, built state no |
| Sendspin CLI 9.1.0 and its settings | partly |
| Docker + Music Assistant container, 2.2 GB of images | no |
| Mixer state: `Line DAC` 106, `Line` 3, stored with `alsactl store` | script yes, the stored blob no |
| Journald drop-in, sysctl watchdog, systemd user units, `debra-health` timer | scripts yes, but they were typed in by hand first |
| SSH `40-debra-password.conf` drop-in | no |
| The saved sink volume, WirePlumber default nodes | no |

A reflash therefore costs the entire bring-up, and it is not certain that running
the scripts again reproduces it — several were written *after* the device was
working, from what had already been done by hand.

## Historical power risk and present limits

Earlier sessions observed resets and unclean-shutdown evidence, including an
`EXT4-fs orphan cleanup on readonly fs` log. That is a reason to protect state,
not proof that a card is damaged or every warning will cause a reset. Power loss
can corrupt in-flight writes. Same-card rollback also cannot recover a failed
card; accepting that limitation does not require imaging before every small change.

## What has been taken: a file-level archive

Taken 2026-11-15 over SSH from the running device, into the ignored
`.local/backups/` (mode 0700, never committed):

```
ssh <device> "sudo tar --numeric-owner --one-file-system --acls --xattrs -C / -cf - \
    --exclude=./proc --exclude=./sys --exclude=./dev --exclude=./run \
    --exclude=./tmp --exclude=./var/tmp --exclude=./mnt --exclude=./media \
    --exclude=./var/lib/docker --exclude=./var/lib/containerd \
    --exclude=./var/cache --exclude=./swapfile --exclude=./var/swap \
    --exclude=./home/debra/.cache ." \
  | zstd -3 -T4 -o .local/backups/debra-root-<stamp>.tar.zst
```

| Property | Value |
| --- | --- |
| Size | 1.19 GiB compressed; 4.08 GB (4,081,418,240 bytes) when decompressed |
| Covers | everything on the root filesystem except the exclusions above |
| Does not cover | `/boot/firmware` — **taken separately**, see below |
| Does not cover | Docker images, apt cache, swap, user caches |
| Contains | Wi-Fi credentials from cloud-init and SSH host keys — **private, never commit** |

**This is a file-level copy, not a disk image.** It can supply selected files for
a bounded restoration. Whole-root recovery onto new media would additionally
need a compatible OS/layout, boot/root identity reconciliation and validation.
Blindly unpacking it over a running root is not an approved restore procedure.

### The boot partition, taken separately

`/boot/firmware` is its own 505 MB partition and the root archive deliberately
does not cross into it, so it was taken as a second 64 MB archive. It matters
because it holds the things that make the sound card exist:

| File | Why it matters |
| --- | --- |
| `config.txt` | `dtoverlay=respeaker-2mic-v2_0` under `[all]` — without it there is no `seeed2micvoicec` card |
| `overlays/respeaker-2mic-v2_0.dtbo` | the overlay itself, built by hand from Seeed's repository |
| `cmdline.txt` | root partition UUID and console settings |
| `user-data`, `network-config` | cloud-init: the `debra` user, the SSH key and **the Wi-Fi password** |

Verified by listing the archive: 437 entries including all five of those. The
`dtoverlay` line was checked against the live device rather than assumed, because
an overlay file present but not enabled is exactly the sort of thing a restore
loses silently.


## Deferred media-loss recovery

| | File-level tar (taken) | Offline block image (deferred) |
| --- | --- | --- |
| Needs the card in hand | no | **yes** |
| Proposed recovery, **unproven** | flash fresh OS, then untar — *not yet tried* | write image, boot — *not yet tried* |
| Bootloader, partition table | not included | included |
| `/boot/firmware` | included in the separate boot archive | included |
| Consistency | live files may be caught mid-write | stable when captured offline; application/boot correctness still needs testing |
| Time | minutes over the network | minutes with a reader |

Both recovery cells are **proposals, not procedures**. No restore has been
performed: file selection, the device identities a fresh OS generates, boot
layout and the actual recovery step all remain unvalidated. Treat the table as
what each option *would* need, not as instructions to follow.

An offline image normally needs shutdown and card-reader access. It is an
optional later recovery route, not a present request for James to remove the card.

## What has been verified

The archive was unpacked and the critical files compared with the live device by
SHA-256. All six match exactly:

| File | What it holds |
| --- | --- |
| `etc/systemd/journald.conf.d/50-debra-persistent.conf` | the persistent journal |
| `etc/systemd/system.conf.d/50-debra-watchdog.conf` | the 60 s hardware watchdog |
| `etc/sysctl.d/60-debra-watchdog.conf` | `hung_task_panic` |
| `etc/ssh/sshd_config.d/40-debra-password.conf` | the password-login drop-in |
| `home/debra/.local/bin/debra-health` | the audio-path health check |
| `var/lib/alsa/asound.state` | **the stored mixer state** — `Line DAC` 106, `Line` 3 |

The mixer state is the one that matters most: without it the device boots silent
with every service green, which is the fault that took a whole session to find.

`zstd -t` passes, so what the archive contains is intact. That is **not** the same
as the archive being complete: the frame decompresses to 4.08 GB while the root
filesystem was described as 5.7 GB, and the difference is unexplained. Neither
figure has been reconciled against the device, so do not read a passing test as
"not truncated". Reconcile the sizes, or list the archive and compare entry by
entry, before treating it as a whole-root copy.

## What is still unproven

- **No full restore has been performed.** Files are proven extractable and
  identical; a fresh card booting from them is not.
- **The archive was taken from a running system**, so a few files (logs, the
  journal, anything being written) may be inconsistent. The six files above are
  not written by anything at runtime, which is why they were the ones checked.
- **No second destination has been demonstrated.** The host-held archive is
  separate from the Pi card, but host-disk loss would lose this copy; it is not
  independently backed up. Future on-target snapshots have the further
  limitation that card loss also loses the snapshots.

## Next actions

1. Build bounded on-target file capture/list/verify/restore tooling with explicit
   included paths, exclusions, identity/permission checks and space preflight.
2. Demonstrate restoration of representative selected files and check the affected
   component; preserve originals and failure evidence. Do not run historical
   `backups/*.sh`, which use destructive root-level rsync.
3. For the isolated browser service, use its
   [retained-release/previous-unit rollback](../../control/web/README.md#stop-and-roll-back-without-touching-audio).
   That component-specific path is not proof of whole-device restoration.

Second-destination copies, offline imaging and spare-card boot restoration remain
useful future choices under B05, not blocking work in this scope.

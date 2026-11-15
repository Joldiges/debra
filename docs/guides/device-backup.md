# Backing up the lab Pi

**Why this exists, what has actually been taken, and what has not been proven.**
Written 2026-11-15, the night the device was browned out twice.

James asked why a card image was being pushed. The short answer: **the device has
no backup at all, and the thing most likely to destroy it is the fault already
happening.**

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

## Why the risk is live rather than theoretical

The 5 V rail sags under load. A brownout during a card write is how SD cards die:
the failure is not "the card needs a reboot", it is "the card is now
unreadable", and then there is nothing left to diagnose. The device also hung
once with `EXT4-fs orphan cleanup on readonly fs` in the boot log, which is the
signature of an unclean shutdown.

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
| Size | about 1.1 GB compressed |
| Covers | everything on the root filesystem except the exclusions above |
| Does not cover | `/boot/firmware` — **taken separately**, see below |
| Does not cover | Docker images, apt cache, swap, user caches |
| Contains | Wi-Fi credentials from cloud-init and SSH host keys — **private, never commit** |

**This is a file-level copy, not a disk image.** Restoring it means flashing a
fresh Raspberry Pi OS, then unpacking over the top. That is a longer and less
certain recovery than an image, which is the reason an image is still wanted.

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


## What an image would add, and what it costs

| | File-level tar (taken) | Block image (wanted) |
| --- | --- | --- |
| Needs the card in hand | no | **yes** |
| Restore | flash fresh OS, then untar | write image, boot |
| Bootloader, partition table | not included | included |
| `/boot/firmware` | **missing** | included |
| Consistency | files can be caught mid-write | consistent |
| Time | minutes over the network | minutes with a reader |

An image needs the card out of the Pi and a card reader on the host. That is the
only step here that needs James, which is why the tar was taken first.

## What is still unproven

- **No restore has been performed.** Until the archive is unpacked somewhere and
  the result compared with the device, it is a file, not a backup.
- **The archive was taken from a running system**, so a few files (logs, the
  journal, anything being written) may be inconsistent.
- **It has not been copied off this machine.** A backup on the same disk as the
  work is not a backup of the work.

## Next actions

1. Verify the archive: `zstd -t`, then unpack a few known paths into a scratch
   directory and diff them against the device.
2. Copy the archives to a second location that is not this machine.
3. Image the card when the Pi is next powered down and a reader is available.
4. **Then** test a restore end to end on a spare card. A backup that has never
   been restored is a hypothesis.

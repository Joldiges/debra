---
title: Storage durability for a long-lived Raspberry Pi appliance
date: 2026-11-15
type: project-learning
status: unreviewed
task: B01
author: OpenCode subagent
author_model: deepseek/deepseek-v4.1-flash-1017
author_variant: high
sources:
  - Raspberry Pi Ltd, "Making a more resilient file system", white paper RP-003610-WP, release 3, build 2026-08-07 — https://pip.raspberrypi.com/documents/RP-003610-WP (checked 2026-11-15)
  - Raspberry Pi documentation, "Power supply warnings" and "SD Cards / Specifications" — https://www.raspberrypi.com/documentation/computers/raspberry-pi.html and https://www.raspberrypi.com/documentation/accessories/sd-cards.html (checked 2026-11-15)
  - systemd, journald.conf(5), systemd 262 — https://www.freedesktop.org/software/systemd/man/latest/journald.conf.html (checked 2026-11-15)
  - Linux kernel documentation, "Journal (jbd2)" — https://docs.kernel.org/filesystems/ext4/journal.html (checked 2026-11-15)
  - Linux kernel documentation, "ext4 General Information" — https://docs.kernel.org/admin-guide/ext4.html (checked 2026-11-15)
  - Linux kernel documentation, "ext4 Disk Layout / Superblock" — https://docs.kernel.org/filesystems/ext4/super.html (checked 2026-11-15)
  - Linux kernel documentation, "zram: Compressed RAM-based block devices" — https://docs.kernel.org/admin-guide/blockdev/zram.html (checked 2026-11-15)
  - e2fsprogs 1.47.4, e2fsck(8) — https://man7.org/linux/man-pages/man8/e2fsck.8.html (checked 2026-11-15)
  - util-linux mount(8) as installed on the research host (noatime / relatime / lazytime) — local man page, checked 2026-11-15
  - Cactus Technologies, application note CTWP005 "Write Abort Handling" — https://www.cactus-tech.com/wp-content/uploads/2019/03/CTWP005-WriteAbort-v3.pdf (checked 2026-11-15)
  - Silicon Power Industrial, "SPOR resilient firmware for microSD card" — https://www.silicon-power-industrial.com/support-detail/spor-resilient-firmware-for-microsd-card/ (checked 2026-11-15)
  - M. Zheng et al., "Understanding the Impact of Power Loss on Flash Memory", DAC 2011 — https://cseweb.ucsd.edu/~swanson/papers/DAC2011PowerCut.pdf (checked 2026-11-15)
  - embeddedTS, "Preventing Filesystem Corruption in Embedded Linux" — https://www.embeddedts.com/assets/preventing-filesystem-corruption-in-embedded-linux (checked 2026-11-15)
  - Linux kernel source, drivers/mmc/core/quirks.h — https://github.com/torvalds/linux/blob/master/drivers/mmc/core/quirks.h (checked 2026-11-15)
  - JEDEC JESD84-B51 register table (EXT_CSD is an eMMC register) — https://www.jedec.org/sites/default/files/docs/JESD84-B51.pdf (checked 2026-11-15)
  - congatec AN50 "eMMC Lifetime", DEVICE_LIFE_TIME_EST / PRE_EOL_INFO decoding — https://www.congatec.com/fileadmin/user_upload/Documents/Application_Notes/AN50_eMMC_Lifetime.pdf (checked 2026-11-15)
  - SanDisk, "High Endurance microSD Card" data sheet (05/23) — https://documents.sandisk.com/content/dam/asset-library/en_us/assets/public/sandisk/product/memory-cards/high-endurance-uhs-i-microsd/data-sheet-high-endurance-uhs-i-microsd.pdf (checked 2026-11-15)
  - f3 "Fight Flash Fraud" documentation — https://fight-flash-fraud.readthedocs.io/en/latest/introduction.html (checked 2026-11-15)
  - Docker, "Configure logging drivers" — https://docs.docker.com/engine/logging/configure/ (checked 2026-11-15)
  - BTRFS documentation, "Subvolumes" ("A snapshot is not a backup") — https://btrfs.readthedocs.io/en/latest/Subvolumes.html (checked 2026-11-15)
  - RAUC, "Using RAUC" (slots, mark-good/mark-bad) — https://rauc.readthedocs.io/en/latest/using.html (checked 2026-11-15)
  - raspberrypi/rpi-image-gen, `image-rota` A/B layer documentation — https://raspberrypi.github.io/rpi-image-gen/layer/image-rota.html and release v2.3.0 notes (checked 2026-11-15)
  - Repository: docs/guides/device-backup.md, docs/testing/results/2026-11-15-lab-pi5-silence-and-hang.md, tools/device/lab-pi5/60-watchdog.sh (read 2026-11-15)
supersedes: []
---

# Storage durability for a long-lived Raspberry Pi appliance

## Summary

The card is not one failure mode, it is four: NAND wear, a power cut during a
write, a controller that lies or caches, and outright counterfeit or
out-of-spec media. Raspberry Pi's own white paper is blunt about the first
(`upstream-documented`: SD flash "has a limited write cycle lifetime… This can
be from months to years", and failure "is usually indicated by random file
corruptions"), and the peer-reviewed power-loss measurements say the second is
worse than the in-flight sector alone.

The useful conclusion for Debra is that **the cheapest protections are
behavioural, not filesystem surgery**: bound the unbounded writers (Docker's
default log driver), keep the journal small but *present*, and make application
state survive a torn write. A "filesystem rollback" that works with no user
intervention cannot be `fsck`, and cannot be a snapshot stored on the same card;
it has to be either a bootloader-visible second slot or a restore from verified
media. Everything in §6 is ordered by cost, not by ambition.

Limitation: no device contact was made for this note. Every magnitude in §2 is
unmeasured; the measurement is one `cat` away and is recommendation 1.

This note does not restate what is already recorded about the lab device's
storage — see [device backup](../guides/device-backup.md) (the 1.1 GB file-level
archive, the separate `/boot/firmware` archive, and the unproven restore) and
[silence and hang](../testing/results/2026-11-15-lab-pi5-silence-and-hang.md)
(the `EXT4-fs orphan cleanup on readonly fs` trace, the volatile journal that
hid the evidence, and the supply fault).

## 1. What actually kills cards

| Mechanism | Label | Detail |
| --- | --- | --- |
| NAND program/erase wear | `upstream-documented` | Flash cells tolerate a finite number of erase cycles. Wear levelling spreads them, but "in the end they can still fail… usually indicated by random file corruptions as parts of the SD card become unusable" ([RP-003610-WP](https://pip.raspberrypi.com/documents/RP-003610-WP), §"What is data corruption", checked 2026-11-15). |
| Power loss during a write (write abort) | `upstream-documented` (vendor, industrial media) | "Data losses can only occur when power is unexpectedly removed… during write operations. If the write operation is aborted during flash erase operations, data losses beyond the data pending for write may occur." Controllers with large DRAM caches can lose their own mapping metadata, after which "the only way to recover is to do a low level format" ([Cactus CTWP005](https://www.cactus-tech.com/wp-content/uploads/2019/03/CTWP005-WriteAbort-v3.pdf), checked 2026-11-15). This is a *vendor* describing *industrial* cards; consumer cards are not obliged to behave this well. |
| Power loss corrupting data that was already written | `upstream-documented` (measured) | Measured on MLC: cutting power while programming a *second* page produced bit error rates up to 25–50 % in the *first*, previously successful page — "retroactive data corruption… Flash device datasheets make no mention of this phenomenon" ([DAC 2011](https://cseweb.ucsd.edu/~swanson/papers/DAC2011PowerCut.pdf), checked 2026-11-15). |
| Garbage collection / FTL remap during power loss | `reported` | Third-party embedded vendor: the card's FTL may be relocating an *allocation group* when power drops, and "you can lose up to the allocation groups worth of data… 4MiB on SDHC, SDXC allows up to 64MiB" ([embeddedTS](https://www.embeddedts.com/assets/preventing-filesystem-corruption-in-embedded-linux), checked 2026-11-15). Not reproduced by us. |
| Controller/firmware bugs | `upstream-documented` | The kernel carries per-card quirks for real products, e.g. "Kingston Canvas Go! Plus microSD cards never finish SD cache flush" (cards from 11/2019) and a GIGASTONE model that "never clear Flush Cache bit" ([quirks.h](https://github.com/torvalds/linux/blob/master/drivers/mmc/core/quirks.h), checked 2026-11-15). Cheap cards can also simply ignore a flush. |
| Counterfeit capacity | `upstream-documented` | A fake card reports more capacity than it has; writes past the real end "wrap around and overwrite earlier files, or simply vanish". Only a full write-and-verify test detects it ([f3 docs](https://fight-flash-fraud.readthedocs.io/en/latest/introduction.html), checked 2026-11-15). |
| Temperature | `upstream-documented` | Consumer SanDisk High Endurance: operating −25 °C to 85 °C, storage −40 °C to 85 °C ([data sheet 05/23](https://documents.sandisk.com/content/dam/asset-library/en_us/assets/public/sandisk/product/memory-cards/high-endurance-uhs-i-microsd/data-sheet-high-endurance-uhs-i-microsd.pdf)). A house is not a hostile environment; a Pi 5 SoC at 80 °C is not the card. No Debra measurement exists for card temperature. |
| Low supply voltage | `upstream-documented` | Raspberry Pi: "Low quality power supplies can corrupt storage or cause unpredictable behaviour"; undervoltage is detected below 4.63 V ±5 % and logged ([raspberry-pi.html](https://www.raspberrypi.com/documentation/computers/raspberry-pi.html#power-supply-warnings), checked 2026-11-15). This is the documented cause most relevant to *this* device. |
| Dirty/loose socket, bent contacts | `hypothesis` | Plausible and cheap to rule out by reseating; no source found, no measurement here. |

What is folklore, or at least not what people think:

- **"Rewriting the same file wears one spot."** The host sees logical block
  addresses; the card's FTL remaps them. Raspberry Pi attributes wear to "how
  much data has been written to or, more importantly, erased from the card" —
  i.e. *volume plus erase amplification*, not file identity
  (`upstream-documented`, RP-003610-WP). Treat "same file" as a proxy for
  "same volume of writes", not as a mechanism.
- **"An endurance card cannot fail."** It has a bigger budget, not immunity. A
  forum-reported torture test wrote 70 TB to a 32 GB High Endurance card and it
  still worked (`reported`, [forum thread](https://forums.raspberrypi.com/viewtopic.php?t=347981)) — that is one card, not a guarantee.
- **"Filesystem corruption means the card is dying."** Two different failures.
  Raspberry Pi's paper separates interrupted-write inconsistency (a filesystem
  problem, fixable by journal replay) from media wear (not fixable).
- **"Formatting or defragmenting extends life."** `unknown`. No source found;
  do not claim it.

## 2. Which writes dominate

There is no honest way to answer this for the lab device from a desk. What can
be said is *which writers are unbounded by configuration*, and how to measure
the rest.

The kernel exports a real per-filesystem write counter:
`/sys/fs/ext4/<dev>/lifetime_write_kbytes` (since creation) and
`session_write_kbytes` (since mount) — `upstream-documented`
([ext4 admin guide](https://docs.kernel.org/admin-guide/ext4.html), checked
2026-11-15). Two reads a day apart answer §2 empirically.

| Writer | What it writes | Magnitude | Label |
| --- | --- | --- | --- |
| systemd-journald | Journal objects under `/var/log/journal` (persistent) or `/run/log/journal` (volatile). Batched: `SyncIntervalSec` default **5 min**; CRIT/ALERT/EMERG flush immediately | Bounded by `SystemMaxUse`; the lab device caps it at 64 MB total, 8 MB per file (`tools/device/lab-pi5/60-watchdog.sh`). Volume = bytes actually logged, not the cap | `upstream-documented` (journald.conf(5)) + `observed` (repo config) |
| Raspberry Pi OS default journal | Pi OS ships `Storage=volatile` in `/usr/lib/systemd/journald.conf.d/40-rpi-volatile-storage.conf`, i.e. **zero** card writes and zero crash logs | 0 bytes, and no evidence after a hang — exactly what happened on 2026-11-15 | `observed` (repo) + `upstream-documented` (RP-003610-WP) |
| Docker container logs | Default driver is `json-file` **with no log rotation**; Docker's own docs warn this "can cause a significant amount of disk space to be used… which can lead to disk space exhaustion" | Unbounded until the disk fills | `upstream-documented` ([Docker](https://docs.docker.com/engine/logging/configure/), checked 2026-11-15) |
| Music Assistant container | Images are 2.2 GB on the device; runtime writes go to the overlay upper dir plus its database | Unmeasured. `estimate`: dominated by library/DB updates and container logs, not by audio streaming (audio is buffered in RAM) | `hypothesis` |
| PipeWire / WirePlumber state | Sink volumes, default nodes, saved on change | Small; event-driven | `hypothesis` |
| `alsactl store` | `/var/lib/alsa/asound.state`; already captured in the device archive | Bytes, on demand | `observed` (repo) |
| Package metadata (`apt`, `dpkg`) | `/var/lib/dpkg`, `/var/lib/apt/lists`, `/var/cache/apt` | Bursty: tens to hundreds of MB per upgrade, near zero otherwise | `estimate` |
| Swap | The lab device uses 2 GiB zram, so swap pages land in compressed RAM | 0 card bytes while zram is the only swap | `observed` (repo/task statement) + `upstream-documented` (zram doc) |
| atime | Kernel default is `relatime`, which writes at most about once per day per file | Small; `noatime` saves little more | `upstream-documented` (mount(8): relatime default since 2.6.30) |
| ext4 journal itself | `data=ordered` writes data before the metadata commit; `data=journal` "roughly doubles the amount of data written to storage for every change" | Multiplier, not a volume | `upstream-documented` (RP-003610-WP) |

Working estimate, clearly labelled: if the device wrote 100 MB/day, a 32 GB card
would see ~36 GB/year — under 1.2 full-card rewrites per year. The entire
question is whether the real number is 100 MB/day or 10 GB/day, and only the
counter in the first row of §6 settles it. Do not quote the 100 MB figure as a
measurement.

## 3. Mitigations and what each costs

Every row states what it removes *and* what it does not. Nothing here is a
recommendation yet; §6 is.

| Mitigation | Protects against | Costs / loses | Does **not** protect against | Label |
| --- | --- | --- | --- | --- |
| journald `Storage=volatile` + `RuntimeMaxUse=` | All journal card writes | **All logs on reboot, including the ones from the crash you are debugging** — Raspberry Pi states this explicitly | Application state, Docker logs | `upstream-documented` |
| journald persistent + small cap + longer `SyncIntervalSec` + rate limit | Unbounded journal growth; keeps crash evidence | A bounded trickle of writes; 64 MB of card | Nothing else | `upstream-documented` |
| Log rotation (journald caps, Docker `local` driver or `max-size`) | Disk exhaustion; unbounded write volume | Docker: the new driver applies only to *newly created* containers | A worn card | `upstream-documented` |
| zram instead of SD swap | Swap traffic on the card | RAM (kernel: no point exceeding ~2× RAM at an assumed 2:1 ratio); OOM behaviour changes under pressure | A memory leak that exhausts zram | `upstream-documented` (zram doc) |
| `noatime` | atime inode writes | Nothing meaningful; slightly breaks tools that rely on atime | Everything else. `relatime` already removes most of this cost | `upstream-documented` (mount(8)) |
| `lazytime` | Inode-table writes on frequent random writes | Timestamps can be lost on power failure; on-disk update deferred | Everything else | `upstream-documented` (mount(8)) |
| App state on tmpfs + periodic flush to disk | Torn/partial state files | Everything since the last flush; needs a flush path that itself uses atomic rename | The OS image | `upstream-documented` (RP-003610-WP) |
| Read-only ext4 root (or `raspi-config` overlayfs with tmpfs upper) | Corruption of the root filesystem | **All root changes are lost at reboot**; needs a separate writable partition for real state; `apt` no longer works normally; the lower layer is still a writable-designed ext4 | `/boot/firmware`, the data partition, the card's wear | `upstream-documented` |
| SquashFS/EROFS immutable root + overlay | Same, plus the image cannot be mutated at all | Build-time image pipeline; no on-device package installs | `/boot`, data partition, wear | `upstream-documented` |
| A/B slots (tryboot / `autoboot.txt`) | An unbootable or broken *system*; gives real rollback | ~2× system partition (rpi-image-gen `image-rota` defaults: 96 MB boot + 512 MB system **per slot**, 1 GB persistent), health-check + mark-good logic, per-slot `/var` and duplicate-UUID constraints | User data, the card, `/boot` corruption in the *active* slot | `upstream-documented` (rpi-image-gen, RAUC) |
| `overlayroot` | Same class as overlayfs | Not verified as packaged for Pi OS trixie — `unknown` | — | `unknown` |
| `commit=` tuning (e.g. 30 s) | Write frequency | More data at risk per power cut | Media wear | `upstream-documented` |
| `barrier=0` / `nobarrier` | Nothing. Raspberry Pi: "Do not disable write barriers" | Destroys the ordering guarantee the journal depends on | — | `upstream-documented` |
| Wear levelling | Spreads erase cycles across the die | You cannot see the result: there is no host-visible wear gauge on SD (§5) | End of life; plan replacement by calendar and by measured writes | `upstream-documented` + `unknown` (gauge) |

Endurance expectations, with the arithmetic shown: SanDisk rates its High
Endurance line in *hours of Full HD recording*, not TBW — 2,500 h at 32 GB,
5,000 h at 64 GB, 10,000 h at 128 GB (`upstream-documented`, data sheet 05/23).
A third party converts that at 26 Mbps ≈ 11.7 GB/h, giving ≈29 TB written for
the 32 GB card (`reported`, derived — SanDisk does not publish TBW). Those
figures assume *sequential video*; a small-file, metadata-heavy workload has
different write amplification, so treat the derived TBW as an upper bound of
sorts, not a promise.

## 4. Power loss

### What ext4 does when the power dies mid-write

- `data=ordered` (default): metadata goes through the journal, and file data is
  forced out *before* the metadata that references it. After replay the
  filesystem structure is consistent; **the file being written may still be
  truncated, empty, or hold stale contents** (`upstream-documented`, both
  [jbd2 docs](https://docs.kernel.org/filesystems/ext4/journal.html) and
  RP-003610-WP).
- `data=journal`: data *and* metadata go through the journal, so the file's
  contents are also recoverable — at "roughly double" the writes, and it
  disables delayed allocation and `O_DIRECT` (`upstream-documented`,
  RP-003610-WP). **It is deprecated with support removal planned for January
  2028** ([ext4 admin guide](https://docs.kernel.org/admin-guide/ext4.html),
  checked 2026-11-15). Designing a ten-year appliance around it is a trap.
- `data=writeback`: faster, and after a crash a file's metadata can point at
  data that was never written, exposing old freed blocks. Raspberry Pi: "Avoid
  `data=writeback` unless you fully understand the risk"
  (`upstream-documented`).
- Below the filesystem: the card may lose more than the in-flight sector (an
  allocation group, per embeddedTS `reported`), may corrupt an already-written
  page (`upstream-documented`, DAC 2011), or may lose its own mapping table and
  stop enumerating (Cactus, vendor `upstream-documented`).

### Practical failure modes with no UPS

1. **Journal replay, nothing visible.** The common case. Journal replays on
   mount; some recently written files are stale or empty.
2. **Runtime remount-read-only.** ext4 defaults to `errors=remount-ro`; on a
   detected inconsistency it stops writing rather than making it worse
   (`upstream-documented`, RP-003610-WP). Services then fail in confusing ways
   while the kernel is healthy. This is the "sshd accepts, never sends a
   banner" shape the lab device already produced.
3. **Unbootable, because of `/boot/firmware`.** It is FAT, it has **no
   journal**, and firmware/config/kernel updates write to it; "a corrupted
   `/boot` partition can prevent the device from booting at all"
   (`upstream-documented`, RP-003610-WP). Read-only root does not cover this.
4. **The card stops enumerating.** Controller metadata loss; no amount of
   filesystem tooling helps, only replacement media.

### What `fsck` can and cannot do

`e2fsck` on a journaled filesystem "will normally replay the journal and exit"
— it restores *consistency*, not *content* (`upstream-documented`, e2fsck(8)).
With `-p` (preen, what boot scripts use) it fixes "any file system problems that
can be safely fixed without human intervention" and exits with code 4 when it
cannot. `-y` answers yes to everything, which on a badly damaged filesystem can
delete what a human would have recovered. Its `-z undo_file` is explicitly
useless here: "The undo file cannot be used to recover from a power or system
crash."

So `fsck` cannot: restore a previous state, recover a file's contents, repair
media, fix a card that will not enumerate, or fix `/boot`'s FAT (that needs
`fsck.fat` and has no journal to replay). It *can* detect and repair metadata
inconsistency, and with `-c` do a read-only bad-block scan.

### What "filesystem rollback" would have to be to be real

"Rollback" implies returning to a *known-good previous state*. Nothing in
`fsck` does that. The three things that can:

| Real rollback | What it actually is | Precondition | Cost |
| --- | --- | --- | --- |
| Bootloader slot switch | A/B root slots, health check, automatic fallback (`tryboot`/`autoboot.txt`); RAUC models this as mark-good/mark-bad | Two system slots, bootloader cooperation, a health signal | ~2× system partition; per-slot `/var`; orchestration |
| Restore from verified media | Write a known-good image or file archive onto the same or a new card | Media access and a *tested* restore | Minutes of downtime; must be rehearsed, not assumed |
| btrfs snapshot rollback | Switch the default subvolume back | The filesystem must still mount, and the snapshot must be intact | btrfs root (not what Pi OS ships), plus: "**A snapshot is not a backup**… if that data is damaged… the snapshot and the original will both be damaged" (`upstream-documented`, [btrfs docs](https://btrfs.readthedocs.io/en/latest/Subvolumes.html)) |

The honest statement for Debra: **"filesystem rollback with no user
intervention" is only achievable as an A/B slot switch**, and even then it rolls
back the operating system, not the user's state. Everything else needs a
bootable recovery path that does not live on the failing card. The project's
current position — a 1.1 GB file-level archive on the host with **no restore
ever performed** — is a *capture*, not a rollback, and
[device-backup.md](../guides/device-backup.md) already says so.

## 5. Detection before failure

| Signal | Real? | Why |
| --- | --- | --- |
| Kernel I/O errors (`I/O error, dev mmcblk0, sector …`) in `dmesg`/journal | **Real, late** | The card or link is already failing. Catches nothing early. |
| ext4 remounting read-only | **Real, late, definitive** | `errors=remount-ro` is the default; the mount becomes `ro` and dmesg says so. A device that keeps doing this is telling you something. |
| ext4 superblock error history: `s_state`, `s_error_count`, `s_first_error_time`, `s_last_error_time`, `s_last_error_func/line` | **Real, survives reboot** | Fields exist in the on-disk superblock (`upstream-documented`, [ext4 superblock](https://docs.kernel.org/filesystems/ext4/super.html)); e2fsprogs shows them via `tune2fs -l` / `dumpe2fs -h`. This is the closest thing to a flight recorder. |
| `metadata_csum` mismatch reports | **Real** | Checksums detect bit rot that journaling cannot; enabled by default by modern `mkfs.ext4` (`upstream-documented`, RP-003610-WP). |
| `badblocks` read-only scan / `e2fsck -c` | **Real, slow** | Block-level only; a clean scan does not prove the card is healthy. |
| Undervoltage entries in the kernel log (below 4.63 V) | **Real, and directly relevant** | `upstream-documented` (Pi docs). On this device it is the documented trigger for the corruption already seen. |
| Card re-enumeration (`mmc0: card … removed` / new card events) | **Real** | Loose socket or a controller resetting itself. |
| `lifetime_write_kbytes` | **Real, but it measures writes, not health** | Answers §2, not "will it die". |
| `/sys/block/mmcblk0/stat` read/write error counters | **Real but noisy** | Retries and recovered errors are included; not a wear metric. |
| A "SD card health percentage" | **Does not exist** | eMMC has `DEVICE_LIFE_TIME_EST_TYP_A/B` and `PRE_EOL_INFO` in EXT_CSD, decoded in 10 % bands (`upstream-documented`, [congatec AN50](https://www.congatec.com/fileadmin/user_upload/Documents/Application_Notes/AN50_eMMC_Lifetime.pdf)). **SD cards have no EXT_CSD** — it is an eMMC register (JEDEC JESD84-B51), and `mmc extcsd read` on a microSD fails (`reported`). Any UI that shows a percentage for an SD card is inventing it. |
| SMART | **Not applicable** | `smartctl` targets ATA/NVMe. A USB card reader may expose a SCSI device, but that describes the bridge, not the card's NAND. `reported`/`unknown` — I found no credible way to read SD NAND health from Linux. |
| "Filesystem is clean" | **Misleading** | It means the last unmount was clean, or that fsck fixed it. Says nothing about media. |

Design consequence: Debra cannot predict card death from the card. It can detect
*consequences* (I/O errors, remount-ro, error counts) and it can measure *dose*
(write volume). Plan replacement on dose and calendar, and make recovery not
depend on the card being readable.

## 6. What Debra should do — cheapest first

| # | Change | Protects against | Does not protect against | Cost |
| --- | --- | --- | --- | --- |
| 1 | **Measure, don't guess**: read `/sys/fs/ext4/*/lifetime_write_kbytes` twice a day apart; `du -sh /var/log/journal /var/lib/docker/containers` | Wasting effort on the wrong writer | Anything, by itself | One `cat`, no risk |
| 2 | **Bound Docker logs** (`log-driver: local`, or `max-size`/`max-file`) | Unbounded disk fill and write volume from the Music Assistant container | Wear from legitimate writes | Config change; containers must be re-created for it to apply |
| 3 | **Keep the journal persistent but small**, with `SyncIntervalSec` raised and a rate limit (the 64 MB cap already in `60-watchdog.sh` is in the right shape) | Losing the crash evidence that the 2026-11-15 hang lost; unbounded journal growth | Nothing about the card | A bounded trickle of writes — an explicit trade, already made once |
| 4 | **`noatime,lazytime`** on the root and any data partition | A little inode-table churn | Everything else | One fstab edit |
| 5 | **Atomic state writes in Debra's own code** (temp file → `fsync` → `rename`, same filesystem) | A torn config/mixer/identity file after a power cut | The filesystem or the card | A code pattern; note that many "atomic write" helpers skip the `fsync` |
| 6 | **Fix the power path** (adequate 5 V supply and cable; a UPS or graceful-shutdown HAT if the appliance must never lose power uncleanly) | The documented cause of the corruption already observed | A card that is already worn | Money, not code |
| 7 | **Prove one restore onto spare media**, and keep a verified image or archive off the card | Card death, unbootable `/boot`, a corrupt root | Nothing about future corruption | Hours, and a spare card — this is the gap `device-backup.md` already names |
| 8 | **Read-only root (overlay or immutable image) + a small persistent data partition** | Corruption of the OS itself | `/boot`, the data partition, wear | Rebuild of the image/update workflow; loses on-device `apt` |
| 9 | **A/B slots with health check and automatic fallback** | An unbootable system, with actual rollback | User data, the card, active-slot `/boot` | ~2× system partition, tryboot orchestration, per-slot `/var` — an image-design decision, not a config tweak |

Rows 1–5 are hours and near-zero risk. Rows 6–7 are the ones that address the
failures this device has actually had. Rows 8–9 are architecture, and belong
with the B01/I01 image decisions rather than being slipped in as a tweak.

## Traps

- **`data=journal` is a dead end.** Safest on paper, ~2× the writes, and
  scheduled for removal in January 2028. Do not build the recovery story on it.
- **`Storage=volatile` hides the crime scene.** It is the Pi OS default and it
  is why the 2026-11-15 hang left one boot of history.
- **Masking a vendor journald drop-in needs a `/dev/null` symlink**, not another
  drop-in — that is the documented mechanism (journald.conf(5)), and the repo
  already records that a later drop-in alone did not override it.
- **Read-only root is not read-only `/boot`.** `/boot/firmware` is FAT, has no
  journal, and is written by every kernel/firmware update. It is the part that
  makes the device unbootable.
- **An overlay with a tmpfs upper silently discards changes at reboot** — which
  will include the mixer state if it is not on a persistent partition. That
  exact failure ("boots silent with every service green") is already documented
  in the device backup guide.
- **A snapshot on the same card is not a rollback.** Btrfs says so itself; a
  dead card takes the snapshot with it.
- **`fsck -y` is not a recovery strategy.** `-p` is what boots use; `-y` can
  delete recoverable data, and the undo file explicitly excludes power-loss
  recovery.
- **tmpfs is swappable.** If anyone later adds an SD swapfile, "RAM-only" state
  quietly lands on the card (RP-003610-WP states this directly).
- **Changing Docker's log driver does not touch existing containers.**
- **Derived TBW is not a spec.** SanDisk publishes hours of recording, not
  terabytes written; do not quote "117 TBW" as a vendor number.
- **`barrier=0` for "SD performance"** is a well-known bad tip that Raspberry
  Pi explicitly warns against.
- **No wear gauge means "it looks fine" is not evidence.** The absence of
  warnings is the normal state right up until the card fails.

## Not verified / open questions

- **No measurement of this device's write volume.** Every magnitude in §2 is
  either configuration-bounded or labelled an estimate. Recommendation 1 exists
  because of this.
- **The lab card's provenance and model are unknown here**; no `f3` capacity
  test has been run, so counterfeit capacity is not ruled out.
- **Whether the 2026-11-15 hang was the card or the rail remains unproven** —
  the repo already records this; this note does not settle it.
- **`overlayroot` availability on Raspberry Pi OS trixie** is unverified, as is
  whether `raspi-config`'s overlay option still exists in trixie.
- **btrfs as a Pi root filesystem** is not evaluated; Raspberry Pi's own paper
  recommends ext4 for power-loss scenarios and warns about F2FS on unclean
  shutdown, which is a reason to be cautious rather than a verdict on btrfs.
- **Whether a 64 MB persistent journal measurably shortens card life** is
  unknown; it is a deliberate diagnosability trade, not a measured optimum.
- **Card temperature in the eventual enclosure** is unmeasured; the datasheet
  limit is not a design margin.
- **No field failure data** exists for this workload, so "will it last years"
  cannot be answered from this note.

## Handoff and correction links

- Current state: research note only. Nothing here was applied to the device, and
  no file other than this note was created or changed.
- Concrete next action, cheapest first: take the two `lifetime_write_kbytes`
  readings and the Docker log sizes (recommendation 1), then decide rows 2–5 on
  evidence rather than on this note's priors.
- Authorization needed: any device change, any spare-media restore rehearsal,
  and any image-layout decision (rows 6–9) are separate work under the roadmap's
  B01/B02/I01 packets — this note does not authorize them.
- Related records: [device backup](../guides/device-backup.md),
  [silence and hang](../testing/results/2026-11-15-lab-pi5-silence-and-hang.md),
  [evidence rules](../evidence.md).
- Reviewed decision that later adopts any of this: none yet.

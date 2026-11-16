---
title: Corrections to the B01 storage durability note
date: 2026-11-15
type: project-learning
status: unreviewed
task: B01
author: OpenCode subagent (B01 corrections pass)
author_model: deepseek/deepseek-v4.1-flash-1017
sources:
  - docs/notes/2026-11-15-storage-durability.md (the note under correction, read 2026-11-15)
  - docs/notes/2026-11-15-research-notes-review-round-2.md, section "B01 — storage durability" (read 2026-11-15)
  - docs/work/cards/B01.md; docs/evidence.md; docs/project-brief.md; docs/roadmap.md (B01–B05 rows); docs/updates/2026-11-15.md ("Recovery ordering", lines 312–316); docs/guides/device-backup.md; docs/work-queue.md (B13 rows); docs/testing/results/2026-11-15-lab-pi5-silence-and-hang.md; tools/device/lab-pi5/README.md, 51-power-cap.sh, 60-watchdog.sh (all read 2026-11-15)
  - systemd journald.conf(5), systemd 262 — https://www.freedesktop.org/software/systemd/man/latest/journald.conf.html (checked 2026-11-15)
  - DAC 2011 author list via ACM DL and IEEE Xplore records for "Understanding the impact of power loss on flash memory" (checked 2026-11-15)
supersedes: []
---

# Corrections to the B01 storage durability note

## Summary

The B01 note is preserved unchanged; this file records what a reader must not
take from it. Two claims are unsafe. First, the note presents the supply fault as
the **documented cause** of the corruption already observed on the lab device
(lines 78, 245, 267). No source says that: the lab result calls a brownout during
a card write "the leading explanation. It is not proven — no `throttled` bit
survived", and `device-backup.md` now calls earlier brownouts "historical
evidence, not a current fault diagnosis". The undervoltage *mechanism* is
documented; this device's *event* is not. Second, the note concludes that
no-intervention filesystem rollback "is only achievable as an A/B slot switch"
(lines 228–230), which reverses the project's stated ordering and collapses the
same-card / off-device / rescue split that B01 exists to separate. H3 below
restores that ordering; the other findings are factual or labelling defects. The
review that produced the finding list is itself on the same model as the note's
author and is not model-independent (`research-notes-review-round-2.md`,
"Independence, stated plainly").

## Finding-by-finding

Line numbers refer to `2026-11-15-storage-durability.md` as it stands. "Verified"
names the repository or primary source actually checked here, not the review.

| ID | Sev | Current text (line) | Replacement | Verified against |
| --- | --- | --- | --- | --- |
| H1 | High | "Images are 2.2 GB on the device" (115); "write volume from the Music Assistant container" (263) | Row 115: "Music Assistant container (**optional lab extra**) — only if `40-music-assistant.sh` was run; Docker is installed but disabled at boot, so it writes nothing while stopped. Image size on the card is `unknown`; the 2.2 GB figure has no repository source." Row 263: "…from that container, if present; Debra does not ship it". Row 262's `/var/lib/docker/containers` likewise exists only on that extra. | `lab-pi5/README.md:8–12,32,49–52` ("The device is a client, not a server"; script "not part of the device"); `51-power-cap.sh:38–40` disables `docker.service`/`docker.socket`; `device-backup.md:26` — "whether images remain and their size is `unknown`". **The review's direction is right; its absolute "not on the device" is slightly too strong** — Docker was installed and the container was run once, so presence on the card is unknown, use is not. |
| H2 | High | "the documented trigger for the corruption already seen" (245); "The documented cause of the corruption already observed" (267); "This is the documented cause most relevant to *this* device" (78) | 245: "the leading, unproven explanation for the corruption already seen — no `throttled` bit survived, and the supply has since been changed". 267: "The leading, unproven explanation for the corruption already observed (not a documented cause)". 78: "A documented cause of storage corruption, and the leading unproven explanation for this device's 2026-11-15 fault." | `2026-11-15-lab-pi5-silence-and-hang.md:86–89`; `device-backup.md:11–12`; `project-brief.md:200–203`. The note's own open question (314–315) already says the cause "remains unproven", so the body contradicts itself. **Line 78 is the weakest of the three**: as written it attributes documentation to the mechanism, not to this device, so the review's grouping is generous — but "most relevant to *this* device" invites exactly the inference the other two lines assert, so it still needs the qualifier. |
| H3 | High | "is only achievable as an A/B slot switch" (228–229); "cannot be a snapshot stored on the same card" (52–53) | See the section below; the whole §4 closing paragraph (228–234) and the summary sentence (52–55) are replaced. | `updates/2026-11-15.md:312–316` (James's ordering: "filesystem rollback is the first attempt because it can be done live without user intervention; whole-card imaging is the aggressive last resort"); `project-brief.md:180–190`; `work/cards/B01.md:17–18` ("Separate same-card rollback, off-device backup, and rescue/reflash"); `roadmap.md:297–302`. |
| H4 | High | "**btrfs as a Pi root filesystem** is not evaluated" (318); no section covers capture consistency, credentials or a restore test | Not a wording fix — see "B01 acceptance status" below. | `work/cards/B01.md:9–20` against the note's own contents. |
| M1 | Med | "needs a `/dev/null` symlink**, not another drop-in" (282–283) | "A vendor journald drop-in can be overridden by a later-named `/etc` drop-in: journald.conf(5) sorts drop-ins by filename across `/usr/lib`, `/usr/local/lib`, `/etc` and `/run` and the last value wins, and it recommends prefixes 10–40 in `/usr` and 60–90 in `/etc` for exactly that reason. A `/dev/null` symlink under the vendor's own filename is the documented way to *disable* it, not the only way to override it. `50-debra-persistent.conf` did not take effect on this device for a reason not yet established; record that anomaly, do not generalise it." | journald.conf(5) fetched and read: "Files in the `*.conf.d/` configuration subdirectories are sorted by their filename in lexicographic order, regardless of in which of the subdirectories they reside… the entry in the file sorted last takes precedence"; and "To disable a configuration file supplied by the vendor, the recommended way is to place a symlink to `/dev/null`". **The review is right and the note is wrong as a general rule.** The repo's own observation (`60-watchdog.sh:19–24`) is a local anomaly, not a mechanism. |
| M2 | Med | Row labelled `upstream-documented`: "Read-only ext4 root (or `raspi-config` overlayfs with tmpfs upper)" (143) vs "whether `raspi-config`'s overlay option still exists in trixie" (316–317) | Split the label: "`upstream-documented` (overlay mechanism) + `unknown` (whether the trixie `raspi-config` option exists)". Keep the open question. | Note's own lines 143 and 316–317. Not resolvable from this repo — the Pi configuration docs returned HTTP 403 for the source register (`evidence.md:119`). |
| M3 | Med | "rpi-image-gen `image-rota` defaults: 96 MB boot + 512 MB system **per slot**, 1 GB persistent" (145) | "~2× system partition. rpi-image-gen's example is 96 MB boot + 512 MB system per slot + 1 GB persistent, but this device's root is recorded at 5.7 GB, so size slots from the measured root, not from the example." | `device-backup.md:138` (root "described as 5.7 GB"); the note's own 512 MB figure at 145. The review's word "default" is loose — it is rpi-image-gen's example layout — but the understatement is real. |
| M4 | Med | "This is the "sshd accepts, never sends a banner" shape the lab device already produced" (192–193) | "A remount-ro event looks like services failing while the kernel is healthy. The 2026-11-15 hang produced the same *symptom*, but the lab result attributes it to a process in uninterruptible sleep on storage, and the volatile journal recorded no remount. `errors=remount-ro` is not established as that hang's cause." | `silence-and-hang.md:65–89` — accepted TCP, no banner, "almost always a process in uninterruptible sleep on storage"; journal was volatile, so no remount could have been recorded. **The review is right.** |
| M5 | Med | "**All root changes are lost at reboot**" (143) | "A plain `ro` root makes writes fail visibly; an overlayfs tmpfs upper lets them appear to succeed and discards them at reboot. Either way root changes do not persist." | Note's own trap at 288–291 describes the silent variant, so the table cell contradicts it. |
| M6 | Med | "The lab device uses 2 GiB zram" labelled `observed` (repo/task statement) (119) | "The lab device is reported to use 2 GiB zram; no repository file records it." Label: `unknown` — the task statement is not a record. | Repo-wide search for `zram`: no machine or script records it; the only hits are this note and unrelated web-control metric design. **Review right.** |
| M7 | Med | "the 1.1 GB file-level archive" (61); "a 1.1 GB file-level archive on the host" (232–233) | "1.19 GiB compressed (4.08 GB decompressed)". | `device-backup.md:70`. |
| M8 | Med | "M. Zheng et al., … DAC 2011" (22) | "Hung-Wei Tseng, Laura M. Grupp and Steven Swanson". | ACM DL 10.1145/2024724.2024733 and IEEE Xplore 5981701 both list Tseng, Grupp, Swanson. **Review right.** |
| M9 | Med | §6 header "Change / Protects against / Does not protect against / Cost" (260–270) | Add per row: time, money, consumable (spare card, reader), downtime, risk, and a "restore demonstrated?" column that reads **no** for every row. | `device-backup.md:111–114` ("Both recovery cells are **proposals, not procedures**… No restore has been performed"). The column is technical, not beginner-facing; the review is right. |
| L1 | Low | "which writes at most about once per day per file" (120) | "…and also whenever mtime or ctime is newer than atime". | mount(8) relatime semantics; the simplification is not wrong, just incomplete. |
| L2 | Low | "do not quote "117 TBW" as a vendor number" (301) | "…and the arithmetic is the 128 GB card's (10,000 h × 11.7 GB/h); §3 shows only the 32 GB ≈ 29 TB case". | The note's own §3 (151–158) derives 29 TB; 117 TB appears only in the trap, with no derivation. |
| L3 | Low | "Restore from verified media" (225); "keep a verified image or archive off the card" (268) | "verified **at restore time**: a retained release or image is never re-checked after it is superseded (B13), so 'verified' cannot mean verified at capture". | `work-queue.md:83` — "an upgraded-away release is never re-checked, so a corrupted old release is restored by rollback without complaint". |
| L4 | Low | "| SMART | **Not applicable** |" (250) | "**Not applicable as a wear metric**" — keep the cell's own `reported`/`unknown` qualifier visible in the verdict column. | Note's own cell text (250). |
| L5 | Low | Summary reads as settled (39–55) vs `status: unreviewed` (5) | Open the summary with: "Unreviewed research; every magnitude in §2 is unmeasured and §6 is a cost ordering, not an adopted plan." | Note's own status line and 57–58. |

## H3 — restoring the project's ordering

The note's §4 table (222–226) is sound. Its closing paragraph is not: it defines
"filesystem rollback" as whole-system rollback and then declares the whole
category unreachable without A/B. That is not what the project decided.
`updates/2026-11-15.md:312–316` records James's ordering — filesystem rollback is
the first attempt because it can be done live without user intervention;
whole-card imaging is the aggressive last resort — and `project-brief.md:188`
says "Reflashing is a fallback, not the main everyday rollback experience".

**Replacement for 228–234:**

> **A/B is the only automatic whole-OS fallback; file-level rollback is a
> separate, cheaper layer.** Three failure modes need three different answers,
> and only the first is "rollback" in the everyday sense:
>
> - **(a) Same-card file/state rollback** — restore selected files or a
>   pre-change snapshot on the running card. Works while the card mounts, needs
>   no media and no user step, and is the layer the project asks for first
>   (`project-brief.md:180–181`, `roadmap.md:297`). It cannot survive card death,
>   and a snapshot on the same card dies with it (btrfs says so itself).
> - **(b) Off-device backup and restore** — an archive or image held on other
>   media. Survives card death and a destroyed filesystem; needs media, a
>   reader or network path, and a *rehearsed* procedure. `device-backup.md`
>   records the capture and no restore.
> - **(c) Rescue and reflash** — the last resort: boot something that is not the
>   failing card and rebuild. It is what makes (b) usable and what B05 covers;
>   it is not an everyday rollback experience.
>
> No restore has been demonstrated for any of the three. That is the gap, not
> the absence of an A/B slot.

**Replacement for 52–55 (summary):**

> A "filesystem rollback" that works with no user intervention cannot be `fsck`,
> and cannot survive a dead card if it lives on that card. Only an A/B slot
> switch is an automatic *whole-OS* fallback; file-level rollback is a separate,
> cheaper layer, and an off-device restore is a third.

**Which §6 row addresses which mode:**

| Failure mode | §6 rows today | Status |
| --- | --- | --- |
| (a) same-card file/state rollback | **none** | The only mention is §4's btrfs row, which the summary then denies. This is the gap the brief and roadmap prioritise. |
| (b) off-device backup and restore | row 7 ("Prove one restore onto spare media…") | Present as a recommendation; no restore exists. |
| (c) rescue and reflash | **none** | Only §4 prose ("a bootable recovery path that does not live on the failing card"). |
| automatic whole-OS fallback | row 9 (A/B slots) | Correctly scoped to the OS, not user state. |
| prevention / dose reduction | rows 1–5, 8 | Not rollback at all; keep them out of the ordering. |

`roadmap.md:306` repeats the same wrong conclusion ("a no-intervention rollback
means an A/B boot slot or a restore from verified media"). It is outside this
file's scope; the coordinator needs to amend it with the note.

## B01 acceptance status

Against `work/cards/B01.md` (lines 9–20). "Partly" means the note contains the
material but not the analysis the card asks for.

| Card requirement | Status | Why |
| --- | --- | --- |
| CoW vs incremental non-CoW comparison | not started | btrfs explicitly not evaluated (318); no non-CoW incremental approach is examined at all. |
| Realistic separate boot/root Pi layouts | partly met | `/boot/firmware` separation and FAT/no-journal are covered; partition layout, sizes and slot geometry are not. |
| Boot/kernel/modules coupling | partly met | Traps name `/boot/firmware` and per-slot `/var`; kernel/modules vs restored root is never analysed. |
| Consistent capture | not started | Live-capture inconsistency appears only as a caveat inherited from `device-backup.md`; no quiesce/freeze/snapshot mechanism is compared. |
| Live versus offline restore | partly met | §4 distinguishes "media access and a *tested* restore" from a slot switch; no live-vs-offline analysis. |
| Storage overhead / minimum card | partly met | A/B per-slot figures are given but understated (M3); no minimum-card calculation for file-level snapshots. |
| Full-disk and power-loss failure | met | §1, §4 and §5 cover write abort, retroactive corruption, FTL loss, disk fill. |
| Credential protection | not started | The archive holds Wi-Fi credentials and SSH host keys (`device-backup.md:74`), host files were found `0644` (`:48–52`), and B13's retained-release gap applies (`work-queue.md:83–85`). None is analysed. |
| Unbootable-root / dead-card rescue | partly met | The failure is described (§4 item 4, §5); no rescue route, requirements or prerequisites. |
| Source-backed decision table | partly met | §1/§3/§6 are labelled tables, but they compare mitigations, not backup backends. |
| Minimal first-backend recommendation + exit path | not started | §6 is a cost ordering of mitigations; no backend, no exit path. |
| Separate same-card / off-device / rescue | not met | §4's three rows are slot switch, media restore and btrfs snapshot — a different cut — and the summary collapses them (H3). |
| Disposable-media restoration test proving networking/SSH/identity/boot, with time | not started | Row 7 says "prove one restore"; no test design, criteria or duration. |
| No claimed backup success or destructive-trial permission | met | Handoff (328–341) says nothing was applied and authorization is needed. |

## What remains unknown

- The actual cause of the 2026-11-15 hang; the review's and this file's position
  is that it is unproven, and no `throttled` bit survived.
- This device's write volume; no `lifetime_write_kbytes` pair has been read.
- Whether the optional Music Assistant image is still on the lab card, and its
  size.
- Whether the lab device runs 2 GiB zram — no repository record.
- Why `50-debra-persistent.conf` did not override the vendor drop-in here, given
  the documented precedence.
- btrfs (or any CoW) behaviour as a Pi OS trixie root; whether `raspi-config`'s
  overlay option exists in trixie.
- The lab card's model and provenance; no capacity test has been run.
- Whether any restore of any kind works, on any media — none has been tried.

## What I did not do

Read and cite only. No device contact, no command run against the lab Pi, no test
suite, no restore rehearsal, no git operation, no edit outside this file, and no
recommendation of a backup scheme — that decision belongs to the coordinator.

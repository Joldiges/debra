---
title: Evidence audit — can Debra's documents back up what they claim?
date: 2026-11-15
type: project-learning
status: unreviewed
task: none
author: OpenCode subagent (documentation audit)
author_model: deepseek/deepseek-v4.1-flash-1017
author_variant: unknown
sources:
  - docs/evidence.md (read 2026-11-15)
  - docs/comparisons/sources.md, devices.md, music-playback.md, README.md (read 2026-11-15)
  - docs/testing/results/*.md, docs/notes/*.md, docs/guides/*.md, docs/design/*.md (read 2026-11-15)
  - models/**/README.md, models/**/*.sc, models/**/build-script.json (read and re-run 2026-11-15)
  - Repository at 84411f8; no device contacted, no network fetch, no file changed except this note
supersedes: []
---

# Evidence audit: what the record can and cannot support

**Desk audit of what is already written, 2026-11-15.** I read the evidence rules
and then followed representative claims to their evidence: a dated source, a test
record with a command and an observed result, or a measurement with its method.
Nothing was bought, contacted or fetched; the only local executables I ran are
repository tools and `solidcraft-cli` (see Verification). No file other than this
note was created or changed.

**Headline: the documentation is unusually honest about what it does not know,
and that honesty mostly holds up.** Unreviewed notes are labelled unreviewed;
`U` cells are not silently converted to "no"; one-row device claims map to real
test records; every model volume I re-ran reproduces. The failures are not
"everything is invented" — they are a handful of places where a document claims
**more than its own label or its own register entry allows**, plus three places
where **Debra's own records contradict each other**.

**Counts (55 claim rows):** supported **34**, weaker than stated **14**,
unsupported **7**. Of the seven unsupported, **4 have no evidence recorded** and
**3 are contradicted by other Debra records** (a different failure: one needs a
check, the other a decision). Unreviewed status is never counted as unsupported.

| Group | Rows | Supported | Weaker | Unsupported |
| --- | ---: | ---: | ---: | ---: |
| Buying prices and availability | 12 | 7 | 4 | 1 |
| Build cost arithmetic | 6 | 5 | 0 | 1 (contradicted) |
| Board compatibility screen | 5 | 3 | 1 | 1 |
| Music transport | 9 | 7 | 0 | 2 |
| Debra's device claims and measurements | 8 | 3 | 5 | 0 |
| Models | 8 | 6 | 2 | 0 |
| Test records and their echoes | 7 | 3 | 2 | 2 (1 contradicted) |

## Buying prices and availability

| Claim (file:line) | Evidence found | Verdict | What would settle it |
| --- | --- | --- | --- |
| Voice PE `$58.95` ameriDroid, `$58.95` CloudFree sold out [devices.md:22](../comparisons/devices.md) | Register [S35]/[S36] record both prices and the same-day re-check; R02 rev 2 gives the product-JSON path | supported | — |
| "All sources checked 2026-11-15 unless the cell says otherwise" [devices.md:5](../comparisons/devices.md) | True for fetch dates, but the Seeed price/stock cell [devices.md:22](../comparisons/devices.md) rests on [S37], whose own entry says price and stock "were not readable in revision 2" and reuses an R02 reading | weaker than stated | Mark that cell `historical`/as-of-R02, or read the Seeed price server-side |
| "$34.99 Amazon and £13 Pi Hut as recorded in R02" [devices.md:24](../comparisons/devices.md) | [S38] covers only `$14.50` M5Stack direct and its stock. The original R02 line ([complete-alternatives:94](2026-11-15-complete-alternatives-comparison.md)) lists both figures with **no URL**, and R02 states Amazon "blocked or was not fetched" (line 278) | unsupported (no evidence recorded) | One dated listing per figure, or delete them from a buying cell |
| Atom VoiceS3R `$14.50`, "out of stock on re-check" [devices.md:112](../comparisons/devices.md) | [S38]: `available: false`, conflicting readings the same day | supported | — |
| ATOM Voice "10+ in stock on 2026-11-15" [devices.md:111](../comparisons/devices.md) | [S4] records the literal stock string; the shop is the vendor itself | supported | — |
| Satellite1.1 HAT "in stock 2026-11-15, but the same page showed backorder with a 15 Dec 2026 restock earlier the same day" [devices.md:117](../comparisons/devices.md) | [S10] records only "listed available". The 15 Dec restock observation appears in no register entry; the trail stops at the page | weaker than stated | Add the backorder observation to [S10] with its time, or drop the restock date |
| Satellite1.1 Dev Kit "in stock 2026-11-15" [devices.md:118](../comparisons/devices.md) | [S12]: "listed available" | weaker than stated | Keep the register's wording; "listed available" ≠ "in stock" |
| Satellite1.1 Smart Speaker "in stock 2026-11-15" [devices.md:119](../comparisons/devices.md) | [S13]: "listed available" | weaker than stated | As above |
| Echo Dot `$79.99` list, `reported`, review dated 2026-06-16, "not re-verified" [devices.md:26](../comparisons/devices.md) | [S39] carries the PCMag date and figure; the cell labels it `R` and says not re-verified | supported | — |
| Google Home Speaker `$99.99` `reported`; model `U` [devices.md:28](../comparisons/devices.md) | [S52] (Engadget, 2026-06-18) and [S57]; the cell states the model is not named on the Cast page | supported | — |
| Willow "approximately $50" marked `historical`, 2023 [devices.md:29](../comparisons/devices.md) | [S58]: project's own 2023 figure; site content dated 2023 | supported | — |
| "$59.90 is below the Voice PE's estimated complete music setup ($93.95–$139.00, of which just the $58.95 device price is sourced)" [devices.md:65](../comparisons/devices.md) | R02 rev 2 gives the band and says the supply/speaker bands are estimates carried from R02 ([complete-alternatives-revision:165](2026-11-15-complete-alternatives-comparison-revision.md)); arithmetic reconciles: 58.95 + 10–20 + 25–60 | supported | — |

## Build cost arithmetic

| Claim (file:line) | Evidence found | Verdict | What would settle it |
| --- | --- | --- | --- |
| Complete purchase `$59.90`; `$68.35` with a second supply [devices.md:54](../comparisons/devices.md) | [parts-inventory:225–234](2026-11-15-parts-inventory.md) line items; I re-added them: 20.75 + 12.90 + 3.50 + 13.95 + 8.80 = 59.90, + 8.45 = 68.35 | supported | — |
| A′ `$62.49` fully priced WM8960 build [devices.md:55](../comparisons/devices.md) | [parts-inventory:258](2026-11-15-parts-inventory.md); adds to 62.49 and the note says it is untested | supported | — |
| Reused parts `$16.40`; `$17.35` with header [devices.md:56](../comparisons/devices.md) | [parts-inventory:243–247](2026-11-15-parts-inventory.md); adds to 16.40/17.35; page calls it marginal, not a unit price | supported | — |
| "an amplifier for the 2-Mics HAT … excluded" — and the source claim that the HAT has none [devices.md:58](../comparisons/devices.md), [parts-inventory:150–155](2026-11-15-parts-inventory.md), [complete-alternatives-revision:207](2026-11-15-complete-alternatives-comparison-revision.md) | **Contradicted by Debra's own measurement**: the speaker is fed from `Line` "through the board's TPA2005D1 amplifier" ([audio-outputs:39–40](../design/audio-outputs.md)), tape tap test `Line` −21 dBFS vs `HP` ≈ −100 dBFS ([silence-and-hang:33–35](../testing/results/2026-11-15-lab-pi5-silence-and-hang.md)), and the correction note records "LINE→amplifier→speaker is supported by the bring-up evidence" ([corrections:30](2026-11-15-audio-and-enclosure-corrections.md)). R02 rev 2 even says the settling step is to read the lab record, and it was not done | unsupported (evidence contradicts) | Read the ReSpeaker v2 schematic for the TPA2005D1 and its JST speaker; then delete the "excluded amplifier" line from both totals |
| "R01's figures still rest on historical, unverified speaker prices" [devices.md:62](../comparisons/devices.md) | [parts-inventory:139–147, 361–367](2026-11-15-parts-inventory.md): all three Amazon pages returned HTTP 503; $2.50/$3.50 are undated historical figures | supported | — |
| "The ~$40 goal is reachable, but only in the reused-parts sense" [parts-inventory:53](2026-11-15-parts-inventory.md) | Same note's route table and its seven named exclusions; arithmetic checks | supported | — |

## Board compatibility screen

| Claim (file:line) | Evidence found | Verdict | What would settle it |
| --- | --- | --- | --- |
| "ROCK 3C … a documented starting point, not a demonstration" [devices.md:92](../comparisons/devices.md) | [S46] reads the vendor pin table; page repeats that matching positions do not establish HAT support | supported | — |
| ROCK 3C / ZERO 3W / 3B survive with "a decisive unknown each"; Zero 2W and Le Potato "not demonstrated" [devices.md:79–84](../comparisons/devices.md) | R07 rev 2 plus [S42]–[S47], [S61]; each row keeps its one blocking question and no shortlist is claimed | supported | — |
| Zero 2W "pins not soldered by default" [devices.md:95](../comparisons/devices.md) | [S42]'s Covers column records only the V1.1 header table, I2C at 3/5 and no listed I2S; the unsoldered-pin fact is not in the register entry | weaker than stated | Add it to [S42]'s covers, or drop the sub-claim |
| "Radxa's own images are carried as Debian 12 bookworm with 5.10/6.1 kernels" [devices.md:103](../comparisons/devices.md) | No key and no date on the sentence; the register has no entry covering Radxa image/kernel versions | unsupported (no evidence recorded) | Cite the Radxa software page and date, or mark it `U` |
| "whether any Armbian image clears LVA's Python floor is a hypothesis `H`" [devices.md:104](../comparisons/devices.md) | Label present and appropriate | supported | — |

## Music transport

| Claim (file:line) | Evidence found | Verdict | What would settle it |
| --- | --- | --- | --- |
| Satellite1 Sendspin since firmware v0.2.0, 2026-05-28 [music-playback.md:41](../comparisons/music-playback.md) | [S33] release page (Sendspin replaces Snapcast) and [S15] | supported | — |
| Voice PE Sendspin in firmware 25.12.0, 2025-12-17, "public preview" [music-playback.md:42](../comparisons/music-playback.md) | [S20] records the exact release line and date; the page re-read it directly (line 128–131) | supported | — |
| Voice PE "48 kHz FLAC `media_pipeline` in the dev YAML" [music-playback.md:42](../comparisons/music-playback.md) | [S20]'s entry covers only the Sendspin release line; [S21] covers the ESPHome `sendspin` component. No register entry covers a Voice PE development YAML or its 48 kHz FLAC pipeline | unsupported (no evidence recorded) | Cite the voice-pe dev YAML with a pinned commit, or drop the stream detail |
| VoiceS3R YAML declares ESPHome 2026.10.0 while vendor prose says 2026.1.0 — both recorded, neither chosen [music-playback.md:43](../comparisons/music-playback.md) | [S22] and [S7]; R02 rev 2 keeps the disagreement and marks "works at 2026.1.0" `U` | supported | — |
| ReSpeaker Lite needs XMOS I2S firmware ≥ 1.1.0, then a community config [music-playback.md:44](../comparisons/music-playback.md) | [S25] (vendor wiki) + [S26] (community config), labelled `D`+`R` | supported | — |
| "Snapcast has no pause at all" [music-playback.md:28](../comparisons/music-playback.md) | [S30] does not carry this. The claim rests on R03, which quotes MA's own docs: "MA issues a STOP and RESUME command … the resulting player state never changes to paused" ([music-transport:65](2026-11-15-music-transport-and-control-map.md)) | supported, two hops via an unreviewed note | Review R03, or quote the MA sentence on the comparison page |
| "Sendspin needs … MA 2.11 beta; stable was 2.10.12 when this was written" [music-playback.md:84](../comparisons/music-playback.md) | No key, no date. [S56] covers only the "technical preview" wording; R03 records the inspected MA as `2.11.0.dev2026111103` and the dev branch | unsupported (no evidence recorded) | Cite the ESPHome/MA requirement line with a version and date |
| "No listening test, latency measurement or captured sample rate exists for any of the seven" [music-playback.md:107–110](../comparisons/music-playback.md) | True of the repository: the only `T` row states audio reached the microphone, not quality ([lva-sendspin:157–170](../testing/results/2026-11-15-lab-pi5-lva-sendspin.md)) | supported | — |
| "the Pi 5 guide pins a 16 kHz clock [S28]; the 16 kHz ceiling describes the separate USB 4-Mic Array [S27]" [music-playback.md:96–98](../comparisons/music-playback.md) | [S27]/[S28] say exactly that, and the page refuses to convert a configuration into a hardware limit | supported | — |

## Debra's device claims and how strongly they are restated

| Claim (file:line) | Evidence found | Verdict | What would settle it |
| --- | --- | --- | --- |
| Full lab-Pi row: LVA `v1.1.18` accepted by HA, wake→STT→intent→TTS completed, Sendspin `9.1.0`, "MA streamed FLAC to the HAT", speaker→air→mic measured, mic/channel map `U` [devices.md:116](../comparisons/devices.md) | Every clause is in the records: `Stream started with codec flac`, `Audio format: flac 44100Hz/24-bit/2ch`, peak −12.5 dBFS ([lva-sendspin:32](../testing/results/2026-11-15-lab-pi5-lva-sendspin.md)); 41 dB 1 kHz rise plus James's ear check ([pi5-audio:84–92](../testing/results/2026-11-15-pi5-respeaker-v2-audio.md)); channel map unverified ([pi5-audio:123](../testing/results/2026-11-15-pi5-respeaker-v2-audio.md)) | supported | — |
| "yes, lab-tested" for voice and music in the capability summary [devices.md:141](../comparisons/devices.md) | Same records; the capability statement does not borrow the unmeasured parts (quality, distance, echo) | supported | — |
| "the 3.5 mm jack is on the headphone output" [audio-outputs:40](../design/audio-outputs.md) | Contradicted 70 lines later in the same file: "Whether the 3.5 mm jack is on the line tap or the headphone tap … Not tested" ([audio-outputs:112–117](../design/audio-outputs.md)), and by the record ([silence-and-hang:118](../testing/results/2026-11-15-lab-pi5-silence-and-hang.md)) | weaker than stated (internal contradiction) | Plug headphones in and play a tone to each tap |
| "Nothing audible was played, so none of this disturbs a sleeping house" [audio-outputs:131](../design/audio-outputs.md) | Its own table plays a tone to the mic twice (−40.4 / −40.6 dBFS, [audio-outputs:138](../design/audio-outputs.md)) and line 159 says the tone ran at the device's 36 % level. The document's own banner (lines 9–11) already retracts the wording | weaker than stated (self-disclosed) | — |
| Combine-sink and echo-cancel results: −40.4 vs −40.6 dBFS, "17.7 dB" at 50 %, −57.9 dBFS rms from the cancel source [audio-outputs:138–140](../design/audio-outputs.md) | Method is quoted inline (`pactl load-module`, `pw-play --target`, microphone as detector) but there is **no test record** in `docs/testing/results/`; [evidence.md:16](../evidence.md) requires a linked record for `tested` | weaker than stated | Write these into a dated result record with versions, or label them `reported`/inline observation |
| "a reply reaches the microphones around −40 dBFS, which is louder than a person speaking across a room" [audio-outputs:144](../design/audio-outputs.md) | This is the speech-level inference the correction note withdraws ([corrections:28](2026-11-15-audio-and-enclosure-corrections.md)): a 1 kHz tone's dBFS "does not measure speech level, comfort, acoustic safety" | weaker than stated | Measure actual speech, or drop the comparison |
| "doubling the volume moves the measurement by 5.7–6.1 dB, which is 20·log₁₀(2)" [audio-levels:43–46](../testing/results/2026-11-15-lab-pi5-audio-levels.md) | Contradicted by that table's own rows (8→16 % is +16.5 dB); already corrected ([corrections:27](2026-11-15-audio-and-enclosure-corrections.md)) and superseded by the banner at lines 3–6 | weaker than stated (self-corrected) | — |
| "The 3.5 mm jack is untested" [silence-and-hang:118](../testing/results/2026-11-15-lab-pi5-silence-and-hang.md) | Matches the other records; a genuine limit, not a claim | supported | — |

## Models

| Claim (file:line) | Evidence found | Verdict | What would settle it |
| --- | --- | --- | --- |
| "Every folder here holds `README.md`, `<name>.sc`, `assets/`" [models/README.md:4–9](../../models/README.md) | `components/rpispeaker-v17/` has README and renders but **no source** (it is a STEP extraction), and `components/pi5-5-model-b/` carries `pi5-reference.sc`, not `<name>.sc` | weaker than stated | Say "a source where the model is a Debian-built part; the v17 folder is a read-only extraction" |
| v17 "Reported solid properties: Volume 15,282 mm³ … 143 faces … estimated mass 19.71 g" [rpispeaker-v17:47](../../models/components/rpispeaker-v17/README.md) | Reproduced: `solidcraft-cli eval` on the STEP gives 15,282.410 mm³, one body, 143 faces, bbox −17.15/−0.60/−37.65 to 49.0/15.5/37.65; 15,282 × 1.29/1000 = 19.71 g. The README's "method unknown" (line 115) is answerable: `solidcraft-cli eval` | supported | — (optionally record the command) |
| "The second bay endpoints X 17.15–48.25 give 31.10 mm" [rpispeaker-v17:35](../../models/components/rpispeaker-v17/README.md) | STEP plane offsets contain X+ 17.15 and X− 48.25; the Ø2.18 pilots sit at (32.5, ±18.25), 36.5 mm apart, drilled to Y 7.29 — all as stated | supported | — |
| "9283 mm³ measured, and 9283 mm³ by hand (7540 + 2434 − 847 − 168 + 462 − 137)" [zero2w-hat-tray:60](../../models/parts/zero2w-hat-tray/README.md) | CAD gives 9,282.88 mm³ ✓, but the listed hand terms add to **9284**, one unit above the stated 9283 | weaker than stated (arithmetic slip) | Correct one term; the conclusion is unaffected |
| Tub "26 160 mm³", lid "8 986 mm³" [dweii-671-case:16–17](../../models/parts/dweii-671-case/README.md) | `eval` totals 35,145.85 mm³ over two bodies; 26,160 + 8,986 = 35,146 ✓ | supported | — |
| "The independent expected volume was 4,028.8431 mm³, relative difference less than 0.000001 %" [rpispeaker-v17-lid:118](../../models/parts/rpispeaker-v17-lid/README.md) | Recomputing the printed formula gives 4,028.87; `eval` gives 4,028.8431 and the bbox matches to 0.1 mm. "Independent" is a hand evaluation of the same parametric formula, not an independent model | supported | — |
| "Proves: the reference arrangement has … an overall height of 21 mm" — plus "does not prove that the parts do not collide" [zero2w-respeaker-stack:68–75](../../models/assemblies/zero2w-respeaker-stack/README.md) | `eval`: 18 bodies, 38,664.66 mm³, bbox 126.5 × 40 × 21; the disclaimer is accurate and precedes any fit reading | supported | — |
| No model folder asserts a real-world fit without a print [models/README.md:25](../../models/README.md) | Checked all six part READMEs and four assemblies: each says "not printed, not fit-tested" and each separates sourced, assumed and estimated dimensions | supported | — |

## Test records and how they are echoed elsewhere

| Claim (file:line) | Evidence found | Verdict | What would settle it |
| --- | --- | --- | --- |
| Accepted page hash `2df0591065…`, 2667 bytes, from commit `0e0d03b…`, ancestor of `88e1fcb…` [ai-readiness:53–60](../testing/results/2026-11-14-ai-readiness.md) | Re-ran: `git show 0e0d03b:docs/guides/current-status.md \| sha256sum` = `2df0591065…`, 2667 bytes, and `0e0d03b` is an ancestor of `88e1fcb` | supported | — |
| "`taskchain.py check` passed (19 chains, 63 packets); all 15 tests" [f05:93–95](../testing/results/2026-11-15-f05-source-feasibility.md) | Baseline-scoped and accurate for commit `46c02ab`. At 84411f8 the same commands pass with 19 chains / **65** packets and 174 tests (12 skipped) | supported (stale count, not wrong) | — |
| "Extraction also read the entire 5.7 GB stream to completion … so the archive is not truncated" [device-backup:127](../guides/device-backup.md) | `zstd -t` passes, but the frame decompresses to **4,081,418,240 bytes (4.08 GB)**, not 5.7 GB. Compressed size is 1.19 GiB, not "about 1.1 GB" | unsupported (evidence contradicts) | Correct the figure from the archive, or say what the 5.7 GB counted |
| "437 entries including all five of those" [device-backup:85](../guides/device-backup.md) | `tar -tf` on the boot archive lists exactly 437 entries; all five named files present | supported | — |
| Archive stored in `.local/backups/` "(mode 0700, never committed)" [device-backup:47](../guides/device-backup.md) | Directory is 0700 and git-ignored ✓; the two archives themselves are **0644**, against the owner-only file guidance | weaker than stated | `chmod 600` the two archives |
| Lab Pi holds "Docker + Music Assistant container, 2.2 GB of images" [device-backup:26](../guides/device-backup.md) | Conflicts with the device records: MA is "the household instance, not a Debra component", `40-music-assistant.sh` "is not enabled", and Docker was disabled at boot ([lva-sendspin:68–71, 140, 166–168](../testing/results/2026-11-15-lab-pi5-lva-sendspin.md)) | unsupported (records contradict) | State which machine runs MA; one `docker images` on the Pi settles it |
| Lab row's "HAT price `U`; Pi 5 price `U`" [devices.md:116](../comparisons/devices.md) | Under-claims: [parts-inventory:119, 257](2026-11-15-parts-inventory.md) record $12.90 and $110 listed prices (both out of stock / no stock indicator) | weaker than stated (conservative, not risky) | Use the R01 figures with their stock caveats |

## Well evidenced

These are the claims that hold up when pushed, and they are the majority:

- **The lab-Pi device row is the strongest thing in the corpus.** Seven separate
  `[T]` clauses on [devices.md:116](../comparisons/devices.md) each resolve to a
  quoted command output in a dated record, including the exact FLAC format string
  and the 41 dB speaker→air→mic rise with James's ear confirmation. The same row
  keeps the two things it cannot show — channel mapping and headphone routing —
  as `U`.
- **The test records themselves are honest instruments.** They name board revision,
  kernel string, component versions, the script used, the numbers, and a "what
  this does not prove" list ([pi5-audio:119–127](../testing/results/2026-11-15-pi5-respeaker-v2-audio.md)).
  Where an inference was made (the power-rail sag), the record says so and names
  the cheap confirmation ([lva-sendspin:151–155](../testing/results/2026-11-15-lab-pi5-lva-sendspin.md)).
- **Model numbers are reproducible.** I re-ran ten sources: volumes 9,282.88 /
  4,028.8431 / 25,322.65 / 3,291.86 / 20,879.45 / 35,145.85 / 65,471.56 /
  39,665.07 / 38,664.66 / 58,600.65 mm³ and every bbox match the READMEs. The v17
  extraction's 15,282 mm³, 143 faces, 262 `ADVANCED_FACE` entities, 76 planes /
  154 cylindrical patches / 9 cones and 66.15 × 16.10 × 75.30 mm envelope all
  verify against the STEP. No folder claims a fit it has not printed.
- **The register's one-way rule is intact.** Every `[S#]` used in `docs/` has an
  entry; only `S50` is defined and never cited. All 64 entries carry a URL and a
  `2026-11-15` read date, and no entry is dated later than the claim it supports.
- **`U` is used as a real value.** Eleven device cells and every board row keep an
  explicit unknown instead of "no"; the "not demonstrated" wording for Zero 2W and
  Le Potato ([devices.md:79–84](../comparisons/devices.md)) is exactly the
  distinction [evidence.md:20](../evidence.md) asks for.
- **Corrections are appended, not laundered.** The audio-levels and audio-outputs
  documents carry banners that keep the measurements and reject the conclusions;
  R02/R07/R04/N01 all keep revision 1 and link revision 2; the review's 28 findings
  are still readable. The hash of the superseded status page still verifies.
- **Version pins are real pins.** R03 cites the Sendspin spec at a commit and the
  MA tree at a commit; the ARMv6 note cites both repositories at commits and says
  its "observed" means ELF headers read, "weaker than a run".

## Register defects

Ordered by how much they could mislead a decision.

1. **A price cell with no source anywhere.** `$34.99 Amazon` and `£13 Pi Hut`
   ([devices.md:24](../comparisons/devices.md), repeated at
   [devices.md:112](../comparisons/devices.md)) carry `[S38 R]`, but `S38` covers
   only M5Stack's `$14.50` and its stock. The figure has no URL in R02 either
   ([complete-alternatives:94](2026-11-15-complete-alternatives-comparison.md)),
   and R02 says Amazon was blocked (line 278). This violates
   [sources.md:84–85](../comparisons/sources.md) ("prices without a date get no key").
2. **Covers that do not cover the cell.** Four cases: `S20`/`S21` for the Voice PE
   development YAML and its "48 kHz FLAC"
   ([music-playback.md:42](../comparisons/music-playback.md)); `S10`/`S14` for
   "armhf/aarch64 on a Pi" ([devices.md:117](../comparisons/devices.md)) when `S10`
   is a HAT page with no SoC; `S51` for the quoted "not a standalone device"
   ([complete-alternatives-revision:111](2026-11-15-complete-alternatives-comparison-revision.md)),
   which `S51`'s entry does not record; `S42` for "pins not soldered by default"
   ([devices.md:95](../comparisons/devices.md)).
3. **Register wording weaker than the page built on it.** `S10`, `S12`, `S13` all
   say "listed available"; the pages say "in stock 2026-11-15"
   ([devices.md:117–119](../comparisons/devices.md)). Same rule, three cells.
4. **A same-day observation with no register home.** The Satellite1 HAT
   "backorder with a 15 Dec 2026 restock earlier the same day"
   ([devices.md:117](../comparisons/devices.md)) appears in no entry; the trail
   stops at the page. [sources.md:62–64](../comparisons/sources.md) says stock is a
   snapshot; this one is not recorded as one.
5. **A blanket date claim that is true of fetches and false of readings.**
   "All sources checked 2026-11-15" ([devices.md:5](../comparisons/devices.md))
   sits above a Seeed price taken from R02 because the price did not render
   ([S37](../comparisons/sources.md)).
6. **A source cited for a mechanism it does not carry.** "Snapcast has no pause"
   is listed against `S30`, whose entry is one line about synchronised multi-room.
   The real evidence is R03's quotation of MA's docs — correct, but the register
   entry is being asked to support more than it records
   ([music-playback.md:28](../comparisons/music-playback.md)).
7. **Register scope is narrower than its use.** [sources.md:3–5](../comparisons/sources.md)
   calls itself "numbered sources for devices.md", but
   [music-playback.md](../comparisons/music-playback.md) depends on the same keys
   and has no register of its own.
8. **One unused key.** `S50` (Libre Computer V2) is defined and never cited; its
   page body was JS-rendered in R07 and only a search extract was read. It is
   honestly marked as a lead, so this is housekeeping, not a defect in a claim.

Checks that came back clean: no cited key is missing; no entry lacks a date or a
URL (`T` is the documented exception at
[sources.md:75–77](../comparisons/sources.md)); no entry postdates its claim; no
entry silently rewrites an earlier one.

## Are the evidence rules being followed?

**Broadly yes, at a level most project documentation never reaches.** The rules in
[evidence.md](../evidence.md) are applied per cell rather than per page; `U` is
treated as a value; test records carry the fields the rules ask for; models state
method and print status; corrections are dated and cited rather than edited away.
"Unreviewed" is used honestly and I have not counted it as a failure.

The deviations fall into four patterns, and they need different responses:

1. **Citation coverage drift (most common).** A claim is true and someone checked
   it, but the key attached to the cell covers a neighbouring fact. Six cases,
   all cheap to fix by editing a Covers cell or adding one key.
2. **One surviving contradiction inside Debra's own records.** The 2-Mics
   amplifier claim outlived the measurement that contradicts it, and it is
   load-bearing for a published cost total. This is the only finding that changes
   a number a reader might act on.
3. **Measurements outside the test-record system.** The combine-sink, echo-cancel
   and volume numbers in `docs/design/audio-outputs.md` are described and
   reproducible in principle, but `tested` is defined as pointing at a record.
   Either move them into a result note or stop implying the stronger label.
4. **Two slips that look like carelessness rather than over-claiming.** The backup
   stream size (a contradicted number inside a well-kept archive record) and the
   `models/README.md` folder-structure sentence (two folders do not match it).
   Neither is a reasoning failure; both are the kind of thing a reader trusts
   because the surrounding text is careful.

## Verification

- Working directory `/home/james/Projects/debra` at `84411f8`; no device, network
  fetch, commit or file change other than this note. The working tree also carried
  an unrelated uncommitted edit to `docs/guides/current-status.md` from another
  session at audit time; it was read but not touched, and the hash check below
  used the committed blob.
- `python tools/taskchain.py check` → `PASS: 19 chains cover 65 packets`.
- `python -B -m unittest discover -s tests -v` → `Ran 174 tests … OK (skipped=12)`.
- `git show 0e0d03b:docs/guides/current-status.md | sha256sum` and
  `git merge-base --is-ancestor 0e0d03b 88e1fcb` → hash and ancestry confirmed.
- `zstd -t` on the root archive → passes, 4,081,418,240 bytes; `tar -tf` on the
  boot archive → 437 entries, five named files present. Archive contents were not
  read beyond file names.
- `solidcraft-cli eval --in` on ten `.sc` sources and on the v17 STEP;
  `python3 tools/cad/step_inspect.py summary|features` on the v17 STEP.
- Not verified by me: any URL's current content, the six-file SHA-256 comparison
  against the live device (the device is out of scope), stock or price today, the
  kernel's 143-face sewing beyond the `eval` count, and whether R02/R07/R04/N01
  revision 2 notes are correct — that is the review's job, not this audit's.

## Handoff and correction links

- Current state: one audit note; no other document changed. It supersedes nothing
  and corrects no claim; it records where the trail stops.
- Concrete next actions, in order of value: (1) resolve the 2-Mics amplifier
  question from the HAT schematic and fix the two cost totals; (2) attach or
  remove the four price and version claims that have no source (`$34.99`/`£13`,
  the Voice PE 48 kHz FLAC YAML, the Radxa image/kernel line, the MA 2.11/2.10.12
  gate); (3) align the three stock cells with the register's own wording;
  (4) correct the backup stream size and the `models/README.md` structure
  sentence.
- Authorization: none of this is permission to edit another author's note,
  contact the device, or buy anything. Corrections belong in new notes citing the
  originals, or in a reviewed edit by their owner.

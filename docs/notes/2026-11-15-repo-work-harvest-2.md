---
title: Repository work harvest, second pass - what today's corrections left behind
date: 2026-11-15
type: project-learning
status: unreviewed
task: none
author: OpenCode (read-only review; one file written)
author_model: openrouter/deepseek/deepseek-v4.1-flash-1017
author_variant: unknown
sources:
  - Repository at commit 78cba58 (working tree clean when read), read 2026-11-15
  - git diff 9c9383d..78cba58 (nine commits: 2604526, 57ebe64, 317f72f, 16635bf, 96575d1, 68ea080, 120865a, cc0b7ab, 78cba58)
  - python -B -m unittest discover -s tests -> Ran 178 tests, OK (skipped=12) (same date)
  - python tools/taskchain.py check -> PASS 19 chains cover 65 packets (same date)
  - docs/notes/2026-11-15-repo-work-harvest.md (first pass, pinned to 9c9383d), read and not repeated
supersedes: []
---

## Summary

Second pass, several hours after [the first harvest](2026-11-15-repo-work-harvest.md).
That note pinned `9c9383d`; nine commits have landed since. **I do not repeat its
rows**; where one is still open it appears once, at the end, as a one-liner.

**The repository is still in better shape than its notes suggest.** The suite is
green at 178 tests (12 skipped), `taskchain.py check` passes at 19 chains / 65
packets, the 11 documentation checks pass, and the tree was clean at `78cba58`
when I read it. The day's corrections were real work, not relabelling: the v17 bay
inventory reproduced its probe before changing anything, and the four evidence
corrections changed what the comparison pages assert.

**The new problem is the same shape as the old one, one layer down.** Each
correction was applied to the file that was argued about and not to the files that
quoted it. So the amplifier correction now sits in `devices.md`, `enclosures.md`
and the roadmap while the note that supplies the `$59.90` total still says the
opposite; the v17 pocket correction is in `models/README.md` while the component
folder it describes still gives the withdrawn measurement as fact; and the new
status page's test total disagrees with its own per-module counts at the same
commit. Forty-six work items are listed below, 4 of them about half a day.

## Method and limits

- Read at `78cba58`, clean tree. Every citation was re-checked with `grep -n`
  against the committed files after the review, so line numbers are stable.
- While this note was being written, another session's uncommitted edits to
  `tools/activity.py` and `tests/test_activity.py` appeared in the tree. Nothing
  below cites them, and no claim here is about uncommitted work.
- Line numbers are current (`78cba58`), not the audit's pinned commit. Three
  audits pinned `84411f8`; where a cited line moved I cite where it is now and
  say so.
- "Stale" below means a statement a reader would act on that today's commits made
  false or half-true. "Loose end" means an audit named it and nobody fixed it.
- No device was contacted, no server was bound, no network was fetched, and no
  file other than this note was created or changed.
- Two behaviours below (parser accepting port 80 and a 70-character announcement
  name while the hub rejects both) were **run** against the modules, not inferred;
  see Verification.

## 1. Stale text today's commits created

Fourteen items. The cause is uniform: the corrected file was fixed, the files that
restate it were not.

| # | Stale statement | Evidence (file:line) | Why it matters | Size |
| --- | --- | --- | --- | --- |
| A1 | R01 and R02 revision 2 still say the 2-Mics HAT needs an external amplifier, while `devices.md`, `enclosures.md` and the roadmap now say the opposite. `$59.90` total A is cited from R01 by the very paragraph that refutes it | `docs/notes/2026-11-15-parts-inventory.md:150-152` ("has no speaker amplifier … needs **an amplifier between them**"), `:378` ("the 'cheap' route has an unpriced component"), `docs/notes/2026-11-15-complete-alternatives-comparison-revision.md:66` ("excludes an unpriced speaker amplifier") against `docs/comparisons/devices.md:58-62`, `docs/design/enclosures.md:108-110`, `docs/roadmap.md:158` | The only correction of the day that changes a published number. `devices.md:54` sources its totals from R01, so the page now contradicts its own source. Either add a dated correction banner to both notes or edit them under the owner's review; the anomaly triage is already settled (TPA2005D1, measured at −21 dBFS) | M |
| A2 | The v17 component folder — the "body reference" every design page links — still gives the withdrawn pocket as measured geometry | `models/components/rpispeaker-v17/README.md:17` ("it is a 31.10 × 66 × 7 mm"), `:42` ("so the bay is a 31.10 × 66 mm pocket 7 mm deep"), `:14` ("two M2.5 pilots") against `models/README.md:16-23` (lower footprint 31.10 × 28.125; "supersedes the earlier … 31.10 × 66 × 7 pocket") | `docs/design/rpispeaker-v17-speaker-mount-options.md:21` and `docs/design/rpispeaker-v17-fastening-options.md:7` both link this folder as the v17 body reference. A worker who opens it instead of the note cuts a 66 mm pocket in a 28.125 mm recess | M |
| A3 | The same withdrawn pocket is restated in a part README as the reference model's shape | `models/parts/dweii-671-case/README.md:86` ("the speaker side is a 31.10 × 66 × 7 mm pocket with two M2.5 pilots") | This is the aesthetic reference for the chosen case, so the error propagates into the part that will actually be printed | S |
| A4 | The extraction note still carries 31.85 × 66 × 7, blind pilots and "drilled from the back face", with no correction banner | `docs/notes/2026-11-15-rpispeaker-v17-extraction.md:51`, linked from `models/components/rpispeaker-v17/README.md:9` and `docs/design/rpispeaker-v17-speaker-mount-options.md:22` | Notes are append-only, so the fix is a banner like the one the other note got. The bay inventory (`:38-43`) says it supersedes these claims but the extraction itself gives no sign a reader would see | S |
| A5 | The correction banner added today covers only the 1.21 mm web, while that note's own table still proposes 31.10 × 66 mm as the fix | `docs/notes/2026-11-15-rpispeaker-v17-second-bay-corrections.md:22` (banner) against `:32` ("**31.10 x 66 mm**") | A reader who reads to the banner and stops takes 66 mm as current. The banner is one sentence short | S |
| A6 | The brand-new status page states a test total that its own per-module counts and the suite both contradict | `docs/guides/current-status.md:108` ("176 tests, 12 skipped, OK") against `:37` (77 in `test_web.py`), `:42` (12 discovery), `:43` (39 + 15 + 9), `:109` (11 docs) — 178 by my run | This is the page written today to be the single true answer to "what is Debra". The per-module figures are right for this commit; only the total is wrong, so the error is arithmetic in the summary line, not a stale run | S |
| A7 | The roadmap's WEB01 row still says the fix round is in progress; the outcome (code-r6, one low finding, fixed, awaiting re-check) exists only in the status page and the log | `docs/roadmap.md:207` ("`code-r5` … Fixes are in progress; the candidate is not approved") against `docs/guides/current-status.md:45-50`, `docs/updates/2026-11-15.md:566`, `:634` | The roadmap is the page a worker reads before choosing work; it makes r6 invisible and would send someone to re-do a finished fix round | S |
| A8 | The device-link port rule now contradicts itself one paragraph apart, and still allows a port the installer forbids | `control/web/README.md:157` ("an explicit port from 1 to 65535") against `:161-164` ("**Port 80 is refused on purpose**"), `control/web/install.py:69-70` (1024–65535), `control/web/server.py:585-589` | Three different port sets in two files. The sentence a reader copies from is the false one | S |
| A9 | The web design page still says the app does not discover addresses | `docs/design/web-control.md:280-281` ("but does not discover addresses, create stable identity") against `control/web/README.md:166` and `control/web/discovery.py:43-93` | Flagged as a post-pin risk by the drift audit (`2026-11-15-doc-code-drift-audit.md:210-211`) and not fixed. It is a WEB02 "roadmap/code gap" statement, so it inflates an open gap that has partly closed | S |
| A10 | "Getting started" still says the browser deployment is not recorded | `docs/guides/getting-started.md:41` ("Deployment not yet recorded") against `docs/guides/current-status.md:19-22` ("Its own page answers at … a logged deployment"), `docs/guides/web-control-quickstart.md:74-75` | The quickstart notices the disagreement and tells the reader to check the device instead of fixing it. Getting-started is one of the two "Start here" pages | S |
| A11 | The sentence corrected today for spend and CAD counts still under-lists the component envelopes | `AGENTS.md:35` ("the Pi 5, the three Pi Zero variants, the ReSpeaker 2-Mics HAT and ten speaker candidates") against `models/README.md:39` (three DWEII modules, modelled) and `models/components/rpispeaker-v17/` (present, no table row anywhere) | The file every session loads now under-describes the model set in the very bullet that was just fixed; a session reads "ten speaker candidates" and never learns the DWEII modules are modelled | S |
| A12 | The documentation map still describes three parts and calls the current case "historical" | `docs/README.md:84` ("tray, historical compact case and speaker carrier exist") against `AGENTS.md:35` ("six printable parts including a tub-and-lid case"), `models/README.md:59` (tub and lid, "Not printed, not fit-tested") | The map undercounts by three parts and labels the current case as superseded, so a reader looking for the case is told it is archive material | S |
| A13 | R01 still says there is no case or lid | `docs/notes/2026-11-15-parts-inventory.md:210` ("It has not been sliced, printed or fit-tested, and there is no case or lid") | This is the fourth copy of the claim removed from `AGENTS.md` today (`317f72f`). It is the note behind the `$59.90` figure the comparison pages cite | S |
| A14 | The index row for the v17 corrections still describes a narrower supersession than happened | `docs/README.md:60` ("the blind-pilot claim is superseded by the linked bay inventory") | The inventory also withdrew the pocket description and the wall that the 31.10 span was measured against (`docs/notes/2026-11-15-rpispeaker-v17-bay-inventory.md:32-38`). The row is the only summary most readers see | S |

## 2. What the three audits found and nobody fixed

Twenty-eight items, collected from the drift, coverage and evidence audits so they
stop being scattered across three notes. Each cites where the finding lives **now**;
the audit column is the original finding, which stays valid.

| # | Audit and original finding | Where it is still open (file:line) | Code or counter-evidence | Size |
| --- | --- | --- | --- | --- |
| B1 | Drift: `activity.log` is "one JSON line per finished task" | `docs/guides/scheduled-runner.md:33` | Two lines per task, `start` then `finish` (`tools/scheduled_runner.py:421`, `:438`) | S |
| B2 | Drift: run directory is `runs/<day>-<id>/` | `docs/guides/scheduled-runner.md:34` | `<day>-<8 hex>` from `uuid4().hex[:8]` (`tools/scheduled_runner.py:419`) | S |
| B3 | Drift: `prompts/` is runner state, "prompt files, one per task" | `docs/guides/scheduled-runner.md:36` | `ensure_layout()` creates no such directory and the token appears nowhere (`tools/scheduled_runner.py:123-131`) | S |
| B4 | Drift: the state table omits a file the runner creates | `docs/guides/scheduled-runner.md:30-36` (no `run.lock` row) | `.local/runner/run.lock` is real state (`tools/scheduled_runner.py:45`, `:163-192`) | S |
| B5 | Drift: WEB04 gap names only LVA, Sendspin and Snapcast units | `docs/design/web-control.md:425` | `SERVICES` also probes `pipewire.service` and `wireplumber.service` (`control/web/server.py:37-43`) | S |
| B6 | Drift: installer port/host rules undocumented | `control/web/README.md:77-86` (example only) | Port 1024–65535 and every `--host` port must equal it (`control/web/install.py:69-71`) | S |
| B7 | Drift: device-list limits undocumented | `control/web/README.md:155-160` | ≤50 entries, name ≤64, label ≤80, URL ≤200 (`control/web/server.py:607`, `:615`, `:628-629`) | S |
| B8 | Drift: status cache never mentioned | `control/web/README.md:13` | Most of status is cached 2 s, audio is re-read (`control/web/server.py:357-359`); only `docs/design/web-control.md:138` records it | S |
| B9 | Drift: default loopback authority unmentioned | `control/web/README.md:84-85` | With no `--host` and a loopback bind the server admits `127.0.0.1:<port>` itself (`control/web/server.py:656`) | S |
| B10 | Drift: `/api/status` carries an `auth` field the README never mentions | `control/web/README.md:31-34` | `data["auth"] = self.server.auth_mode` (`control/web/server.py:487`); the page depends on it | S |
| B11 | Drift: `hardware.json` presented as inert labels | `control/web/README.md:134` | Today's `57ebe64` made a malformed file refuse startup with a message instead of a restart loop (`control/web/server.py:678-683`); the README still says nothing about it | S |
| B12 | Coverage priority 3: run the browser tests in a regular job | `docs/notes/2026-11-15-test-coverage-audit.md:87` | Still opt-in only (`tests/test_web_browser.py:509`), so the 12 scenarios are skipped by every ordinary run | M |
| B13 | Coverage priority 4: installed bytes, modes, tampered release, interrupted rollback | `docs/notes/2026-11-15-test-coverage-audit.md:88` (its `tests/test_web.py:655` has since moved) | `tests/test_web.py:937` (`test_install_only_fixed_payload_idempotent_preserves_key`) asserts filenames and self-consistency, not the installed bytes or file/unit modes | M |
| B14 | Coverage: the discovery adapter test constructs its own data and cannot fail | `docs/notes/2026-11-15-test-coverage-audit.md:72` | `tests/test_discover.py:61-64` still builds the three keys itself instead of calling the adapter | S |
| B15 | Coverage: timeout assertions compare against the production constant | `docs/notes/2026-11-15-test-coverage-audit.md:73-74` | `tests/test_discover.py:101`, `tests/test_activity.py:185` | S |
| B16 | Evidence: "All sources checked 2026-11-15" is true of fetches, false of the Seeed cell | `docs/comparisons/devices.md:5`, cell in the Voice PE row at `:114` | Register `[S37]` says price and stock were not readable | S |
| B17 | Evidence: "in stock" where the register says "listed available" | `docs/comparisons/devices.md:121-123` | S10/S12/S13 wording in `docs/comparisons/sources.md` | S |
| B18 | Evidence: a same-day backorder observation with no register home | `docs/comparisons/devices.md:121` ("backorder with a 15 Dec 2026 restock") | No `[S#]` entry carries it | S |
| B19 | Evidence: Radxa image/kernel sentence has no key or date | `docs/comparisons/devices.md:107` | Register has no Radxa software entry | S |
| B20 | Evidence: "pins not soldered by default" is not in `[S42]` | `docs/comparisons/devices.md:99` | The register entry records only the pin table | S |
| B21 | Evidence: the MA version gate has no key or date | `docs/comparisons/music-playback.md:84` ("MA 2.11 beta; stable was 2.10.12") | `[S56]` covers only "technical preview" | S |
| B22 | Evidence: "Snapcast has no pause" is cited to a register entry that does not carry it | `docs/comparisons/music-playback.md:17` (claim; the audit's `:28` is now the protocol table) | The real support is R03's quotation of MA's docs | S |
| B23 | Evidence: combine-sink and echo-cancel numbers are `tested` with no result record | `docs/design/audio-outputs.md:138-140` | No record under `docs/testing/results/` | S |
| B24 | Evidence: the headphone-jack claim contradicts its own page | `docs/design/audio-outputs.md:40` ("the 3.5 mm jack is on the **headphone**") against `:112-115` ("Whether … Not tested") | Unchanged by today's commits | S |
| B25 | Evidence: the tray's hand arithmetic sums to 9284, not 9283 | `models/parts/zero2w-hat-tray/README.md:60` | One term is off by one; the conclusion is unaffected | S |
| B26 | Evidence: "Every folder here holds `<name>.sc`" is false for two folders | `models/README.md:4-9` | `models/components/rpispeaker-v17/` has no source; `pi5-5-model-b/` holds `pi5-reference.sc` | S |
| B27 | Evidence: the backup guide's Docker/Music Assistant row conflicts with the device records | `docs/guides/device-backup.md:26` ("Docker + Music Assistant container, 2.2 GB of images") | MA is the household instance and `40-music-assistant.sh` is not enabled (`docs/testing/results/2026-11-15-lab-pi5-lva-sendspin.md:68-71`, `:166-168`) | S |
| B28 | Evidence: archives are 0644 against the owner-only file rule | `docs/guides/device-backup.md:47` (claims mode 0700 directory only) | Device-local files; cannot be fixed from the repository, and not by this note | S |

Not carried over: the drift audit's `index.html` keyless warning was fixed today
(the page now says status read, volume and mute), and its hardware.json
crash-loop finding was fixed in code — only the README sentence remains (B11).
Coverage priorities 1 and 2 were fixed today by `cc0b7ab`; the new
`test_non_action_requests_never_control_services` also kills the `status_restart`
mutant that the audit recorded as undetected.

## 3. New gaps today's work exposed

| # | Gap | Evidence (file:line) | Why it matters | Size |
| --- | --- | --- | --- | --- |
| C1 | "One parser" is a parser, not a shared contract: the CLI prints records the hub silently drops | `control/web/discovery.py:12`, `:43-75` (accepts any `_debra._tcp` on port 1–65535 and any TXT name), `tools/discover.py:32-35` (no validation), against `control/web/server.py:585-589` (port 80) and `:606` (name 1–64) | Verified by running both: a `_debra._tcp` record on port 80 and a 70-character name both parse and would be printed by `tools/discover.py --json`, and `validate_device()` rejects both, so the hub never lists them. `control/web/README.md:174-175` ("Discovered records use the same … URL checks") is true of the hub and false of the CLI, and nothing states it | S |
| C2 | The port-80 rule was applied to links but not to the service's own port | `control/web/server.py:638` (`--port`, `type=int`, no range), `:449-450` (exact-string Host match), `:656` | The installer refuses anything below 1024 (`control/web/install.py:69-70`), so the guard exists on one path only. The day's own rationale — a browser drops `:80`, so the page cannot satisfy the Host check — applies to a standalone `serve` started with `--port 80` exactly as it does to a link | S |
| C3 | The re-statused discovery design page does not describe the behaviour a user will notice | `docs/design/device-discovery.md:3-12` | Nothing on the page mentions the 8 s browse timeout, the 30 s rescan, or that a failed or empty scan **clears** discovered entries; those live only in `control/web/README.md:166-175`. It also does not mention that an advertisement on port 80 disappears without a message. The page was re-statused by restating code in prose, which is the pattern that drifted in the first place | S |
| C4 | If the discovery thread cannot start, the hub serves configured-only with no signal | `control/web/server.py:93-99` | The failure is deliberately swallowed so configured links keep working, which is right, but neither `control/web/README.md:166-175` nor `docs/guides/web-control-quickstart.md:37-40` says discovery can be silently off for a reason other than a missing `avahi-browse` | S |

## 4. Pairs that now contradict each other because of today's corrections

Eight pairs. Four are direct products of a correction landing in one file only;
four are internal to a file edited today.

| Pair | Side A | Side B | Cause |
| --- | --- | --- | --- |
| 1 | `docs/roadmap.md:158` — "its claim that the 2-Mics HAT needs an unpriced amplifier is **wrong**" | `docs/notes/2026-11-15-complete-alternatives-comparison-revision.md:66` — "it excludes an unpriced speaker amplifier"; `docs/notes/2026-11-15-parts-inventory.md:150-152`, `:378` | Correction applied to the roadmap and two design pages, not to the two notes the totals come from (A1) |
| 2 | `models/README.md:16-23` — 31.10 × 28.125 footprint; the 66 × 7 pocket is superseded | `models/components/rpispeaker-v17/README.md:17`, `:42` — 31.10 × 66 × 7 pocket, 7 mm deep; `models/parts/dweii-671-case/README.md:86` | Index corrected, the folders it indexes left alone (A2, A3) |
| 3 | `docs/guides/current-status.md:19-22` — the device page answers at a `.local` address, from a logged deployment | `docs/guides/getting-started.md:41` — "Deployment not yet recorded" | Status page rewritten today; the older progress table not revisited (A10) |
| 4 | `docs/guides/current-status.md:45-50` — r6 returned one low finding, now fixed | `docs/roadmap.md:207` — "`code-r5` … Fixes are in progress" | Roadmap row not updated when the fix round landed (A7) |
| 5 | `control/web/README.md:166` — discovery is on when the service runs | `docs/design/web-control.md:280-281` — "does not discover addresses" | Design-page gap statement left behind by the discovery merge (A9) |
| 6 | `control/web/README.md:157` — port "from 1 to 65535" | `control/web/README.md:161-164` — "Port 80 is refused on purpose" | Today's paragraph added above an unchanged sentence (A8) |
| 7 | `docs/guides/current-status.md:108` — "176 tests" | The same page at `:37`, `:42`, `:43`, `:109`, which sum to 178, and the run itself (178) | Arithmetic slip in the page's own summary line (A6) |
| 8 | `AGENTS.md:35` — "six printable parts including a tub-and-lid case" | `docs/README.md:84` — "tray, historical compact case and speaker carrier" | Today's AGENTS.md correction against an unchanged map row (A12) |

## 5. What a careful person would do next

Spend the day making today's two corrections *finish*, and touch no code. Concretely:
one sitting on the amplifier (A1) — add a dated banner to R01 at
`parts-inventory.md:150` and to R02 revision 2 at `:66`, correct the "largest hidden
cost" paragraph and the `$59.90` narrative that depends on it, and make the
comparison page cite the corrected arithmetic rather than the note it contradicts;
then one sitting on v17 (A2–A5, A14) — rewrite the component README's two pocket
statements against the bay inventory, fix the same sentence in the 671 case README,
add a banner to the extraction note, extend the existing banner by one sentence, and
reword the index row; then one sitting on the numbers a reader trusts (A6–A13) —
178 tests on the status page and the roadmap's WEB01 row, the port range and the
"does not discover" sentence, the port-80 and cache behaviours in the design page,
the hardware.json sentence, and the two undercounts in `AGENTS.md:35` and
`docs/README.md:84`. The three audits' 28 loose ends (section 2) are
deliberately *not* in that day; they are cheap individually and none of them changes
a decision, so they belong in a batched "citation hygiene" pass after the
corrections are closed, with B11 and B26 folded in because today's work touched
them. Nothing here needs a device, a server, Chromium, or a commit from anyone but
the coordinator, and the enclosure lane stays blocked on a photograph, not on these
edits.

## Verification

- Working directory `/home/james/Projects/debra`, commit `78cba58`; the tree was
  clean when the review started and gained another session's uncommitted
  `tools/activity.py` / `tests/test_activity.py` edits while it was written. All
  citations are to the committed tree.
- `python -B -m unittest discover -s tests` → `Ran 178 tests` / `OK (skipped=12)`.
- Per module: `tests.test_web` 77, `tests.test_web_browser` 12 (skipped),
  `tests.test_docs` 11, `tests.test_activity` 39, `tests.test_taskchain` 15,
  `tests.test_scheduled_runner` 9, `tests.test_discover` 12, `tests.test_runner` 3.
- `python tools/taskchain.py check` → `PASS: 19 chains cover 65 packets; starter
  cards/paths valid.`
- Parser-versus-hub check, run as a one-off `python3 -B -c` against the modules:
  `discovery.parse()` returns a record for a `_debra._tcp` line on port 80 and for
  a 70-character TXT name; `server.validate_device()` rejects both
  (`Port 80 is unsupported…`, `Device name must be 1-64…`).
- Grep scans for the retired figures (`31.85`, `66 mm`/`× 66`, `1.21`, `blind`,
  `amplifier`, `no case or lid`) across `docs/` and `models/`; every surviving hit
  is either a dated record, a note with a banner, or one of the rows above.
- Not tested: anything on a device, any live network or mDNS, any bound port, and
  the two `M` coverage items (B12, B13), which were read, not written.

## Handoff and correction links

- This note is a review, not an assignment. A1–A14 and C1–C4 need the coordinator's
  triage before anyone edits the cited files; A1 and A2 change what a design or
  purchase reader acts on, so they should be owned rather than self-selected.
- Still open from [the first harvest](2026-11-15-repo-work-harvest.md), unchanged
  today, one line each: `docs/design/enclosures.md:86-88` ("nothing here is in
  SolidCraft yet"); `docs/design/audio-outputs.md:173` ("a device whose power rail
  still sags"); `docs/task-chains.md:4`, `:38` (63 packets, still 65); the
  `debra-advertise` unit still exists on one machine only (`tools/discover.py:7`,
  `docs/updates/2026-11-15.md:607`); `tools/device/lab-pi5/README.md:22-31` still omits
  `70-audio-level-probe.sh`; `docs/README.md:9-40` still omits `docs/updates/` and
  `docs/design/rpispeaker-v17-fastening-options.md`; `docs/guides/pi5-lab-preparation.md`
  is still unreferenced and still describes preparation that already happened.
  `models/README.md:4-9` is now B26 above, so it is not repeated here.
- If a later commit fixes a row, record it in a new dated note that cites this one
  and the first harvest rather than editing either.
- Authorization: none of this is permission to edit another author's note, contact
  the device, print a part or install a service.

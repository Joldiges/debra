---
title: Repository work harvest - what is worth fixing, with citations
date: 2026-11-15
type: project-learning
status: unreviewed
task: none
author: OpenCode (read-only review; one file written)
author_model: openrouter/deepseek/deepseek-v4.1-flash-1017
author_variant: unknown
sources:
  - Repository at commit 9c9383d ("Show discovered Debra devices in the hub, from one parser"), working tree clean, read 2026-11-15
  - tools/taskchain.py check -> PASS 19 chains / 65 packets (same date)
  - python -B -m unittest discover -s tests -> Ran 175 tests, OK (skipped=12) (same date)
supersedes: []
---

## Summary

I read the tracked repository and looked for work that is worth doing: statements
that are now false, documents that contradict each other, and things a reader is
told to open that they cannot find. Every proposal below cites a real line at
commit `9c9383d`. Proposals that the roadmap or `docs/updates/` already owns are
excluded, including the ones the coordinator recorded as known-but-unfixed.

**The repository is in better shape than its own documents suggest.** A relative
link-and-anchor scan over every tracked `*.md` found **0 broken links**. The
backticked-path scan found **one** missing file (`scripts/debra-setup.sh`), and
that one is explicitly disclosed as history-only at `AGENTS.md:33` and
`docs/legacy-findings.md:16-18`. `python tools/taskchain.py check` passes
(19 chains / 65 packets) and the full suite is green (175 run, 12 skipped). The
`docs/updates/2026-11-15.md` log is unusually honest — it records its own
mistakes, its own wrong model choice, and a red that was a browser crash rather
than an assertion. The problem is almost entirely that **status prose drifts
faster than the code it describes**, not that the project is disorganised.

No proposal needs a board flashed, a live service changed, or host tooling
installed. None is larger than a day of edits; there is nothing L-sized here,
which is itself the finding: the gaps are wording, status and indexes, not
missing engineering.

## Method and limits

- Read at commit `9c9383d`. During the review HEAD moved from `84411f8` to
  `9c9383d`; one finding (discovery being undocumented) was partly fixed by that
  commit and is reported here only in its surviving form.
- Every line number was re-checked against the committed tree after the review,
  so it is stable. The working tree kept moving: at the end it held uncommitted
  edits to `models/README.md`, `docs/README.md`,
  `docs/design/rpispeaker-v17-*.md` and `control/web/{server.py,assets/index.html}`,
  plus four untracked notes. None of that is cited, because none of it is
  committed; see the last bullet of the handoff section.
- I did not contact a device, touch audio, or modify any file except this note.
- "Contradiction" below means two statements in tracked files that cannot both be
  true, both cited. "Drift" means duplicated content whose copies have already
  diverged.

## Ranked proposals

Ordered by what would hurt most if left alone, not by how easy it is. `S` is
under two hours, `M` is roughly half a day.

| Proposal | Evidence (file:line) | Why it matters | Size | Prerequisite |
| --- | --- | --- | --- | --- |
| Rewrite the "What actually exists today" bullets in `AGENTS.md` against today's tree | `AGENTS.md:34` ("power rail sags … resets the board"), `AGENTS.md:35` ("daily reported-cost budget", "one reference stack assembly, and one printable tray … there is no case or lid") | This is the first file every agent and every new session loads. Three claims in two bullets are now false: the supply report has been superseded (`docs/project-brief.md:200-203`, `docs/guides/getting-started.md:47-50`, `docs/README.md:25`); there is no local spend cap (`tools/scheduled_runner.py:49`, `docs/guides/scheduled-runner.md:21-23`); `models/` now holds four assemblies and six printable parts including a tub-and-lid case (`models/README.md:43-46`, `models/README.md:56`) | S | none |
| Retire or re-status `docs/design/device-discovery.md` | `docs/design/device-discovery.md:3` ("Status: **proposal, unimplemented**") against `control/web/README.md:162` ("Local `_debra._tcp` mDNS discovery is on when the web service runs") and `control/web/discovery.py:62-65` | The design page now contradicts shipped code: the hub browses, caches and serves discovered devices, and `tools/discover.py` is a front end over the same module. The page also specifies a TXT record with device id, model, release and protocol (`docs/design/device-discovery.md:37-38`), while the implementation reads `label` only — so an implementer reading the design builds the wrong advertisement | S | none |
| Fix the self-contradiction about whether the HAT's component positions are known | `docs/design/enclosure-arrangements.md:171-172` ("positions are still estimates … a hole cannot be cut for anything yet") against `docs/design/enclosure-arrangements.md:50` ("the HAT's positions are now **sourced from Seeed's board file**") and `models/README.md:35` | This one sentence decides whether the enclosure lane can cut microphone ports, which is the gate for the whole case. The same page says both "sourced" and "estimate", so the reader must guess which is current; the models agree with "sourced for X/Y, heights estimated" | S | none |
| Decide the fate of `docs/guides/current-status.md` | `docs/guides/current-status.md:3-8` ("Debra is a planning and reference documentation project … reflects the repository baseline of 2026-11-14"), `docs/guides/current-status.md:20-21` ("not evidence that any appliance component works") | The page that answers "what is Debra today" is a day behind the device record it contradicts: a satellite and player run end to end on the lab Pi (`docs/README.md:25`). It is also reachable only from two notes, so nobody is prompted to fix or retire it. Either point it at `docs/guides/getting-started.md` or rewrite it | S | none |
| Reconcile the enclosure requirements with the speakers actually chosen | `docs/design/enclosures.md:86-88` ("Status is 'researched, not modelled' for all of them: nothing here is in SolidCraft yet") against `models/README.md:37` (ten Adafruit/Visaton/Dayton drivers "modelled") and `docs/design/enclosure-arrangements.md:16-22` (the chosen speakers are DWEII housed modules, not in that table) | The document that assigns enclosure work states a maturity that is already past and an inventory that excludes the parts James picked. A worker handed `enclosures.md` would model ten drivers that are no longer the target and would not know the DWEII modules exist | M | none |
| Put the `debra-advertise` unit in Git, or drop it from the docstring | `tools/discover.py:6-7` cites "the `debra-advertise` user unit" (also `control/web/README.md:162`) | Discovery is the only feature that makes a second device appear without editing a file, and the unit that publishes `_debra._tcp` exists on exactly one machine, created by hand. No clone can reproduce it, so the feature is unrepeatable off the lab Pi | M | Blocked: a decision that device unit files belong beside the others in `tools/device/lab-pi5/`. Authoring only — installing it on any device is a separate live operation with a named target |
| Correct the packet count in the worker entrypoint | `docs/task-chains.md:4` ("canonical 63-packet backlog"), `docs/task-chains.md:38` ("All 63 packets are mapped below") | The roadmap holds 65 packets, and the tool proves it: `taskchain.py check` prints "19 chains cover 65 packets". This page is what a self-selecting worker reads first, and a wrong total invites someone to conclude a packet is unmapped and invent a duplicate | S | none |
| Remove the stale power sentence from the audio design page | `docs/design/audio-outputs.md:173` ("on a device whose power rail still sags") | The page's own header (`docs/design/audio-outputs.md:12-13`) marks it historical, and the brief says not to present earlier fault evidence as current (`docs/project-brief.md:200-203`). It is the sentence that keeps re-seeding the false claim in `AGENTS.md:34` | S | none |
| Put a banner on the result record whose arithmetic was refuted | `docs/testing/results/2026-11-15-lab-pi5-audio-levels.md:43-46` ("doubling the volume moves the measurement by … 6.02 dB … pick its level by arithmetic rather than by ear") against `docs/notes/2026-11-15-audio-and-enclosure-corrections.md:27` ("The old table does **not** show +6 dB for doubling") | The refutation exists, but only in the map (`docs/README.md:26`) and a separate note; the record itself still asserts a straight-gain model that its own rows do not support, and it is cited as device evidence through `docs/comparisons/sources.md:18` | S | none |
| Mark `docs/guides/pi5-lab-preparation.md` as superseded or link it | `docs/guides/pi5-lab-preparation.md:3-8` ("not yet device-tested … No card has been written, key generated, Pi contacted"), `docs/guides/pi5-lab-preparation.md:101-102` (no verified snapshot/restore exists) | A 133-line preparation procedure with a destructive Imager stage, no inbound link from anywhere, and no note that the preparation it plans has already happened. The risk is not that it is old; it is that a reader follows it to image a card for a device that already exists | S | none |
| Complete the documentation map | `docs/README.md:9-39` omits `docs/updates/` while `docs/ai-workflow.md:69-70` tells every resuming reader to open "the current `docs/updates/` entry", and omits `docs/design/rpispeaker-v17-fastening-options.md` while linking its companion at `docs/README.md:62-65`; `docs/updates/README.md:1-5` is itself unreferenced | Two pages a reader is told to read are absent from the index, and the 7-option fastening study (with its recommendation and its deciding measurement) is invisible next to the mount study that is linked | S | none |
| Add the missing row to the device script table | `tools/device/lab-pi5/README.md:22-31` (table of ten scripts) versus the committed `tools/device/lab-pi5/70-audio-level-probe.sh` | That table is the only index of device scripts. The one script a reader cannot identify is the level probe — which is also the script behind the refuted arithmetic above | S | none |
| Repair the folder contract stated in the models index | `models/README.md:5-11` ("Every folder here holds … `<name>.sc` the editable source; the model is rebuilt from this") versus `models/components/rpispeaker-v17/` (README and renders only) and `models/components/pi5-5-model-b/` (`pi5-reference.sc`) | The stated invariant is how a reader decides whether a part is editable or a frozen snapshot. It is false for the folder the "current direction" of the lane depends on (`models/README.md:13-20`), whose source STEP lives outside the repository | S | none |

## Duplicated or contradictory content

Ten contradictions, plus two duplicated inventories that have already drifted.
`C1` and `C2` are the same underlying claim in two files; both are live.

| # | Contradiction | Where |
| --- | --- | --- |
| C1 | Power rail "sags … resets the board" vs "the changed supply mostly resolved the lab instability … do not describe it as a current measurement" | `AGENTS.md:34` vs `docs/project-brief.md:200-203`, `docs/guides/getting-started.md:47-50`, `docs/README.md:25` |
| C2 | "a device whose power rail still sags" vs the same brief, and vs the page's own "historical" header | `docs/design/audio-outputs.md:173` vs `docs/design/audio-outputs.md:12-13` |
| C3 | "a daily reported-cost budget" vs `daily_budget_usd: None` ("no local cap") | `AGENTS.md:35` vs `tools/scheduled_runner.py:49`, `docs/guides/scheduled-runner.md:21-23` |
| C4 | "one reference stack assembly, and one printable tray … there is no case or lid" vs four assemblies and six parts, including "Tub and lid" | `AGENTS.md:35` vs `models/README.md:43-46`, `models/README.md:56` |
| C5 | "63-packet" / "All 63 packets" vs the tool's "19 chains cover 65 packets" | `docs/task-chains.md:4`, `docs/task-chains.md:38` vs `tools/taskchain.py check` output; the 65 figure is also recorded at `docs/notes/2026-11-15-browser-docs-handoff.md:32` |
| C6 | "not evidence that any appliance component works" vs a voice+music result on the lab device | `docs/guides/current-status.md:20-21` vs `docs/README.md:25` |
| C7 | HAT "positions are still estimates … a hole cannot be cut" vs "positions are now sourced from Seeed's board file" | `docs/design/enclosure-arrangements.md:171-172` vs `docs/design/enclosure-arrangements.md:50`, `models/README.md:35` |
| C8 | "nothing here is in SolidCraft yet" vs "Ten driver envelopes … modelled" | `docs/design/enclosures.md:86-88` vs `models/README.md:37` |
| C9 | Discovery "unimplemented" vs "discovery is on when the web service runs", plus a parsers module and a CLI | `docs/design/device-discovery.md:3` vs `control/web/README.md:162`, `control/web/discovery.py:62-65` |
| C10 | "Every folder here holds … `<name>.sc` the editable source" vs two folders that do not | `models/README.md:9` vs `models/components/rpispeaker-v17/`, `models/components/pi5-5-model-b/` |

**Drifted duplicates** (not counted above, because both copies are technically
true but they answer different questions):

- There are **three** descriptions of where the enclosure lane is:
  `docs/design/enclosures.md:84-104` (ten drivers, "researched, not modelled"),
  `docs/design/enclosure-arrangements.md:14-38` (DWEII modules, cylinders are the
  wrong shape), and `models/README.md:29-37` (both sets, with per-row status).
  Choosing one as canonical is the M-sized item above.
- `AGENTS.md:33-39` restates the status table in
  `docs/guides/getting-started.md:38-45` in prose. Prose restatements of a
  table drift silently — C1, C3 and C4 all came from that one bullet block.

## Referenced but missing

Very little, which is worth saying plainly: the link and anchor scan is clean
(0 broken across every tracked `*.md`), and the path scan found one absent file
that is already disclosed as history-only.

- **`debra-advertise` unit** — cited as existing at `tools/discover.py:6-7` and
  as live behaviour at `control/web/README.md:162`; no unit file, script or
  template for it is tracked anywhere. This is the only missing artifact that
  blocks a shipped feature from being reproduced on a second device.
- **`scripts/debra-setup.sh`** — absent from the working tree but named in
  `docs/legacy-findings.md:3-18`; correct as it stands, because the note says how
  to recover it from history (`git show bc81d9b:scripts/debra-setup.sh`).
- **The v17 body's source STEP** — lives at a path outside the repository
  (`models/components/rpispeaker-v17/README.md:5-7`), which is disclosed. It is
  listed only because the lane's "current direction"
  (`models/README.md:13-20`) is unreconstructable without it, and the folder
  contains no `.sc` at all.
- **Not missing, but unreachable:** `docs/updates/README.md`,
  `docs/guides/pi5-lab-preparation.md`, `docs/design/rpispeaker-v17-fastening-options.md`,
  `docs/guides/current-status.md` and `docs/outline.md` have no inbound link from
  any tracked file. `docs/outline.md` is a 15-line checklist whose own header
  marks it historical, so leaving it unlinked is defensible; the other four are
  in the table above.

## What I would do first and why

Start with `AGENTS.md:34-35`, then `docs/design/enclosure-arrangements.md:171-172`,
then `docs/design/device-discovery.md:3`. All three are single-sentence edits on
pages that other work is planned from, and all three are wrong in a way that
causes a *decision* rather than an inconvenience: `AGENTS.md` tells every agent
that the one working device is unreliable, that spend is capped, and that there
is no case or lid, so a fresh session re-plans finished work and treats a
working device as a hazard; `enclosure-arrangements.md` simultaneously says the
microphone positions are known and unknown, which is precisely the gate on
cutting a port, so the enclosure lane either stalls on a solved problem or cuts a
hole from an estimate; and `device-discovery.md` says the feature does not exist
while `control/web/README.md:162` says it is running, so an implementer either
rebuilds it or designs the wrong advertisement. Fixing all three costs under two
hours, changes no code, and removes three of the ten contradictions. The
`task-chains.md` count (C5) and the `current-status.md` page (C6) belong in the
same sitting, because they are the same class of defect: prose that was true on
2026-11-14 and is now the only place a reader can find a wrong answer.

## Verification

- Working directory `/home/james/Projects/debra`, commit `9c9383d`, clean tree.
- `python tools/taskchain.py check` → `PASS: 19 chains cover 65 packets; starter
  cards/paths valid.`
- `python -B -m unittest discover -s tests` → `Ran 175 tests in 13.192s` /
  `OK (skipped=12)`.
- Relative link/anchor scan over all tracked `*.md` → 0 broken links.
- Backticked `tools/*.py` and `scripts/*.sh` paths → one absent file
  (`scripts/debra-setup.sh`), disclosed as history-only.
- Not tested: anything on a device; no live service was read or changed.

## Handoff and correction links

- This note is a review, not an assignment. Every row needs the coordinator's
  triage before anyone edits the cited files, and the two `M` rows need a scope
  decision rather than a worker.
- Items deliberately **not** proposed because the roadmap, the task registry or
  `docs/updates/2026-11-15.md` already owns them: the `docs/guides/device-backup.md`
  recovery ordering, the no-auth prototype mode, merging discovered devices into
  the hub, the WEB acceptance criteria rewrite, the N01 "seven-row copy map"
  miscount (`docs/updates/2026-11-15.md:676-678`), and the four revision-2
  research notes' standing `status: unreviewed` frontmatter (that is the
  documented convention, `docs/README.md:137-139`, not a defect).
- If a later commit fixes any row here, record it in a new dated note that cites
  this one rather than editing this file.
- **Concurrent work to check before assigning edits.** While this note was being
  written, another session had uncommitted changes in the tree and two
  untracked audit notes: `docs/notes/2026-11-15-doc-code-drift-audit.md` (pinned
  to `84411f8`; compares web-control and tooling prose claim by claim) and
  `docs/notes/2026-11-15-test-coverage-audit.md`. That audit already covers
  `docs/guides/current-status.md` as "understates what exists", so my C6 row and
  the table's fourth row may be the same edit seen from two directions — check
  it before assigning either. The same working tree also had modifications to
  `models/README.md`, `docs/README.md` and
  `docs/design/rpispeaker-v17-fastening-options.md`, which are the files behind
  three of my rows; my citations stay valid because they are pinned to `9c9383d`,
  but the coordinator should confirm those rows are not already fixed. Nothing
  above is a claim about uncommitted work, and nothing in that tree was edited by
  this review.

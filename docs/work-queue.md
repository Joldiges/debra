# Work queue

Execution state: what is being worked on, by whom, and what is waiting. The
[roadmap](roadmap.md) is the plan, and [notes](notes/) hold findings. This page
holds none of that — only where each item stands right now.

For the whole product rather than individual execution rows, use the
**[colour-coded progress and dependency diagrams](progress.md)**. Update this
queue and the roadmap, then run `python3 tools/progress.py` to refresh that view.

Why it exists: work felt like it only happened when James asked for it, because
nothing durable recorded the next item. A harvest note lists findings; it does
not say which ones are claimed, finished, or stuck. This page does.

Visible: the activity TUI's Todos tab (`python tools/activity.py --todos`)
answers "what could run next" from what already records it — this page's Queued
table, the entries of the [research backlog](research-backlog.md), and the
task-chain catalog with its claim registry in `<git-common-dir>/debra-work/`.
Backlog entries that are not-ready, duplicated or already run are reported
rather than hidden. It reads those files and never keeps a fourth list that
could disagree.

## States

| State | Means |
|---|---|
| **queued** | ready to start, not started, no owner |
| **running** | one worker owns the files and is editing them |
| **review** | the worker reports done; a different check must read the diff before it lands |
| **done** | merged, with the commit that proves it |
| **blocked** | cannot proceed; the blocker is named, and it is not a missing instruction |

A worker owns its files exclusively. Two workers never edit one file. Workers do
not commit, push, or approve their own work.

Item ids such as `A1`, `B16` or `C1` are [harvest](notes/2026-11-15-repo-work-harvest-2.md)
findings, not roadmap packets; most rows cite the timestamps or commits where the
item was raised, and a row that names an audit says which one. Roadmap packets
(`N02`, `D02`, `WEB03`) keep their own ids.

## Running

| Packet | Item ids | Files | Notes |
|---|---|---|---|
| Acceptance review `code-r10` | WEB01 | `.local/reviews/code-r10-20261115/` | independent, `gpt-6.1-sol`; frozen on `e4b16e0` (re-verified byte-identical), judging R9-01…R9-06, re-running the nine r9 survivor transforms and five new ones, and running the offline and browser suites in a scratch copy |
| Re-review `docs-r3` | Z01, T01 | `.local/reviews/docs-r3-20261115/` | independent, `gpt-6.1-sol`; hash-bound on the two documents (`Z01-armv6.md` `6b205f5b…`, `acceptance.md` `930e9d84…`), judging the seven docs-r2 findings and the new historical-library evidence |

## Done this round

| Packet | Item ids | Proof |
|---|---|---|
| Wi-Fi onboarding, identity and first baseline | N02 | `cd4790f`, fixed by `40ef8dc` and `ef370d5` — 67 tests; **not run on a device** |
| Setup service at boot | N02 | `cf88922` — system unit, installer, 24 tests; never loaded by systemd |
| The r1 review's remaining blockers | N02 | `ef370d5` — reserved admission, active-profile check, classified errors, baseline retry and atomicity, form kept while polling |
| Nearby-network picker in the setup page | N02 | this round — the radio is scanned once before the access point is raised, so a beginner chooses a name instead of typing it; 13 setup browser scenarios |
| The r3 review's blockers | N02 | `5c8fde4` — the SSID is NetworkManager's byte list (proven against libnm), the hostname is reconciled every boot, the baseline pointer is verified or adopted, tar metadata comes from the read descriptor, claim/settle are atomic, and the page keeps a name's spaces and says "not known yet" instead of claiming a handover. Both surviving r3 mutations are now caught |
| Four installer gaps: retained releases re-verified, staging files created 0600, the device list validated in `install()`, and a start limit in `[Unit]` | B13, WEB03 | `6b762ba` — each checked by reverting it and watching a named test fail; `--restore` now refuses a unit whose release no longer matches its content address |
| The r4 review's blockers | N02 | `a550a96` — a claim no longer survives a reboot, the failure rearm holds the admission lock, the setup password is generated once and reused, state schema 2 carries a monotonic revision and its consistency rules, baseline adoption is one bounded validator, a failed pointer write is adopted rather than re-captured, and the page accepts a newer answer and can leave the uncertain card. All six surviving r4 mutations plus a request-time status guard now fail a named test |
| The r5 review's narrow findings | N02 | `f9c5e7b` — answers are now ordered against each other by revision, `do_POST` has a fixed-sentence boundary, and the three properties a revert could silently remove (rearm-in-lock, superseded failure, persisted capture error) have tests. Schema 2 is documented. R5-06 remains bounded and documented |
| The r6 review's findings | N02 | this commit — the capture-failure record has its own second-process test (the r5 test reached only the pointer-write branch); `do_GET` has the POST boundary; the handler logs the exception's class and releases a reservation it cannot hand on; `--enable` accepts the absolute wants link systemd writes; the schema-1 migration fills every field the old record never wrote; the setup password and the `first-boot.md` rows are described as they are. Eight reversals all killed |
| The r7 review's blockers | WEB03 | `709b3df` — the documented rollback command runs without `--host` and refuses an unstartable unit, the keyless dashboard carries its own warning, HAT detection needs a vendor and a two-mic word, parser refusals reach the page, a 390 px page holds a long sink identity, an oversized valid body is refused, same-device detection is the exact host or its `.local` alias, a Switch link is not refused as cross-site, and the labels name their sources |
| The r8 review's blockers | WEB03 | `f974f7f` — restore reads `ExecStart` with a systemd decoder so a HOME with a space, `%` or `$` round-trips; the launchability guard reads only `[Service]`, honours a reset and `-`, and requires a complete release matching its content address; a write outcome sits beside Apply at 390 px; the No-HAT row reports no family verdict and `12-Mics` no longer matches two-mic; two equal advertisements count as two; a late Setup response cannot repaint cleared rows. Three test gaps closed, including labels beside disabled controls and pre-`app.js` request recording. 20 reversals all killed |
| The r9 review's findings | WEB03 | this commit — restore now accepts **only** a unit this installer wrote (marker line, one `ExecStart` in `[Service]`, every argument double-quoted with only `\\`, `\"`, `%%`, `$$`), so it can no longer validate a path systemd would not start (`he\x20home`); the release boundary refuses a linked release, a linked payload file or directory, a traversing or non-payload entry point, and a release whose content no longer matches its name; four safety tests that only looked like tests now fail their reversals (digest compare, linked release, linked named file, unit absent at publication); the control sweep reads the pre-wrapper request log, so a captured `fetch` cannot hide a write; a Setup read is bound to the session only (an audio write no longer discards a valid answer, a pending read no longer blocks a re-pair) and the held-*error* arm is tested; an audio write settling after Disconnect no longer throws on the null state; the refusal count is described as refused records. Nine reversals all killed |
| The setup r7 review's findings | N02 | this round — the schema-1 migration has a floor (`MANDATORY_1`): a record missing any field every prototype revision wrote is refused as damage instead of being filled into a fresh, unconfigured journey, so `{"schema": 1}` no longer raises a new access point; `--enable` compares **resolved** destinations, so a link spelled `../jump/../debra-setup.service` through a symlinked directory is refused when it lands on a foreign unit, and an absolute target carrying the preparing host's mount point is refused as a path that names nothing after boot; a redirect marks the request answered before its body is written, so a failed body write cannot append a 500 to a partial 302. The four survivors are now killed by named tests, including the GET already-answered guard and the POST exception class the journal prints |
| The r2 review's blockers | N02 | this round — the profile is written where NetworkManager keeps it and promoted to autoconnect only after the join is verified; a per-attempt token replaces the SSID check; the reservation is released when the reply cannot be written; the country is set after the AP is down; the portal prints the address it is served on; the baseline is never overwritten, never archives itself, and `latest()` verifies the hash; the page keeps what was typed across a poll and shows a baseline failure |
| Browser proof of the device list | — | `test_development_bypass_and_device_links` already drives the configured and discovered badges, the same-device case, a literal label, a discovery start failure, an empty scan and a refused advertisement |
| Browser proof of the setup page | N02 | `508a7f9` — 7 Chromium scenarios; the page was unreachable and the tests caught it |
| Installed-artifact tests and atomic rollback | B13 | `508a7f9`, `9d11d08` — 16 tests; two real gaps recorded rather than asserted away |
| Dashboard Setup card | WEB03 | `8b05215` — 21 tests, read-only, every choice disabled with its reason |
| First-boot design page | N02 | `b136db2`, kept in step with the code by `40ef8dc` |
| A card that can be booted into the trial, and a written trial | N02 | `92f31c7` — `--enable` links the unit into `multi-user.target.wants` so a tree prepared with `--root` starts at first boot; 7 tests. `docs/testing/first-boot-trial-plan.md` states what one run would prove, the run sheet, the recovery path and the three questions only James can answer. No card prepared, no service started |
| Speaker cover carrying the four-screw pattern | — | `4b62ff6`; `SQ_PITCH` still an assumption |
| Notices checklist in the activity TUI | — | `3f7236a` — 22 tests, driven in a real pty |
| The v17 body as an editable source | A2 | `f7b2163` — reconstruction, honest about what it cannot reproduce |
| Web pages matched to the server | A8, A9, B5–B11, C3 | `f35d47f` |
| Evidence claims matched to sources | B16–B25, B27, B28 | `5e83273` |
| Eleven stale claims and the optional studies indexed | A1, A3–A7, A10–A14 | `7918ccd`, `503ce7f` |
| Runner guide and models index | B1–B4, B26 | `f5da00d` |
| Activity TUI and the runner elapsed-time fix | `--tui`, B15 | `a6732d1` |
| Idle reasons in the session table | — | `5d329ec` |
| Discovery contract: one acceptance rule, named rejections | C1, C2, C4, B14 | `f2b5c72` |
| Demo case: Pi Zero + DWEII 671, bays, lid with mic and LED openings | — | `3d7c07f` |
| Tabbed TUI with stable scroll positions | — | `d4ba492` |
| Queue refiller from a repository backlog | — | `059a3ba` |
| The lid checked against the reconstructed body | D02 | `models/assemblies/rpispeaker-v17-body-lid/` — 0 mm³ interference at the lid's defaults, with a 0.5 mm per-side oversize control that is caught; a composed assembly, no duplicate `.sc`; still nothing printed |
| Tabbed TUI that redraws only changed lines, and drops columns instead of truncating them | — | this round |
| Two unattended studies: the ARMv6 audio stack, first-boot identity | — | `35d43c3` |
| Todos tab: what nothing is working on | — | `fafb8f2`, fixed by `f355347` and `04b0867`, then test tightening — the first review found it read `.git/state.json` instead of `.git/debra-work/state.json`, so claims were never seen; 19 Todos tests, five of them against a real registry file |

## Queued

| Packet | Item ids | Why it is next |
|---|---|---|
| Device run of the onboarding flow | N02 | needs a spare card and one of the next Pis; nothing in `control/setup/` has touched a radio |
| Captive-portal probes may never arrive | N02 | researched: NM shared mode starts dnsmasq without `--no-resolv`, so with no uplink the probe names cannot resolve. The smallest fix is one file, `dnsmasq-shared.d/50-debra-captive.conf` with `address=/#/<AP address>`; see [the note](notes/2026-11-15-captive-portal-dns-in-nm-shared-mode.md). Not implemented: `control/setup/` is frozen under review, the AP address should be made explicit first, and dnsmasq presence plus the real `--conf-dir` need a device check |
| A real NetworkManager has never loaded the Wi-Fi profile | N02 | the profile is written into `/etc/NetworkManager/system-connections` with `autoconnect=false` and promoted after a verified join. That the keyfile plugin reads it, that it survives a reboot, and that the promotion takes effect are all unproven |
| The radio handover has never run | N02 | stop the access point, associate, verify, and restore the access point on failure is only exercised against the fake. No `nmcli`, `hostnamectl` or `raspi-config` call has been made by Debra |
| No baseline restore demo | N02 | a baseline is captured and can be inspected, but nothing restores from one, so "recovery" is untested in the direction that matters |

## In review

Coordinator-assigned subagent work creates no claim, so the activity TUI's Todos
tab still lists Z01 and T01 under "Spawnable now" until the coordinator advances
those chains. They are not available for reassignment: their deliverables exist
and are waiting for the review rows below.

| Item | Reviewer | Outcome |
|---|---|---|
| First-boot setup, r7 (`e4b3125`) | `gpt-6.1-sol`, independent | **changes requested** — seven of eight r6 findings closed and all nine supplied reversals killed, but three reproduced regressions: a schema-1 file that was never a record (`{"schema": 1}`) was filled into an unconfigured device that raised a fresh access point; `--enable` followed no symlinks, so `../jump/../debra-setup.service` was accepted while resolving to a foreign unit, and a host-prefixed absolute target was accepted too; a failed body write after a captive 302 appended a 500 on the same connection. Two behaviour-changing mutations survived every test. All repaired; awaits re-review. Verdict: `.local/reviews/setup-r7-20261115/verdict.md` |
| T01 acceptance and test tiers (`docs/testing/acceptance.md`) | `gpt-6.1-sol`, independent | **changes requested, twice** — r1: the detailed browser scope was not mapped and a slow-but-correct restore could pass; r2: the browser submap still lacked labels/contrast, the WEB07 metric inventory and recovery/report fields, and the new performance wording left an executed-but-failing run `not-run`. Both rounds addressed: a browser table with a recovery/report column, and three distinct outcomes (no run, no agreed limit, missed limit = **fail**). Awaits re-review. Verdicts: `.local/reviews/docs-r1-20261115/` and `docs-r2-20261115/` |
| Z01 ARMv6 reconnaissance (`docs/research/Z01-armv6.md`) | `gpt-6.1-sol`, independent | **changes required, twice** — r1: the leading blocker generalized broken piwheels artifacts to all 32-bit ARM, the experiments could not produce their promised evidence, and the historical leads had no disposition. r2: E1's second branch was not a runnable command, a chroot is not read-only confinement, E0 still offered `readelf` as provenance, and the historical section added unsupported specifics. All addressed, plus one finding of the repair itself: the v2.14.0 ARMv6 library in this repository's history (`90a4c19`) was extracted and read — `Tag_CPU_arch: v6`, `Tag_FP_arch: VFPv2`, all 16 bound symbols present — so the gap is a provenance-pinned build, not a library that was never built. ARMv6 runtime stays unproven. Awaits re-review. Verdicts: `.local/reviews/docs-r1-20261115/` and `docs-r2-20261115/` |
| Browser control slice, r9 (`e170448`) | `gpt-6.1-sol`, independent | **changes requested** — the restore decoder accepted a larger language than it could reproduce (`\x20` read as `x20`), the release boundary was partial, four safety reversals survived every web test, an audio write could discard a valid Setup answer, and a write settling after Disconnect threw. All six repaired; `code-r10` reviews the repair. Verdict: `.local/reviews/code-r9-20261115/verdict.md` |
| First-boot setup, r6 (`f9c5e7b`) | `gpt-6.1-sol`, independent | **changes requested, narrow** — four of five r5 findings repaired with executed proof; R5-05 unrepaired because the new test reached the pointer-write branch, and the dated record's "611 tests" and survivor claim were measured on the live tree. All eight findings repaired; `setup-r7` reviews the repair. Verdict: `.local/reviews/setup-r6-20261115/verdict.md` |
| v17 body reconstruction `f7b2163` | `gpt-6.1-sol`, independent | **approved with one fix** — the "no four-screw mount" sentence must be attributed to the audit, not stated as settled; sent to the STEP search worker, which owns the file. Verdict: `.local/reviews/cad-r1-20261115/verdict.md` |
| Device switcher and discovery fixes | — | **not yet reviewed**; needs an independent acceptance review of the current commit |

## Accepted

| Item | Reviewer | Verdict |
|---|---|---|
| Discovery contract, r2 (`5ff7ead`) | `openrouter/openai/gpt-6.1-sol#flex-high`, independent | **approve** — all three r1 blockers closed, no new blockers. 242 tests + 12 skipped, 12 browser tests, mutation proved the tests are sensitive. Verdict: `.local/reviews/discovery-r2-20261115/verdict.md` |
| Activity TUI, r3 (`262daed`) | `openrouter/openai/gpt-6.1-sol#flex-high`, independent | **approve** — all four r2 blockers closed; Needs groups distinguishable at 100, 80 and 60 columns. 78 activity tests, 242 total. Verdict: `.local/reviews/tui-r3-20261115/verdict.md` |

## Blocked

| Item | Blocker | What would unblock it |
|---|---|---|
| The v17 speaker mounting | The [lid](../models/parts/rpispeaker-v17-lid/README.md) is now the single front panel and the [cover](../models/parts/rpispeaker-v17-cover/README.md) is retired ([decision](notes/2026-11-15-v17-one-front-panel.md)), but the real driver is unmeasured: diameter, depth, frame outline, mounting pitch and thread. `SQ_PITCH` = 32 mm and `DRIVER_DEPTH` = 10 mm are assumptions, and only 5.40 mm separates the lid's plate underside from the bay's raised surfaces | the real speaker's measurements, then a mounting choice: protruding sleeve, or a flat plate with a rear clamp |
| Speaker and board purchase decisions | DWEII listings return HTTP 503; Pi Zero 2 W out of stock at US sellers | re-checked listings, or a different supplier |

## Open engineering work the harvest did not contain

The harvest of 2026-11-15 found **zero L-sized engineering items** in the
repository — the backlog was documentation, evidence and test gaps, not missing
features. That has changed: Wi-Fi onboarding, hardware-derived identity and the
first baseline now have an implementation (`control/setup/`, 177 onboarding tests
and 39 installer tests) that has
**never run on a device**, and the activity TUI has a notices checklist. The
whole offline suite is 653 tests, 43 of which are the opt-in browser cases that
skip in an ordinary run (`-p 'test_*browser.py'` with `DEBRA_BROWSER_TEST=1`).

Still without an implementation: update and rollback, the SSH maintenance TUI,
and the browser setup card (in progress). See the [first-boot design
page](design/first-boot.md) for the honest per-step status.

## Needs James

Everything here needs a fact or a decision that only James has. The tooling
reads these tables: `tools/activity.py` prints them, so they are visible
instead of being remembered. Keep each row to one question, and say what the
answer changes. Delete a row when it is answered.

A **true blocker** stops work outright. A **please confirm** does not: the work
continues on the stated assumption, the design marks it unconfirmed, and a
better answer refines it later. Prefer moving an item down to "please confirm"
over waiting.

### True blockers

No true blockers right now.

### Please confirm

| Need | Blocks | What the answer changes |
|---|---|---|
| ReSpeaker 2-Mics HAT v2 microphone and LED positions | The demo lid's two microphone holes and LED window sit on an estimated v2 layout from product pictures and the v1 board, marked unconfirmed | Openings that sit exactly over the right hardware instead of close |
| DWEII module outer dimensions and acoustic opening positions | The speaker bay uses seller-claim envelopes with added clearance, marked unconfirmed | A measured bay, and certainty that no vent is sealed |
| The v17 speaker's diameter, depth, frame outline and mounting pitch | The [lid](../models/parts/rpispeaker-v17-lid/README.md) is the single front panel, but its Ø28 driver, 10 mm sleeve, 24.8 mm rear opening and 32 mm assumed pitch are all guesses | A speaker mount that is a design instead of a placeholder: which mounting the frame allows, whether it fits the 5.40 mm between the plate underside and the bay's raised surfaces, and whether the sleeve is needed at all |

## Unattended research

`tools/scheduled_runner.py` holds a queue of bounded research tasks that run from
a systemd user timer without anyone present. It is the one channel that works
between conversations. When the queue is empty, nothing happens on its own —
check `python3 tools/scheduled_runner.py status` and refill it rather than
relying on the next conversation to start the work.

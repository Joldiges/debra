# Work queue

Execution state: what is being worked on, by whom, and what is waiting. The
[roadmap](roadmap.md) is the plan, and [notes](notes/) hold findings. This page
holds none of that — only where each item stands right now.

Why it exists: work felt like it only happened when James asked for it, because
nothing durable recorded the next item. A harvest note lists findings; it does
not say which ones are claimed, finished, or stuck. This page does.

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

## Running

| Packet | Item ids | Files | Notes |
|---|---|---|---|
| Acceptance review `setup-r3` | — | `.local/reviews/setup-r3-20261115/` | independent, `gpt-6.1-sol`; reviews the r2 fixes, which are the first candidate that writes a persistent Wi-Fi profile |

## Done this round

| Packet | Item ids | Proof |
|---|---|---|
| Wi-Fi onboarding, identity and first baseline | N02 | `cd4790f`, fixed by `40ef8dc` and `ef370d5` — 67 tests; **not run on a device** |
| Setup service at boot | N02 | `cf88922` — system unit, installer, 24 tests; never loaded by systemd |
| The r1 review's remaining blockers | N02 | `ef370d5` — reserved admission, active-profile check, classified errors, baseline retry and atomicity, form kept while polling |
| Nearby-network picker in the setup page | N02 | this round — the radio is scanned once before the access point is raised, so a beginner chooses a name instead of typing it; 13 setup browser scenarios |
| The r2 review's blockers | N02 | this round — the profile is written where NetworkManager keeps it and promoted to autoconnect only after the join is verified; a per-attempt token replaces the SSID check; the reservation is released when the reply cannot be written; the country is set after the AP is down; the portal prints the address it is served on; the baseline is never overwritten, never archives itself, and `latest()` verifies the hash; the page keeps what was typed across a poll and shows a baseline failure |
| Browser proof of the device list | — | `test_development_bypass_and_device_links` already drives the configured and discovered badges, the same-device case, a literal label, a discovery start failure, an empty scan and a refused advertisement |
| Browser proof of the setup page | N02 | `508a7f9` — 7 Chromium scenarios; the page was unreachable and the tests caught it |
| Installed-artifact tests and atomic rollback | B13 | `508a7f9`, `9d11d08` — 16 tests; two real gaps recorded rather than asserted away |
| Dashboard Setup card | WEB03 | `8b05215` — 21 tests, read-only, every choice disabled with its reason |
| First-boot design page | N02 | `b136db2`, kept in step with the code by `40ef8dc` |
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

## Queued

| Packet | Item ids | Why it is next |
|---|---|---|
| Acceptance review `code-r7` | — | must follow B14/C1–C4, from a model that did not write it |
| Device run of the onboarding flow | N02 | needs a spare card and one of the next Pis; nothing in `control/setup/` has touched a radio |
| Retained releases are never re-verified | B13 | an upgraded-away release is never re-checked, so a corrupted old release is restored by rollback without complaint. Either verify every retained release at install, or record that rollback may restore bad content |
| Staging files can be `0644` | B13 | an interrupted copy is retained with files created before `chmod`; the containing directory is `0700`, so the README's "private staging files" is true only at directory level |
| `install()` does not validate the device list | B13 | only `main()` does, so a programmatic caller can install a list the server then refuses at startup |
| No captive portal | N02 | the setup page exists but no phone will offer to open it. A person has to read the password from the boot-partition note and type `10.42.0.1` — workable, not seamless |
| No baseline restore demo | N02 | a baseline is captured and can be inspected, but nothing restores from one, so "recovery" is untested in the direction that matters |

## In review

| Item | Reviewer | Outcome |
|---|---|---|
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
| The four-screw square speaker mount | The body has no square pattern and only two Ø4.5 pilots, which are **4.1875 mm outside** the shelf a speaker stands on and also hold the lid. A [cover carrying the pattern](../models/parts/rpispeaker-v17-cover/README.md) exists, but it intersects the [lid](../models/parts/rpispeaker-v17-lid/README.md) by **785.08 mm³** ([conflict note](notes/2026-11-15-v17-cover-lid-conflict.md)), and its `SQ_PITCH` is an assumption | a decision on whether the front panel or a separate cover carries the speaker; then the real speaker's frame, height and four-screw pitch |
| Speaker and board purchase decisions | DWEII listings return HTTP 503; Pi Zero 2 W out of stock at US sellers | re-checked listings, or a different supplier |

## Open engineering work the harvest did not contain

The harvest of 2026-11-15 found **zero L-sized engineering items** in the
repository — the backlog was documentation, evidence and test gaps, not missing
features. That has changed: Wi-Fi onboarding, hardware-derived identity and the
first baseline now have an implementation (`control/setup/`, 47 tests) that has
**never run on a device**, and the activity TUI has a notices checklist.

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

## Unattended research

`tools/scheduled_runner.py` holds a queue of bounded research tasks that run from
a systemd user timer without anyone present. It is the one channel that works
between conversations. When the queue is empty, nothing happens on its own —
check `python3 tools/scheduled_runner.py status` and refill it rather than
relying on the next conversation to start the work.

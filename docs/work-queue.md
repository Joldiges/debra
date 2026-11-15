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
| Discovery contract | C1, C2, C4, B14 | `control/web/server.py`, `discovery.py`, `install.py`, `test_web.py`, `test_discover.py` | one acceptance rule for CLI and hub; `--port` range; name a failed discovery thread |

## Done this round

| Packet | Item ids | Proof |
|---|---|---|
| The v17 body as an editable source | A2 | `f7b2163` — reconstruction, honest about what it cannot reproduce |
| Web pages matched to the server | A8, A9, B5–B11, C3 | `f35d47f` |
| Evidence claims matched to sources | B16–B25, B27, B28 | `5e83273` |
| Eleven stale claims and the optional studies indexed | A1, A3–A7, A10–A14 | `7918ccd`, `503ce7f` |
| Runner guide and models index | B1–B4, B26 | `f5da00d` |
| Activity TUI and the runner elapsed-time fix | `--tui`, B15 | `a6732d1` |
| Idle reasons in the session table | — | `5d329ec` |

## Queued

| Packet | Item ids | Why it is next |
|---|---|---|
| Installed-artifact tests | B13 | needs `tests/test_web.py`, which the discovery worker holds; installed bytes, modes, a tampered release and an interrupted rollback are still unproven |
| Acceptance review `code-r7` | — | must follow B14/C1–C4, from a model that did not write it |
| Browser verification of the device list | — | the discovered badge and the discovery status line have no browser proof yet |

## Blocked

| Item | Blocker | What would unblock it |
|---|---|---|
| The four-screw square speaker mount | The v17 STEP contains no such pattern; the body has two pilots 36.5 mm apart and a central Ø10 hole | a photo of the assembled original with the cover off, showing the speaker and what its four screws enter, or the missing part file |
| Any claim that an enclosure fits | nothing has been sliced, printed or fit-tested | printing and measuring a part |
| The `models/` parts as a product | same | same |
| Speaker and board purchase decisions | DWEII listings return HTTP 503; Pi Zero 2 W out of stock at US sellers | re-checked listings, or a different supplier |

## Open engineering work the harvest did not contain

The harvest of 2026-11-15 found **zero L-sized engineering items** in the
repository — the backlog is documentation, evidence and test gaps, not missing
features. The features are in the [roadmap](roadmap.md) packets (Wi-Fi
onboarding, hardware-derived identity, update and rollback, the setup TUI) and in
the [project brief](project-brief.md); none of them has an implementation yet.

## Needs James

Everything here needs a fact or a decision that only James has. The tooling
reads this table: `tools/activity.py` prints it, so it is visible instead of
being remembered. Keep each row to one question, and say what the answer
changes. Delete a row when it is answered.

| Need | Blocks | What the answer changes |
|---|---|---|
| Which three speakers does James have? Model names, or a measurement of one: outside diameter, mounting-hole spacing and screw size, overall depth | The speaker bay, the arm geometry and the acoustic volume behind the driver | The bay stops being a documented default and becomes a measured fit |
| Which board should the first demo case fit: the Pi Zero (v1.3/W) or the Zero 2 W? He owns both | The board bay, the header height, and the port cut-outs differ between them | One case design, sized to the board that is actually the target |
| Save or close the design open in SolidCraft, and confirm it can be replaced | Every SolidCraft MCP tool is refused while an unsaved design is loaded, so designs are built headless and never shown in the window | The v17 body and the demo assembly can be opened and looked at directly |
| Does the demo case have to be wall-mountable, or desktop-only? | The base, the wall bracket and where the speaker fires | One layout instead of two, and no bracket designed against an assumption |
| If the STEP's square-pattern search finds nothing: a photo of the assembled original with the cover off, showing the speaker and what its four screws enter | The four-screw mount, and the claim that the STEP contains no such pattern | Distinguishes a part that was never exported from a different revision |

## Unattended research

`tools/scheduled_runner.py` holds a queue of bounded research tasks that run from
a systemd user timer without anyone present. It is the one channel that works
between conversations. When the queue is empty, nothing happens on its own —
check `python3 tools/scheduled_runner.py status` and refill it rather than
relying on the next conversation to start the work.

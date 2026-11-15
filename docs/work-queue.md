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
| Discovery contract: one acceptance rule, named rejections | C1, C2, C4, B14 | `f2b5c72` |
| Demo case: Pi Zero + DWEII 671, bays, lid with mic and LED openings | — | `3d7c07f` |
| Tabbed TUI with stable scroll positions | — | `d4ba492` |
| Queue refiller from a repository backlog | — | `059a3ba` |
| Tabbed TUI that redraws only changed lines, and drops columns instead of truncating them | — | this round |
| Two unattended studies: the ARMv6 audio stack, first-boot identity | — | `35d43c3` |

## Queued

| Packet | Item ids | Why it is next |
|---|---|---|
| Installed-artifact tests | B13 | needs `tests/test_web.py`, which the discovery worker holds; installed bytes, modes, a tampered release and an interrupted rollback are still unproven |
| Acceptance review `code-r7` | — | must follow B14/C1–C4, from a model that did not write it |
| Browser verification of the device list | — | the discovered badge and the discovery status line have no browser proof yet |

## In review

| Item | Reviewer | Outcome |
|---|---|---|
| v17 body reconstruction `f7b2163` | `gpt-6.1-sol`, independent | **approved with one fix** — the "no four-screw mount" sentence must be attributed to the audit, not stated as settled; sent to the STEP search worker, which owns the file. Verdict: `.local/reviews/cad-r1-20261115/verdict.md` |
| Discovery contract `f2b5c72` | `gpt-6.1-terra#flex-high`, independent (sol is unavailable) | in flight; verdict goes to `.local/reviews/discovery-r1-20261115/` |
| Activity TUI `3e4f787` | `gpt-6.1-terra#flex-high`, independent (sol is unavailable) | in flight; re-review after the changes requested on `a6732d1`; verdict goes to `.local/reviews/tui-r2-20261115/` |

## Blocked

| Item | Blocker | What would unblock it |
|---|---|---|
| The four-screw square speaker mount | A widened search of the STEP is **inconclusive, not negative**: no square was found among the analytic surfaces (262 faces, 776 edges), but irregular slots and non-analytic surfaces still need a topology search | that topology search; failing it, a photo of the assembled original with the cover off, showing what the four screws enter |
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
| Confirm the ReSpeaker 2-Mics HAT v2's microphone and LED positions, or measure them on the board | The demo lid's two microphone holes and LED window are placed from the v1 layout because v2 is not documented | Openings that sit over the right hardware instead of near it |
| `gpt-6.1-sol` is no longer offered by the configured provider, so the acceptance reviews you named cannot run as written. Keep using `gpt-6.1-terra#flex-high` and label the verdicts, or name another reviewer? | Every acceptance review: the web candidate, the discovery contract and the TUI are all waiting on a reviewer you trust | Verdicts that count as acceptance, or work that waits for your choice instead of being reviewed by a stand-in |

## Unattended research

`tools/scheduled_runner.py` holds a queue of bounded research tasks that run from
a systemd user timer without anyone present. It is the one channel that works
between conversations. When the queue is empty, nothing happens on its own —
check `python3 tools/scheduled_runner.py status` and refill it rather than
relying on the next conversation to start the work.

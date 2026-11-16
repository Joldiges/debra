---
title: Device page reordered for phone-first use, measured before and after
date: 2026-11-16
type: project-learning
status: unreviewed
task: control-ui
author: OpenCode coordinator
author_model: openrouter/deepseek/deepseek-v4.1-flash-1017
author_variant: unknown
sources:
  - "control/web/assets/index.html, style.css, app.js at 1fb25c7"
  - "tests/test_web_browser.py, tests/test_web_setup.py at 1fb25c7"
  - "docs/design/device-page-ux-2026-11-16.md (GPT-6.1 Sol design study)"
  - "/tmp/opencode/a11y.py and /tmp/opencode/shots2.py measurement harnesses"
  - "James, 2026-11-16: a polished web UI is wanted soon, with planned items shown"
supersedes: []
---

## Summary

The device page was a good prototype with a desktop hierarchy: it opened on
"switch to another Debra", the volume control was 1262 px down a 6733 px
document at 390 px wide, the section bar was 16–19 px tall and in an order that
disagreed with the document, and the Setup card showed eight planned
capabilities as disabled radios, selects and buttons. All four are fixed, each
by one commit with a geometric browser check. Measured at 390 × 844: document
6733 → 3184 px, volume slider y=1262 → y=723 (on the first screen), every tap
target ≥ 24 × 24, no fictional controls anywhere.

Nothing here was verified on a phone, a screen reader, or a second real device.
The measurements come from Chromium at a fixed 390 px inside an iframe.

## Claims and evidence

| Kind | Claim | Source / date / hardware-version scope | Verification and limits |
| --- | --- | --- | --- |
| user-requirement | Planned features must be shown as static markup with no control at all, never a disabled button | James, 2026-11-16 | Implemented in `791136d`; browser and offline checks assert zero controls in the Setup card |
| observed | Headless Chromium clamps `--window-size` to 500 px, so a 390 px viewport exists only inside an iframe, and the page's own CSP `frame-ancestors 'none'` blocks that unless the framed copy is served with `frame-ancestors 'self'` | `/tmp/opencode/a11y.py`, 2026-11-16, Chromium 156 | A "phone" measurement without the iframe was really a 500 px one and was discarded |
| observed | The page's contrast was never the problem: 0 of 153 texts measured below WCAG AA at 390 and 1200 px | `/tmp/opencode/a11y.py` at `9f9e32a` | Computed against each element's nearest opaque background; gradients, images and transparency not exercised |
| observed | Two state defects were invisible from the code and obvious when rendered: a held read showed the key prompt with no "checking" indication, and a failed poll left readings on screen with only a 13 px header line, which scrolls away, saying they might be stale | `/tmp/opencode/shots2.py`, fixed in `9ff523c` | Both are now browser checks; the states were produced by the fixture, not by a real device |
| observed | `position: sticky` elements report `offsetParent === null`, so a visibility guard written that way silently disabled the whole section-marker update | `29f323c`, found by the new check failing | Replaced with `getClientRects().length` |
| observed | `requestAnimationFrame` does not run in the headless browser these checks use; a scroll handler throttled with it never fires, so the behaviour would have been "verified" nowhere | `29f323c` | Throttled with `setTimeout` instead; the check drives both a tap and a scroll |
| observed | A write the device accepts but cannot report was treated as settled and rendered "not confirmed"; it is an unconfirmed change | `bffb8fa`, found by an existing check | Now unconfirmed at the point of the write |
| observed | With no usable output, the level showed the slider's default position as "50% · not confirmed" — a number the device never sent | `bffb8fa` | Now "No level", in the muted colour |
| observed | Running `tests.test_web` instead of the whole suite missed `tests/test_web_setup.py`, which still asserted the old disabled-control design | `bc651cf` | Lesson: the browser suite and the offline web suite are not the whole web contract |
| hypothesis | A single reading column is the right shape for both widths | Sol design study, section A | Chosen for unambiguous reading order; desktop space is left unused |

## Verification

- From repository root:
  `python -B -m unittest discover -s tests` — 835 tests, OK (62 skipped).
  `DEBRA_BROWSER_TEST=1 python -B -m unittest discover -s tests -p 'test_web_browser.py'`
  — 35 tests, OK.
- `git show --stat 5b024bd 9f9e32a d558e02 29f323c 791136d 0ebb3d4 10e1667 1fb25c7 bffb8fa 61ce60c bc651cf ba4fd8d`
  lists the slices; each names its own checks in the message.
- Not tested: any real phone, tablet or screen reader; zoom beyond the default;
  a second Debra open in another tab; a device losing its audio sink while the
  page is open; the welcome card against a device that answers slowly on a real
  network.
- Measurement harnesses live outside the repository under `/tmp/opencode/` and
  are not preserved by Git. Their useful assertions were moved into
  `tests/test_web_browser.py`, which is.

## Handoff and correction links

- Current state: device page restructured at `ba4fd8d`; the two devices that
  report builds `054631e3a7ab` and `9f532517e4fe` are behind it and have not
  been updated (James restricted the update to host and Pi 5).
- Next action: implement the remaining design-study slices — the state
  vocabulary items in section B that are still unbuilt (a visible "reading in
  flight" state for later polls, and the one-announcement-per-failure rule) — as
  separate commits with their own checks.
- Authorization needed: a design review of the new order before it is treated as
  settled, and a decision on whether the page should ever open a disclosure by
  itself when a section is chosen from the bar.
- Not to be undone accidentally: the first-screen order, the 44 px bar, and the
  absence of controls in the Setup card. Three checks fail if any of them goes.

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
| observed | The page's contrast was never the problem: 0 of 153 texts measured below WCAG AA at 390 and 1200 px, and 0 of 171 after the rework | `/tmp/opencode/a11y.py` at `9f9e32a` and at `791136d` | Computed against each element's nearest opaque background; gradients, images and transparency not exercised |
| observed | Two state defects were invisible from the code and obvious when rendered: a held read showed the key prompt with no "checking" indication, and a failed poll left readings on screen with only a 13 px header line, which scrolls away, saying they might be stale | `/tmp/opencode/shots2.py`, fixed in `9ff523c` | Both are now browser checks; the states were produced by the fixture, not by a real device |
| observed | `position: sticky` elements report `offsetParent === null`, so a visibility guard written that way silently disabled the whole section-marker update | `29f323c`, found by the new check failing | Replaced with `getClientRects().length` |
| observed | `requestAnimationFrame` does not run in the headless browser these checks use; a scroll handler throttled with it never fires, so the behaviour would have been "verified" nowhere | `29f323c` | Throttled with `setTimeout` instead; the check drives both a tap and a scroll |
| observed | A write the device accepts but cannot report was treated as settled and rendered "not confirmed"; it is an unconfirmed change | `bffb8fa`, found by an existing check | Now unconfirmed at the point of the write |
| observed | With no usable output, the level showed the slider's default position as "50% · not confirmed" — a number the device never sent | `bffb8fa` | Now "No level", in the muted colour |
| observed | Running `tests.test_web` instead of the whole suite missed `tests/test_web_setup.py`, which still asserted the old disabled-control design | `bc651cf` | Lesson: the browser suite and the offline web suite are not the whole web contract |
| observed | The lab Pi 5 runs keyless, and its welcome card asked for a key that nothing checks while offering a Continue button underneath: typing there cannot change the outcome | live page at `debra-3c6b3f.local:8787`, 2026-11-16 | `a33fc10` hides the field, its hint and its intro line on a keyless device and says there is nothing to type; key mode unchanged |
| observed | Focusing a hidden element does nothing, so the disconnect path left focus on the device name once the key field became hidden | `a33fc10`, found by an existing check failing | Replaced with a helper that focuses whichever action the card offers |
| observed | The page footer sat inside the dashboard while the network switcher follows it, so the page appeared to end and then carried on with another card | desktop screenshot of `ready`, 2026-11-16 | `7308269`: footer is last in `main`, hidden until the dashboard opens |
| observed | A read failure printed the same sentence into an alert region every poll; a region re-announcing "the device did not answer" indefinitely is worse than silence | `13bbc15` | Written only when it changes. Not observed with a screen reader, so "announced once" is inferred from not rewriting the node |
| hypothesis | A single reading column is the right shape for both widths | Sol design study, section A | Chosen for unambiguous reading order; desktop space is left unused |

## Verification

- From repository root:
  `python -B -m unittest discover -s tests` — 835 tests, OK (62 skipped).
  `DEBRA_BROWSER_TEST=1 python -B -m unittest discover -s tests -p 'test_web_browser.py'`
  — 35 tests, OK.
- `git show --stat 5b024bd 9f9e32a d558e02 29f323c 791136d 0ebb3d4 10e1667 1fb25c7 bffb8fa 61ce60c bc651cf ba4fd8d 9c7f2e7 13bbc15 a33fc10 7308269`
  lists the slices; each names its own checks in the message.
- Not tested: any real phone, tablet or screen reader; zoom beyond the default;
  a second Debra open in another tab; a device losing its audio sink while the
  page is open; the welcome card against a device that answers slowly on a real
  network.
- Measurement harnesses live outside the repository under `/tmp/opencode/` and
  are not preserved by Git. Their useful assertions were moved into
  `tests/test_web_browser.py`, which is.

## Handoff and correction links

- Current state: `7308269` on `main`. The lab Pi 5 was installed from it and
  reports build `f75034cbfa10`, `restart_required: false`, `--auth none`, all
  four unit flags unchanged and the previous unit preserved. The host serves the
  same assets from this checkout and is key mode (401), so its key form is
  correct; its running process predates version reporting, which a restart would
  change. `debra-8518d6` and `debra-f943dc` were deliberately not updated
  (James restricted the update to host and Pi 5).
- Next action: the state-vocabulary items in section B that are still unbuilt —
  `aria-busy` on the audio controls during a write (the controls are already
  disabled, so this is assistive-technology polish only), and a "checking"
  indication for a later poll that does not flicker on a 3-second cadence.
- Authorization needed: a design review of the new order before it is treated as
  settled, and a decision on whether the page should ever open a disclosure by
  itself when a section is chosen from the bar.
- Not to be undone accidentally: the first-screen order, the 44 px bar, and the
  absence of controls in the Setup card. Three checks fail if any of them goes.

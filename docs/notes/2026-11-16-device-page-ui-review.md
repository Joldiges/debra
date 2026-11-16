---
title: Device page UI review at phone and desktop widths
date: 2026-11-16
type: project-learning
status: unreviewed
task: control-ui
author: OpenCode coordinator
author_model: openrouter/deepseek/deepseek-v4.1-flash-1017
author_variant: unknown
sources:
  - "control/web/assets/index.html, style.css, app.js at 467adf0"
  - "tests/test_web_browser.py FIXTURE (synthetic responses)"
  - "/tmp/opencode/shots.py and its output under /tmp/opencode/shots/"
  - "James, 2026-11-15: a polished web UI is wanted soon, with planned items shown"
supersedes: []
---

## Summary

I rendered the real device page and the real setup page with the browser
fixture's synthetic data at 390 px and 1200 px and looked at them, rather than
inferring the layout from the geometry assertions. The **setup page already reads
as a phone-first appliance page**: one step marker, one primary action, full-width
fields, nothing competing. The **device page is a good prototype with a
desktop hierarchy**: its first screen on a phone is a rare action (switching
device), its section navigation is neither tappable nor stateful, and its status
line wraps into the brand.

Nothing here changed a file. `control/web/` is frozen under `code-r12`; these are
findings for the polish pass, not edits.

## Claims and evidence

| Kind | Claim | Source / date / hardware-version scope | Verification and limits |
| --- | --- | --- | --- |
| observed | At 390 px the header status "Connected · updates every 3 seconds" wraps to two lines inside a 145 px box and ends up as tall as the brand block | `style.css:95` sets `#connection { max-width: 145px; text-align: right; }` at ≤650 px; screenshot `/tmp/opencode/shots/phone.png` | Rendered with Chromium 156 headless against the fixture; the text is the fixture's real connection string |
| observed | The "Switch to another Debra" card is the first content on the page, above the device you are already on, and occupies the whole first screen at 390 px | `index.html:15–26`; `phone.png` | The switcher is a rare action; on a phone the volume control starts about 1000 px down |
| observed | The section links (`Audio`, `Setup`, `Device`, `Health`, `Components`) are 13 px text with no padding and no active state | `style.css:15,99`; `index.html:30`; both screenshots | The anchor box is roughly 16 px tall, below the 24 × 24 minimum in WCAG 2.2 SC 2.5.8; the current section is not indicated at all |
| observed | The links are in-page anchors, so every section renders in one document; nothing collapses and nothing marks where you are while scrolling | `index.html:30`, `app.js` has no routing | `/tmp/opencode/shots/full.png` is 5400 px tall at 1200 px wide |
| observed | The setup page at 390 px has one clear primary action, a "STEP 1 OF 2" marker, full-width fields, and a single small footer caveat | `/tmp/opencode/shots/form.png` (setup harness, synthetic) | This is the standard the device page should meet, and it already does |
| observed | Planned items render as static cards with a `PLANNED` badge and a status line that says why they cannot act; disabled selects show "Not set on this device" | both screenshots; `tests/test_web_browser.py` planned-control sweep | This matches the decision to show planned items with no control at all |
| observed | The access-key-off banner is unmissable and states the consequence in one sentence | `desktop.png`, `phone.png` | Good; keep this shape for the enrollment banners |
| hypothesis | Moving the switcher below the device's own controls (or behind a "Switch device" disclosure) would put "turn it down" on the first screen without removing the feature | — | Not tested with a person; the cost is one extra tap to switch |
| hypothesis | Real tab switching would make the phone page shorter but would break deep links and the "one page, no router" simplicity | — | A disclosure per section, or a sticky section bar with an active state, is the cheaper middle |
| open-question | How much of the polish pass is safe before the enrollment work defines the authenticated states (locked, wrong password, locked out)? | `docs/design/browser-enrollment.md` | The pairing card's copy will change again when enrollment lands |

## What a polish pass should do, in order

1. **Header**: keep the connection state, drop the polling detail from the
   visible line (or move it under the brand), so it cannot wrap into two lines.
2. **Order**: device controls first; the switcher below them or behind a
   disclosure. On a 390 px screen the first screenful should be volume and mute.
3. **Navigation**: real tap targets (≥24 px), an active state for the current
   section, and a sticky bar so the section is visible while scrolling.
4. **Empty and busy states**: say what is happening while a read is in flight
   and what a failed read means, in the same voice as the setup page's caveats.
5. **Keep** the planned-item treatment and the unmissable mode banners; they are
   already right.

Steps 1–4 all touch `control/web/assets/`, which `code-r12` holds. They wait for
its verdict.

## Verification

- Exact safe commands and working directory:
  `cd /home/james/Projects/debra && python3 /tmp/opencode/shots.py` — a
  screenshot tool, not a test. It serves the real `index.html`, `style.css` and
  `app.js` with the browser fixture's synthetic responses, refuses to reach a
  real backend, and writes PNGs to `/tmp/opencode/shots/`.
- Observed results: pass. Three screenshots at 390 × 2600, 1200 × 2600 and
  1200 × 5400. Chromium `/usr/bin/chromium-browser` 156.0.8078.79, headless.
- Not tested, conflicting evidence, remaining uncertainty: no real device, no
  phone, no touch input, no assistive technology, no contrast measurement, and no
  person using the page. The screenshots show the fixture's data, including a
  sink name deliberately shaped like an injection attempt; it renders as literal
  text, which is the correct behaviour and not a defect. The 5400 px height is a
  layout measurement, not a claim that the page is unusable.
- Sanitized artifact references: `/tmp/opencode/shots/phone.png`,
  `/tmp/opencode/shots/desktop.png`, `/tmp/opencode/shots/full.png`,
  `/tmp/opencode/shots/form.png` (local only, not committed).

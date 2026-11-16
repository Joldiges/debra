---
title: Device page user experience and implementation plan
date: 2026-11-16
type: design-study
status: unreviewed
task: control-ui
author: GPT-6.1 Sol (debra-research worker, read-only)
author_model: openrouter/openai/gpt-6.1-sol
author_variant: flex-high
sources:
  - "docs/design/web-control.md (requirements)"
  - "control/web/assets/index.html, style.css, app.js at 9f9e32a"
  - "control/web/README.md (prototype boundary)"
  - "docs/notes/2026-11-16-device-page-ui-review.md"
  - "docs/design/browser-enrollment.md"
  - "/tmp/opencode/a11y.py measurements at 390x844 and 1200x903"
supersedes: []
---

## What this is

An information-architecture study of the device page, commissioned as design
input for a cheaper implementer. It is **unreviewed design**, not a supported
capability claim and not authorization to operate a device. The roadmap
[WEB packets](../roadmap.md) own task state.

It was produced by a read-only worker that changed no file. The measurements it
did not take were taken here; where the two disagree the measurement wins.

## Measured starting point

`/tmp/opencode/a11y.py` renders the real page with the browser fixture's
synthetic device, opens the dashboard, and reports geometry and contrast. At
`9f9e32a`:

| | 390 × 844 | 1200 × 903 |
| --- | --- | --- |
| Document height | 6733 px | 4846 px |
| "Switch to another Debra" heading | y = 165 (first) | y = 171 (first) |
| Device name | y = 763 | y = 534 |
| Section nav | y = 936 | y = 666 |
| Volume slider | y = 1262 | y = 949 |
| Tap targets under 24 × 24 | 8 of 19 | 8 of 19 |
| Text below AA contrast | 0 of 153 | 0 of 153 |

So the page is **not** a contrast problem: every text colour measured clears
WCAG AA. It is a **structure** problem. On the phone the appliance presents a
rare action (switching to a different device) before the device the person is
already on, and the first control they came for is 1.5 screens down a document
that is eight screens long. The nav links are 16–19 px tall — under half the
44 px a thumb wants and under the 24 px WCAG 2.2 minimum — and the range input
is 16 px tall.

## A. Information architecture

### First screen

Viewport targets below are the test points, not a promise that every label fits
at every zoom level.

| Viewport | First screen |
| --- | --- |
| 390 × 844, key accepted or keyless | Compact brand and connection state; hostname and board; section navigation; speaker volume with slider, Apply and Mute. Explanations sit below the controls. |
| 1200 × 800 | Same order. No second, desktop-only hierarchy. |
| Either, before access | Header, welcome/access-key card, then the collapsed network switcher. No device readings. |
| Either, keyless development | The existing warning band above every control. It may push content down; it is never shrunk or hidden to hit a first-screen target. |

### Order and disclosures

| Order | Element | Treatment |
| --- | --- | --- |
| 1 | Header `#connection` | Connection state only. Drop the polling interval from this line. Not sticky. |
| — | Skip link → `main#main-content` | Direct keyboard entry past the header. |
| — | `#error` | Moves near the top of `main`. A read failure several screens below its cause is not a message. |
| 2 | `#dashboard` → warning, identity, nav | Keep `#hostname` and `#model`. `#disconnect` moves into Browser access; it is not a primary device task. |
| 3 | `#audio` | Always expanded. Sink identity before the controls, `#audio-notice` after them. Secondary explanation in `<details id="audio-help">`. |
| 4 | `#health` | Main readings visible. `#cores` behind `<details id="cores-details">`; swap/compression content moves here behind `<details id="swap-details">`. |
| 5 | `#device` | Heading visible; `#device-values` behind `<details id="hardware-details">`. Separate Browser access disclosure holds Disconnect and the static planned access rows. |
| 6 | `#components` | Evidence limitation visible; `#component-list` behind `#components-details`. |
| 7 | `#setup` | Heading and Planned explanation visible; contents behind `#setup-details`. No disabled mock controls (see slice 2). |
| 8 | `#planned` | Heading and explanation visible; the five rows behind `#tasks-details`. |
| 9 | Footer | Prototype boundary and `#build` unchanged. |
| 10 | `#devices` | Moves **after** `#dashboard`, outside the authentication gate. Available before access, never before the welcome card or the current device. Collapsed behind `#network-details`. |

**Rule:** a `<details>` controls visibility only. A planned capability row
contains no link, field, button, handler or interactive ARIA role. A disclosure
is not a simulated control, and section headings stay outside it.

### Navigation contract

- One content column, maximum 960 px. DOM order identical at both widths.
- Six anchors: Audio, Health, Device, Components, Setup, Tasks. Three columns on
  a phone, six on a desktop.
- Minimum 44 × 44 CSS px for links, buttons and summaries; the range input's hit
  area at least 44 px tall. This deliberately exceeds the 24 px WCAG minimum.
- Sticky navigation only, with an opaque background; its measured height is the
  scroll offset. Non-sticky below 480 px of viewport height.
- Exactly one `aria-current="location"`: the last section heading that has
  crossed below the bar, with Audio as the default above that point. Marked by
  weight and underline, not colour alone.
- Existing ids `#audio`, `#setup`, `#device`, `#health`, `#components` are kept;
  `#planned` joins the navigation. An inbound hash reveals its target's
  disclosure and scrolls below the bar. Existing key-fragment handling runs
  first and ordinary anchors are not consumed.

## B. State vocabulary

| State | What the person sees | Markup | Never shown |
| --- | --- | --- | --- |
| Checking access | "Checking access…" | `#connection`, `role="status"`, atomic | Connected, or any protected reading |
| Connecting with a key | "Connecting…" | same region | "Key accepted" before a successful protected read |
| First reading in flight | "Reading…" | placeholders only before the first result; `aria-busy` on read containers; routine progress not announced | Zero, absence, a healthy state, or a cleared preview |
| Later read in flight | "Checking device…" | previous values retained | Announcing every poll |
| Reading age unknown | "Reading age unknown." | visible qualification, `.age-unknown`; receipt time is never presented as observation time | "Updated just now", a fabricated observation timestamp |
| Previous reading after a failure | "Previous reading · age unknown" | `.previous`; applies inside closed disclosures too | An unqualified old value |
| Read failed | "Could not read {section}. {reason}" | beside the affected content; `#error` for the status read, `#setup-status` for Setup; alert once per changed failure | "Not installed", "not detected", or zero inferred from a failure |
| Write in flight | "Applying volume…" / "Changing mute…" | `#audio-controls[aria-busy="true"]`, inputs disabled | "Not applied" while it is still pending |
| Write refused | "Volume change refused. {reason}" | persistent `#audio-notice`, polite | Treating every HTTP error as proof nothing changed |
| Write unconfirmed | "The device did not confirm this volume change. It may have changed. Read the current setting before trying again." | requested value kept separate from reported value; read back, never replay the write | "Saved", "failed to apply", automatic retry |
| Device unreachable | "Device unavailable" + "This page could not reach the device. Check your connection and try again." + "Try reading again" | audio actions disabled; retained readings qualified; retry reads only | "Powered off", "Wi-Fi disconnected", replayed writes |
| No key | "Access required" | existing `#pair`, labelled password input | Enrolled, recovery, or a setup handoff presented as available |
| Wrong key | "The device refused this access key. It has been forgotten by this tab. Enter the key again." | existing `#pair-status[role="alert"]` | Wrong/expired/revoked distinctions the response does not establish |
| Refused key, keyless device | the refusal plus "This device has access keys switched off for development; you can continue without one." | existing Continue action, explicit | Entering automatically; inferring keyless mode from a failed request |
| Keyless development | existing warning band | `#auth-mode-warning`, above every control, shown even when a stored key exists | Secure, enrolled, private |
| CPU-core voltage | "Unavailable" + Planned: "A collector will show CPU-core voltage; this reading is not implemented yet." | static row, no control | 0 V, the 5 V supply substituted, or a healthy badge |

One announcing region per event. Reading values are never live regions. On
access loss or Disconnect, protected values and old errors are cleared rather
than kept as "previous readings".

## C. Copy

The state text above is used verbatim. New and changed text:

| Location | Text |
| --- | --- |
| Skip link | "Skip to device controls" |
| Connection, success | "Connected" |
| Navigation | Audio · Health · Device · Components · Setup · Tasks |
| Audio, under the controls | "Moving the slider previews a value. Apply volume changes it. No test sound plays." |
| `#audio-help` summary | "About this output" |
| Audio help | "Apply volume links all output channels. Mute is separate. Percent is a native control setting, not a loudness or safety measurement." |
| Health eyebrow | "READ-ONLY" (replaces "RIGHT NOW") |
| Shared age caveat | "Reading age unknown. **Planned** — Observation times will show how old readings are; the device does not report them yet." |
| Health disclosures | "Per-core CPU"; "Swap & compression" |
| Device disclosure | "View hardware and system details" |
| Access disclosure | "Browser access" |
| Disconnect explanation | "Disconnect clears this tab only. It does not remove access from other tabs or cancel changes already sent." |
| Setup introduction | "These are planned setup choices, not controls. This page cannot change them." |
| Setup disclosure | "View setup choices" |
| Tasks introduction | "Every task is Planned; nothing here can be used yet." |
| Tasks disclosure | "View planned device tasks" |
| Network disclosure | "Show devices on this network" |
| Network caveat | "Switching opens that device's page in this tab. Each device checks its own access. This tab does not send your key to it. Discovery is a claim, not authentication. Read the address before entering a key." |

Unchanged: the welcome card, key-source hint, development warnings, native
output caveat, section headings, Output level, Apply volume, Mute/Unmute,
Disconnect this tab, hardware qualifications, metric source labels, swap
explanation, and the prototype footer.

Static Setup rows (each with a Planned badge and one sentence): ReSpeaker
2-Mics Pi HAT v2 — "Select this HAT for the setup; this page cannot change its
drivers or verify compatibility yet."; No HAT: jack or USB audio — "Select a
jack or USB output for the setup; this page cannot choose outputs or confirm
that this board has a jack."; Music player — "Choose the music receiver; no
music-player choice is stored by this page yet."; During an announcement —
"Choose whether music becomes quieter or pauses; coordination with the music
receiver is not implemented or tested yet."; Update policy — "Choose when
component versions change; this page has no update-policy operation yet."; Check
for updates — "Check for available versions; this page has no update source
yet."; Install updates — "Install reviewed component versions; this page has no
update operation yet."; Roll back the last change — "Return to an earlier working
setup; this page has no rollback operation yet."

## D. Implementation slices

Each slice is separately reviewable and separately testable. Order is by value
per unit of risk.

### 1. Put the current device first

Reorder `index.html` as in A; move `#devices` after `#dashboard`; move
`#disconnect` into the access disclosure; add native `<details>`; compact the
header; one column.

Acceptance: at 390 × 844 the slider, Apply and Mute are visible without
scrolling; before access the welcome card precedes the network switcher; the
keyless warning precedes Audio; section ids stay unique. Tests that activate
controls inside a disclosure must open it first. **Do not change** requests,
polling, authentication, audio or discovery logic, or the release digest.

### 2. Remove fictional Setup controls

The eight planned rows become static markup with a badge and a sentence; the
renderer stops building radios, selects and buttons. Protected Setup evidence
moves to its own container.

Acceptance: no planned row contains a control, link, `tabindex`, interactive
role or handler; dispatching click/input/change on every row produces zero
non-GET requests; the eight descriptions and eight badges are present; the
existing label and qualification assertions still hold against the observed
container. **Do not change** `/api/setup` into a write API, its session guards,
or its evidence qualifications.

### 3. Make navigation usable

Six anchors, skip link, 44 px targets, sticky bar with a measured offset,
`aria-current`, hash and Back/Forward handling.

Acceptance: every target ≥ 44 × 44; exactly one current location; keyboard
activation, an inbound `#health` or `#setup`, and Back/Forward all reveal the
section without hiding its heading; no horizontal scroll or clipped text at
390 px, 1200 px or enlarged text; focused elements are never hidden under the
bar.

### 4. Put read failures where people see them

`#error` near the top of `main`; a read-only retry; retained readings labelled
as previous with unknown age.

Acceptance: a failed status read disables audio and labels the retained
readings; a Setup-only failure does not disable audio; retry issues no non-GET
request; access loss clears protected observations; identical repeated failures
are announced once.

### 5. Honest missing readings

A static CPU-core-voltage row marked unavailable and Planned, plus the shared
unknown-age caveat, outside the renderer-owned `#health-values`.

Acceptance: core voltage never shows 0 V or the supply reading; a supplied
`power.supply_voltage_v` appears only as the 5 V supply; missing readings are
never green; waiting, caching and reconnecting never produce a "fresh" badge.
**Do not change** collectors, units, formulas or polling cadence.

### 6. Finish state copy and accessibility

Apply B and C; add `#audio-controls` busy semantics with `#audio-notice`
outside that subtree; correct colours only where measurement requires it.

Acceptance: holding a write shows "applying", not "not applied"; a definite
rejection survives polling and an unrelated mute success; a lost response is
never replayed and never becomes a definite failure; refused-key copy keeps
"refused" and "forgotten"; keyless copy keeps "continue without one". Existing
race, no-write, credential-storage and literal-text protections stay.

## E. Deliberately left alone, and the risks

- Access-key terminology stays. No password, reset, enrolment or revocation
  control before those operations exist.
- No room-name editing, hostname changes, verified identity, IP fallback,
  automatic rerouting or service-working badges.
- CPU-core voltage is treated as absent; observation age as unknown. A missing
  collector never becomes a measured negative.
- **Risk:** one column leaves desktop space unused, and disclosures add one
  activation to diagnostics. Headings, warnings and availability explanations
  stay visible outside them.
- **Risk:** sticky navigation costs two phone rows and needs focus and zoom
  testing; it falls back to non-sticky on short viewports.
- **Risk:** a static planned catalogue can drift from what is built. Moving a
  capability from Planned to available must be a reviewed change; an old mock
  control is never enabled in place.
- **Unknown:** real-phone usability, assistive-technology behaviour and WCAG
  compliance remain unverified. Geometry tests are not accessibility evidence.
- The worker did not read `app.js`; it specified observable behaviour only, and
  the implementer is responsible for checking whether the internals fit.

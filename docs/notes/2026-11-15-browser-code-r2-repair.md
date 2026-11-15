---
title: Browser code repair for WEB-REVIEW-02 findings
date: 2026-11-15
type: project-learning
status: unreviewed
task: none
author: OpenCode coordinating session
author_model: openrouter/deepseek/deepseek-v4.1-flash-1017
author_variant: high
sources:
  - WEB-REVIEW-02 verdict, changes-requested, openai/gpt-6.1-sol, 2026-11-15
  - docs/notes/2026-11-15-browser-docs-handoff.md (earlier state record, now partly superseded)
  - Working tree at /home/james/Projects/debra on base ac2298c308d374d06bdc1ebef9340dc134b3ad1a
  - DEBRA_BROWSER_TEST=1 python -B -m unittest discover -s tests -v, 2026-11-15
supersedes: []
---

## Summary

WEB-REVIEW-02 returned changes-requested with two findings against the frozen
code candidate. Both are repaired in `control/web/assets/app.js`, and the
browser fixture now proves the lost-response behavior. The other six files of
the reviewed candidate are byte-identical, so the repair is provably narrow.
The new candidate is **not** approved: it needs re-review, and this note is not
a verdict.

## Claims and evidence

| Kind | Claim | Source / date / hardware-version scope | Verification and limits |
| --- | --- | --- | --- |
| observed | After a volume write whose response is lost but which the device applied, the page used to keep showing `24% · not applied` while the fresh reading was 24, and cleared the warning. | WEB-REVIEW-02, independently reproduced with a Node VM and synthetic DOM | Reviewer's reproduction, not a device observation. |
| observed | The repair tracks an unconfirmed write, adopts the fresh reading when it matches the requested value, and otherwise labels the retained preview as `N% selected · device reports M%` instead of claiming non-application. | `control/web/assets/app.js`, `change()`, `audio()`, `labelPreview()` | Verified only in the synthetic Chromium fixture; no device involved. |
| observed | A retained notice now survives a successful status refresh, so an unanswered write is not silently cleared. | `refresh()` writing `notice` into the alert element | Same fixture. |
| observed | The native sink name is now always shown next to any friendly description, using text-only rendering. | `audio()` output label; fixture description contains markup | Markup in the fixture stays literal text. |
| observed | The full suite still passes: 84 tests including the browser run. | `DEBRA_BROWSER_TEST=1 python -B -m unittest discover -s tests -v` | Host-only. No device, audio, rollback, or power-loss evidence. |
| observed | The r2 patch applies cleanly to the named base and reproduces all eight file hashes; six of eight match the reviewed r1 manifest exactly. | `.local/reviews/browser-code-r2-20261115/` | Applied in a scratch copy under `/tmp/opencode`, not in the repository. |

## Verification

- Exact safe commands/procedure and working directory:
  - `cd /home/james/Projects/debra`
  - `node --check control/web/assets/app.js`
  - `DEBRA_BROWSER_TEST=1 python -B -m unittest discover -s tests -v`
- Observed results: pass (84 tests); patch reconstruction reproduced all eight
  hashes with `git apply --check` and a hash comparison in a scratch copy.
- Not tested, conflicting evidence, and remaining uncertainty: the browser
  fixture still does not cover a pending-write disconnect/re-pair or a duplicate
  submission while a write is pending; the reviewer named both. No deployment,
  physical audio, live rollback, or abrupt power-loss durability evidence exists.
- Sanitized artifact references, if any:
  `.local/reviews/browser-code-r2-20261115/code.patch` and `code.json`
  (patch SHA-256 `b64a7237d7779eb0db6834a2b9a93d5bd730f6da6079809e6ef9437daf6793d2`).

## Handoff and correction links

- Current state and relevant base/candidate revision: uncommitted work on
  `ac2298c308d374d06bdc1ebef9340dc134b3ad1a`; r2 candidate replaces the frozen
  r1 hash `67dc51379b241c9abe3d65f220574b1a475bbc94f3f19b0a6df2f6ae976af0e5`
  named in the earlier handoff note.
- Concrete next action and prerequisites: obtain an independent re-review of the
  two changed files against the r2 manifest, then stage only reviewed paths.
- Authorization needed; do not treat this suggestion as permission: deployment,
  device access, and dispatch reopening are not authorized here. The author of
  this repair cannot approve it.
- Earlier claim superseded, if this is a correction: the earlier note's frozen
  candidate hash and its "awaiting first review" state.
- Reviewed report/decision that later adopts this finding, if known: none yet.

---
title: Browser control, front-door docs, and model handoff state
date: 2026-11-15
type: project-learning
status: unreviewed
task: none
author: OpenCode coordinating session
author_model: openai/gpt-5 (pre-switch) then openrouter/deepseek/deepseek-v4.1-flash-1017
author_variant: unknown (pre-switch) then high
sources:
  - Working tree at /home/james/Projects/debra, uncommitted on top of ac2298c308d374d06bdc1ebef9340dc134b3ad1a
  - python -B -m unittest discover -s tests -v with DEBRA_BROWSER_TEST=1, 2026-11-15
  - python tools/taskchain.py check, 2026-11-15
  - User statement 2026-11-15 requesting a switch to DeepSeek Flash to conserve the OpenAI five-hour allowance
supersedes: []
---

## Summary

This note records what exists in the working tree, what has been verified, and
what is still unreviewed. Nothing in the browser control work or the rewritten
front-door documentation is committed, pushed, deployed, or independently
reviewed. The session's model was switched to DeepSeek Flash to conserve
James's OpenAI allowance; the switch is confirmed by the session record, not by
a configuration change.

## Claims and evidence

| Kind | Claim | Source / date / hardware-version scope | Verification and limits |
| --- | --- | --- | --- |
| observed | The full suite passes with the browser test enabled: 84 tests, including a synthetic Chromium run with no native audio. | `DEBRA_BROWSER_TEST=1 python -B -m unittest discover -s tests -v`, 2026-11-15 | Host-only. Proves the code's own contract, not device behavior, audio output, or ARMv6 support. |
| observed | `python tools/taskchain.py check` reports `PASS: 19 chains cover 65 packets; starter cards/paths valid.` | Same date, repository root | Registry consistency only; dispatch remains closed. |
| observed | The session model is `openrouter/deepseek/deepseek-v4.1-flash-1017` with variant `high`. | `POST /api/session/ses_.../model` returned 204, then `GET /api/session/ses_...` reported the new model | Confirmed from the session record. A model label does not establish output quality. |
| observed | All browser implementation, tests, and documentation edits are uncommitted and unpushed. | `git status --porcelain` 2026-11-15 | Twelve modified paths, plus untracked `control/`, `docs/archive/`, `docs/design/web-control.md`, `docs/guides/getting-started.md`, `tests/test_web.py`, `tests/test_web_browser.py`. |
| hypothesis | The browser volume/mute design can serve ordinary configuration without SSH, because it targets one explicitly selected native sink and never invents a fallback. | `control/web/` implementation and tests | No on-device deployment has occurred; the sink-selection requirement is untested against the real lab device. |
| open-question | Whether the revised documentation is accurate and consistent after the last round of edits. | `README.md`, `docs/guides/getting-started.md`, `docs/README.md` | Requires a fresh capable review; the earlier WEB-DOC-REVIEW-01 verdict covers an earlier revision. |

## Verification

- Exact safe commands/procedure and working directory:
  - `cd /home/james/Projects/debra`
  - `DEBRA_BROWSER_TEST=1 python -B -m unittest discover -s tests -v`
  - `python tools/taskchain.py check`
- Observed results: pass (host suite and registry check); not-run (device
  deployment, native volume change, browser access from another machine).
- Not tested, conflicting evidence, and remaining uncertainty: no device was
  contacted during this work; the last device observation predates it. Abrupt
  power-loss durability of key publication and release replacement remains
  unproven, and only injected interruption is covered.
- Sanitized artifact references, if any: `.local/reviews/browser-readme-20261115/`
  holds the frozen code candidate for review; `.local/runner/` holds queue state
  and reports and is git-ignored.

## Handoff and correction links

- Current state and relevant base/candidate revision: uncommitted work on
  `ac2298c308d374d06bdc1ebef9340dc134b3ad1a`; frozen code candidate SHA-256
  `67dc51379b241c9abe3d65f220574b1a475bbc94f3f19b0a6df2f6ae976af0e5`.
- Concrete next action and prerequisites: receive the WEB-REVIEW-02 verdict,
  then freeze the revised documentation and obtain separate review of it before
  staging anything. Deployment needs a named target and a stated rollback path.
- Authorization needed; do not treat this suggestion as permission: browser
  deployment, device reflash, and service changes are not authorized by this
  note. Lower-cost editing dispatch stays closed pending F05 evidence.
- Earlier claim superseded, if this is a correction: none.
- Reviewed report/decision that later adopts this finding, if known: none yet.

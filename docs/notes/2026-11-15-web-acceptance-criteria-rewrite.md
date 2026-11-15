---
title: WEB acceptance criteria rewrite handoff
date: 2026-11-15
type: project-learning
status: unreviewed
task: WEB02, WEB03, WEB04, WEB07
author: OpenCode editing worker
author_model: openrouter/openai/gpt-6.1-terra
author_variant: unknown
sources:
  - docs/notes/2026-11-15-web-acceptance-criteria-review.md
  - docs/design/web-control.md
  - docs/project-brief.md
  - docs/roadmap.md
  - control/web/README.md
supersedes: []
---

# WEB acceptance criteria rewrite handoff

## Summary

Rewrote the four [packet acceptance blocks](../design/web-control.md#packet-acceptance-detail)
and their shared failure/freshness rules as proposed offline fixture checks.
The independent review's findings are addressed below, not declared independently
closed: security, identity, current-working evidence and clock designs remain
open, and no fixture implements or verifies these proposed contracts yet.

## Claims and evidence

| Kind | Claim | Source / verification / limit |
| --- | --- | --- |
| User requirement | Revocation must deny the credential in another tab and a direct HTTP client. | Assignment, 2026-11-15; simulated test contract, not an observed server feature. |
| Observed | WEB02 addresses identity/access, WEB03 hardware, WEB04 component states, WEB07 metrics/diagnostics; updates/recovery are WEB08. | `docs/roadmap.md` and `docs/design/web-control.md`, read 2026-11-15. |
| Proposed revision | WEB02 addresses F01–F04, F13 and F18: server-side revocation, separate credentials, failure/readback, bound origins, persistence and authenticated-mode distinctions. | The reviewed enrollment, recovery, identity-binding and transport designs remain undecided. |
| Proposed revision | WEB03 addresses F05–F07, F13 and F18: pending/retained/effective selection, fixture apply, scoped evidence, independent unknowns and actionable reasons. | No real hardware pairing is asserted; A01/A02 and authorized operations remain gates. |
| Proposed revision | WEB04 addresses F08–F11, F13–F14 and F18: current versus historic function evidence, per-scope matrix, conservative aggregation, prerequisites and ownership. | Current working remains unknown without a reviewed function-specific evidence contract. |
| Proposed revision | WEB07 addresses F12–F18: counter reset/rebaseline, age and ordering fixtures, diagnostic/trend fixtures, metric calculations and sourced units. | C05 collectors and a trustworthy freshness protocol remain prerequisites; fixtures do not establish hardware support. |
| Observed | None of the 18 review findings was judged wrong. | The rewrite narrows several to checkable fixtures without pretending their open design decisions are settled. |

## Verification

- In `/home/james/Projects/debra`, `python3 -B -m unittest tests.test_docs -v`
  passed all 11 tests before and after this note was added.
- Documentation tests check repository links/assets and source-register structure,
  not the proposed criteria's completeness, security or device behavior.
- No device, audio, credentials, production server, implementation tests, commit
  or push. No independent review of this rewrite has yet occurred.

## Handoff

- `main` was initially clean; later inspection saw concurrent changes outside the
  assigned files. Leave those changes intact and recheck the moving checkout.
- The prototype guide and roadmap were read before those concurrent changes;
  revalidate current-code gap statements against the integration candidate.
- Obtain separate review of the actual diff and unresolved design questions.
  A fixture proposal is not authorization for device work or an accepted design.

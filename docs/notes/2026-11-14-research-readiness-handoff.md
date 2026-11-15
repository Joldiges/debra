---
title: Corrected research synthesis and partial AI readiness
date: 2026-11-14
type: project-learning
status: unreviewed
task: F01/F05 and bounded research preparation
author: OpenCode coordinator
author_model: openrouter/openai/gpt-6.1-sol
author_variant: flex-xhigh
sources:
  - docs/research/2026-11-14-preliminary-findings.md
  - docs/testing/results/2026-11-14-ai-readiness.md
  - .local/delegation/20261114-parallel-research/ task and host metadata
supersedes:
  - Only the uncommitted integration state in 2026-11-14-deepseek-documentation-pilot.md
---

# Research and readiness handoff

## Summary

The [preliminary synthesis](../research/2026-11-14-preliminary-findings.md)
preserves corrected findings from six research submissions without accepting
their roadmap packets. The [readiness report](../testing/results/2026-11-14-ai-readiness.md)
closes F01's baseline/ownership assessment and leaves F05 incomplete, with
production dispatch closed. No CAD or appliance implementation was delivered.

## Observations and limits

- Separate capable triage found material errors in four drafts. Review is
  necessary even when workers provide long source tables; it is not proof of
  every surviving claim. Source research and physical validation remain separate.
- The supplement's four sentinels match expectations, but an extra empty audit
  file caused the coordinator's directory assertion to fail. Its unknown origin
  and untested alternate tool routes are preserved, not converted into a pass.
- Historical accepted status-page bytes were verified in commit `0e0d03b…`;
  earlier reports describing them as uncommitted remain as dated evidence.
- Before this candidate, `main` and the remote were verified at `88e1fcb…`.
  Review/integration metadata records the later exact candidate and checks.
- The original lock-race test fixture depended on F01 remaining unfinished;
  recording F01 complete made its synthetic blocked R01 state invalid. The
  fixture now completes R01 while the worker waits, preserving the same
  ineligibility check without changing production validation. All 15 tests pass.
  A separate disposable fixture deliberately restored stale pre-lock parsing:
  the repaired test failed as expected because that defective worker claimed
  completed R01. No production implementation or acceptance assertion changed.
  The initial failing log and mutation evidence remain in
  `.local/reviews/research-readiness-20261114/`.

## Cost coverage and next action

Captured host costs: four restarted DeepSeek research tasks **$0.08152**,
F04 preparation **$0.01091**, research triage **$0.20909**, synthetic supplement
**$0.00213**, and the earlier enclosure-requirements review **$0.04943**.
These selected entries total approximately **$0.35308** (unrounded host values:
**$0.353075902**), excluding coordinator,
this candidate's review, earlier pilots and failed subscription attempts.
They are not the account bill, remaining balance, enforced cap or proof of Flex
billing. The OpenAI subscription was not retried after James's limit report.

Next: resolve exact mechanical revisions/dimensions and provenance; complete
claim-sized research reports; plan safely intercepted F05 coverage. No note
authorizes live operations, new tooling, pruning, license application or release.

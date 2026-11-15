---
title: Task-chain review findings and regression repairs
date: 2026-11-14
type: project-learning
status: unreviewed
task: Task-chain workflow review
author: OpenCode coordinator
author_model: openai/gpt-6.1-sol
author_variant: unknown
sources:
  - Read-only reviewer session ses_e236e20edffe7dElMhbyyXgolT
  - Commit 655d1824ea61a77feced9f83ce1ea37e46d07c77
  - tools/taskchain.py and tests/test_taskchain.py
supersedes:
  - Earlier 13-test verification as sufficient coverage of fixture isolation and baseline interleaving
---

# Task-chain review findings and regression repairs

## Summary

The separate capable reviewer requested changes to the
[first task-chain candidate](2026-11-14-task-chain-dispatch.md). Two missing
failure cases were subsequently reproduced in disposable repositories and
covered by passing regressions. These repairs require renewed review; this note
does not establish acceptance, F05 permission enforcement, or worker readiness.

James reported committing and pushing the first candidate. Local observation
confirmed clean `main` at `655d182`, with its tracking ref showing no divergence.
The explicit 21 implementation files still had SHA256
`d461924aa5c559005e41d6a5f4612cb13230cd54d642a68789cba687618377b3`.
The agent did not commit or push that baseline or the subsequent repairs.

## Review and observed reproductions

Reviewer: separate OpenCode child session, host-reported
`openai/gpt-6.1-sol`, variant unknown. Another session of the same model gives
fresh context, not fully independent evidence. It inspected all 21 files and
the actual original diff, ran no implementation/tests, and returned
`changes-requested` for these two findings:

| Finding | Reproduction in disposable fixtures | Repair |
| --- | --- | --- |
| High: inherited Git environment could redirect fixture operations into another repository | Restoring the inherited-environment implementation caused the new sentinel regression to fail: the disposable sentinel's `.git/config` changed from its own identity to the fixture identity. | Fixture subprocesses discard inherited `GIT_*` settings, ignore global/system Git configuration, and explicitly disable hooks. Regression checks sentinel config/index/HEAD/file bytes and resolved HEAD. |
| Medium: `start` parsed eligibility before taking the shared lock | With the committed old dispatcher, a pipe-controlled delayed startup selected R01 after the coordinator committed and approved a new baseline marking it blocked. The regression failed because startup incorrectly succeeded. | Startup validates/selects inside the locked transaction using catalog/roadmap/card inputs read from the immutable approved commit. The regression now refuses the blocked starter without creating a claim. |

The reproductions restored the old behavior only in copied test scaffolds under
`/tmp/opencode/debra-review-regressions-11y0jjpx/`. All fixture repositories and
scaffolds were retained. No production checkout/configuration/index, device,
network service, or actual model permission policy was used as a failure target.

## Verification

From the Debra root:

- `python -B -m unittest discover -s tests -v`: **15 passed** on Python 3.15.2.
- New focused tests can be selected with
  `python -B -m unittest discover -s tests -v -k inherited_git_environment`
  and `python -B -m unittest discover -s tests -v -k start_rechecks_approved_baseline`.
- In the copied mutation scaffolds, those same new regressions failed against
  the respective restored old behaviors, as expected. They passed with the
  repaired implementation; acceptance criteria were not weakened.
- Earlier passing 13-test results remain historical observations, not proof
  that the newly identified cases were covered.

## Handoff and limits

Next: re-review the exact repair diff, independently rerun safe checks, and
record the resulting candidate identity. Keep production dispatch closed.
Do not reinterpret James's baseline commit/push or model-capability question as
approval to activate worker profiles, open dispatch, or operate devices.

DeepSeek V4.1 Flash 1017 was discovered in the host model catalog as
`openrouter/deepseek/deepseek-v4.1-flash-1017`, with `none`, `low`, `high`, and
`max` variants. This is model availability evidence only: no DeepSeek worker,
actual execution test, or F05 pilot has occurred. Model selection, effective
restrictions, and a one-task pilot still need their explicit reviewed scope.

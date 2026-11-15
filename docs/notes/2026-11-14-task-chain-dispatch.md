---
title: Named task chains and local cooperative dispatcher
date: 2026-11-14
type: project-learning
status: unreviewed
task: Task-chain workflow
author: OpenCode coordinator
author_model: openai/gpt-6.1-sol
author_variant: unknown
sources:
  - James's request for any/named task-chain self-selection in this conversation
  - Local git status and commit 39b93fb3ed1956dfd76b888fadb05008b7b8e1be
  - tools/taskchain.py and tests/test_taskchain.py
supersedes:
  - Earlier uncommitted-planning and staged-removal state observations only
---

# Named task chains and local cooperative dispatcher

## Requirements and observed state

James wants many activity streams and a short worker entrypoint: “work on any
task chain” or a named chain, with separate workspaces and visible ownership.
The coordinator still owns scope, architecture, review, and integration.

The local planning baseline is now `39b93fb` (“AI fresh start”), which contains
the planning documents. Git status/index were clean at the beginning of this
task-chain work. This supersedes **only** the earlier uncommitted/index-state
observations in the [initial learning note](2026-11-14-project-learning-baseline.md)
and earlier foundation handoffs; it does not review their product claims.
No commit/push was performed by this task-chain implementation session.

## Implementation and verification

The [dashboard](../task-chains.md) and catalog map all 63 roadmap packets exactly
once into 19 chains. Nine public-source research starters have bounded cards.
Future packets retain roadmap prerequisites and require new coordinator briefs;
self-selection does not authorize an entire stream.

`tools/taskchain.py` uses a Git-common-directory registry, POSIX `flock`,
reservation-before-worktree creation, and atomic JSON replacement. Linked
worktrees see the same claims. It creates dedicated branches/checkouts and
filled local assignments, retains failed/blocked/submitted ownership, fingerprints
submissions, and records coordinator outcomes without merging or deleting work.

Verification from the Debra root:

- `python tools/taskchain.py check`: passed, 19 chains / 63 packets.
- `python -B -m unittest discover -s tests -v`: 13 offline fixture tests passed
  on Linux/Python 3.15.2. Includes simultaneous same-chain contention (one winner),
  visibility/dispatch from linked worktrees, any-chain selection, branch/base/
  staging/path/symlink rejection, failed creation reservation, blocked/resume/
  release behavior, frozen candidate and integration-file verification.
- `python tools/taskchain.py list`: production dispatch closed, no claims;
  read-only listing did not open dispatch.
- Local Markdown link/anchor and whitespace checks passed before this note was
  added; final recheck belongs to the coordinator's handoff.

The first fixture run exposed use of `Path.open(opener=...)`, which is not a
supported argument; using built-in `open` corrected the implementation. A
refused dispatch intentionally need not create `state.json`; the fixture reader
now treats absent state as empty, matching the helper. Final tests above passed.
No acceptance criteria were weakened to manufacture a pass.

## Limits and next action

This is cooperative **single-clone, one-host coordination**, not isolation,
credential protection, remote locking, device leases, model routing, verified
role permissions, independent-review enforcement, or an appliance runtime test.
Fixtures use synthetic pilot evidence, not actual F05 approval. They are retained
under `/tmp/opencode/debra-taskchain-tests-*` without automatic deletion.
No production registry approval, real worker launch, live device/host installation,
network change, remote Git operation, or publication was performed.

Next: independent capable review and safe check rerun; then a deliberate local
checkpoint if authorized, plus actual F05 model/permission pilot before opening
production dispatch. This note is evidence, not authorization for those actions.

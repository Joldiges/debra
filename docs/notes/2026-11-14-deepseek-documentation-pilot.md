---
title: DeepSeek documentation pilot with bounded repair and independent review
date: 2026-11-14
type: project-learning
status: unreviewed
task: F05 bounded documentation pilot
author: OpenCode coordinator
author_model: openai/gpt-6.1-sol
author_variant: xhigh
sources:
  - James's pilot request and coordinator-review clarification in this conversation
  - Base commit b3d5871c28acbb20802c30a9feaa30102a872c46
  - docs/guides/current-status.md and docs/ai-workflow.md
  - .local/pilots/f05-deepseek-20261114/ candidate, policy, tool, review, and integration records
  - https://opencode.ai/docs/permissions (read 2026-11-14)
supersedes:
  - Availability-only/no-actual-pilot observation in 2026-11-14-task-chain-review-repairs.md, lines 73-77
---

# DeepSeek documentation pilot

## Summary

DeepSeek produced a useful [beginner status page](../guides/current-status.md)
within a single-file assignment and one bounded repair. A separate read-only
reviewer accepted the repaired candidate; the coordinator also accepted it,
reproduced checks, and applied its exact bytes locally on `main`. The page is
382 words and remains uncommitted and unstaged at this handoff.

This is an observed documentation result, not approval of F05, production
dispatch, autonomous editing, an OS sandbox, or any appliance capability.
The learning note itself is unreviewed; the separate acceptance covers the
identified page, not this later coordinator-authored report.

## Claims and evidence

All observations below are scoped to this local pilot on 2026-11-14.
Artifact names refer to the ignored evidence directory listed below.

| Kind | Claim | Source | Verification and limits |
| --- | --- | --- | --- |
| user-requirement | James wanted an actual DeepSeek task and capable-agent review, not routine user review. | Conversation request and clarification | One small documentation pilot; no hardware or publication authorization. |
| observed | Worker used `openrouter/deepseek/deepseek-v4.1-flash-1017#high`. | `worker-observed.json`, `revised-worker-frozen.json` | Actual execution/model evidence, not just configured availability. |
| observed | Separate reviewer used `openrouter/google/gemini-4-hydrogen`; variant unknown. | `first-review.json`, `revised-review.json` | Verified assistant-message model; repaired review made 11 successful reads. |
| observed | Coordinator used `openai/gpt-6.1-sol#xhigh`. | Host session record and `coordinator-accepted.json` | Host-reported identity; model labels do not establish correctness. |
| observed | A dedicated worktree and session-specific deny-all policy allowed only named reads and the assigned page edit. | Assignment, phase policies, frozen worker record | Global configuration unchanged; worktrees are not security isolation. |
| observed | All 21 initial and seven edit-enabled policy-decision probes matched expectations. | `phase1-decision-probes.json`, `phase2-decision-probes.json` | Permission decisions, not 28 actual prohibited tool executions. |
| observed | Actual prohibited read, edit, and external-path read calls were rejected. | `preflight-denials.json` | `permission.rejected` for `read`, `edit`, and `external_directory`; both synthetic sentinels remained unchanged. |
| upstream-documented | `edit`, `write`, and `patch` use the `edit` permission action. | [OpenCode permissions](https://opencode.ai/docs/permissions) | Creating the assigned missing page with `write` after `edit` returned “File not found” was not a permission bypass. |
| observed | Initial reviewer acceptance was overridden by coordinator changes-requested. | `first-review.json`, `coordinator-changes-requested.json` | Separate review did not eliminate the need for coordinator source checking. |
| observed | Repaired candidate received its own independent acceptance and coordinator acceptance. | `revised-review.json`, `coordinator-accepted.json` | Acceptance applies only to the exact repaired hashes below. |

The worker reported shell, Code Mode, MCP, web/discovery, and nested delegation
unavailable. Policy probes covered their action routes without executing live
infrastructure operations. Actual denial evidence is limited to the harmless
calls above; this is not an exhaustive alternate-tool or sandbox assessment.
Worker edit permission was removed again before each candidate review.

## Candidate identity and repair

Base: `b3d5871c28acbb20802c30a9feaa30102a872c46`.
Worker branch: `pilot/f05-deepseek-20261114`, in the retained
`.local/worktrees/f05-deepseek-20261114/` checkout.
Only `docs/guides/current-status.md` was assigned to the worker.

SHA256 identities:

| Candidate | Size / words | File SHA256 | Patch SHA256 |
| --- | --- | --- | --- |
| Initial, not integrated | 2494 bytes / 368 | `087e490e9e9383794233fd111283e3d5796b3f49a7f02267c2d3d1f5084c99cb` | `aa1670c0d43e813b15f6c9c840eedae18a8a80bf5521a3d74a9e6349c6f9b0a7` |
| Repair 1, accepted and applied | 2667 bytes / 382 | `2df05910652aff2331f51a95fad525a221d80ba6ed31283f1b2ac6fecd6ccc7d` | `b7f6bc0f0502cfa2e26b8d37bb78597ddf3f866cf6a2167db44d39837c855110` |

Coordinator repairs addressed unsupported historical absence claims, overly
broad backlog wording, tentative browser onboarding, integration-stale status
wording, and terminology. The repaired page separates available documentation
and coordination tooling from the intended, unvalidated device journey.

The remaining non-blocking finding is line 41: “None of these steps works
today” could sound like a claim about generic Wi-Fi/SSH when read alone.
Accepted in context as Debra's absent integrated journey; no optional polish
was applied after review, preserving exact candidate identity.

The revised worker handoff reported roughly 362 words and three edit calls.
Actual evidence shows 382 whitespace-delimited words, four successful edits,
and three reads during that repair. Use `repair-round-tools.json` for those
counts: `revised-worker-tools.json` includes a broader initial-work window.
Handoff self-reports were not substituted for tool or byte-level evidence.

## Verification

Coordinator ran these safe commands from both the worker checkout and the
main Debra root:

- `python tools/taskchain.py check`: **pass**, 19 chains cover 63 packets.
- `python -B -m unittest discover -s tests -v`: **pass**, all 15 tests.
- `git diff --check`: **pass** for tracked changes; untracked files also
  received explicit UTF-8, LF, final-newline, and trailing-whitespace checks.

Additional checks: **pass** for the page's 400-word limit, all three relative
links, accepted file/patch hashes, exact worker-to-main byte equality, unchanged
source hashes against the base in both checkouts, unchanged sentinels, and
allowed changed paths. The coordinator-added note was checked separately for
links and whitespace; it is not part of the worker's single-file candidate.
Private evidence directories/files use owner-only `0700`/`0600` permissions.

Tests are offline dispatcher fixtures, not appliance, model-permission, or
hardware tests. No backup scripts were executed. No device/recovery operation,
host installation, infrastructure change, commit, push, or dispatch opening
was performed for this pilot. No enforced merge gate or backup/restore
demonstration was established.

### Cost and evidence retention

Host-reported worker cost was approximately **$0.02209**; both independent
reviews together were **$0.28431** (raw values
`0.022090401999999995` and `0.284306925`). These exclude coordinator work,
setup, and integration; they do not establish total savings or future rates.

Private evidence is retained under
`.local/pilots/f05-deepseek-20261114/`, including both candidates/patches,
assignment/policy probes, actual tool summaries, handoff, review decisions,
`revised-coordinator-verification.json`, and `final-integration.json`.
These local artifacts are ignored, not shipped documentation or an independent
backup; no raw session transcript or credential material is copied into this note.

## Handoff and correction links

- Local integration: `main` remains at the recorded base, with the exact
  accepted page and this coordinator note unstaged/uncommitted. No integration
  commit exists.
- This supersedes only the earlier
  [availability-only observation](2026-11-14-task-chain-review-repairs.md)
  that no DeepSeek pilot had occurred. Preserve that earlier note and its
  separate safety/readiness limits.
- Next, the coordinator can assess remaining F05 gates against this bounded
  evidence. This suggestion does not authorize another task, automatic model
  routing, permanent worker profiles, production dispatch, or publication.
- Routine worker review remains the coordinator's responsibility; bring James
  only material decisions, blockers, physical actions, or new authorization.
  The [roadmap](../roadmap.md) and [AI workflow](../ai-workflow.md) remain the
  canonical backlog and governance, unchanged by this note.

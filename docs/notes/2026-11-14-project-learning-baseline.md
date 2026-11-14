---
title: Debra project learning and context handoffs
date: 2026-11-14
type: project-learning
status: unreviewed
task: Documentation planning
author: OpenCode coordinator
author_model: openai/gpt-6.1-sol
author_variant: unknown
sources:
  - James's project-workflow and documentation steering in this conversation, 2026-11-14
  - docs/README.md
  - docs/ai-workflow.md
supersedes: []
---

# Debra project learning and context handoffs

## User requirements

James wants a capable AI to coordinate and review bounded work from lower-cost
models rather than making him supervise each worker. He also wants useful
project learning retained in the repository so that context switching does not
lose it. Suggested folder names included `dumping_ground`, `humans`, and
`verbose`; he explicitly left the structure to the coordinator.

PiCompose is worth studying, not a selected foundation. Alternative boards
such as Orange Pi should be considered when exact HAT or other audio options
can be substantiated. These are research requirements, not tested compatibility.

## Proposed structure and observed documentation

The [documentation index](../README.md) uses purpose-based locations instead
of duplicate human/AI document trees: dated learning notes, task research,
reviewed design decisions, guides, comparisons, and test evidence. Several
locations are planned, not populated. The
[learning-note template](../templates/learning-note.md) distinguishes sources,
observations, hypotheses, uncertainty, and corrections.

The [AI workflow](../ai-workflow.md) describes a capable coordinator/reviewer,
bounded editing worktrees, explicit handoffs, and review before integration.
This is written guidance, not verified cheap-worker isolation or automated
merge/model-routing controls. The current documentation is uncommitted.

## Verification and limits

This note records user statements and the authored documentation structure.
It does not claim any application, hardware, recovery, worker-permission, or
publication test. Final documentation checks and review belong in the task's
handoff, not an assumed success in this note. No credentials or private device
records are included.

## Next action

Finish reviewing the documentation, establish the deliberate Git baseline
without sweeping in existing staged removals, then pilot a small worker task
with verified permissions and independent capable review. The roadmap and
current user authorization, not this note, determine what can start.

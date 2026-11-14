# Worker task template

The coordinator fills this before dispatch. An unfilled template or a roadmap
title is not permission to start. Follow the [AI workflow](../ai-workflow.md).
Keep this task and its eventual handoff free of credentials and raw private logs.

## Assignment

```text
Task ID and narrow objective:
Role: research / editing worker
Coordinator and independent capable reviewer:
Worker model/variant (host-reported; unknown if unavailable):
Authorized operations and source of authorization:

Base commit:
Assigned branch and absolute worktree:
Candidate/handoff method: uncommitted diff / explicitly authorized local commit
Assignment-ledger entry and file/device ownership:
Prerequisites that are complete:

Read first:
  - AGENTS.md
  - docs/README.md and the relevant latest dated handoff/research/decision
  - docs/ai-workflow.md
  - docs/project-brief.md and docs/evidence.md
  - Exact relevant roadmap packet and existing implementation/source files:

Exact input sources, revisions, and relevant excerpts/examples:
Allowed edit paths (explicit list; empty means read-only):
Allowed research/read scope and tool permissions actually verified:
Coordinator-owned/shared paths excluded:
Explicit non-goals and forbidden actions:

Acceptance criteria (observable pass/fail, not "works"):
  1.
  2.
Checks that exist: exact command, working directory, expected result
Checks the coordinator will run instead of the worker:
Checks not possible here and how those limits affect acceptance:

Budget: time/steps if supported; one submission + one repair round by default
Stop/escalation conditions:
Expected deliverable and handoff location:
Learning-note path if useful discoveries should be recorded (otherwise hand off to coordinator):
```

Do not include a placeholder command as though it were a working test.
No shell/host installation, infrastructure access, secrets, nested agents,
architecture/interface changes, test weakening, merging, pushing, or publication
unless the appropriate action is specifically authorized; workers never
self-approve or merge. An allowed edit path is not permission to operate a
device mentioned in that file. Permissions must match the assignment; a prompt
cannot grant a tool that the host has denied.

## Required acknowledgement before editing

```text
I understand the goal as:
I have read:
My assigned base / branch / worktree and observed clean state:
I may change only:
I will verify using:
I will stop and ask the coordinator if:
Missing or contradictory inputs:
```

If required identity/state checks are unavailable to the worker, the coordinator
must verify them and supply the result. Do not fabricate a successful check.
Stop if inputs are missing, scope is ambiguous, or the worktree has unexpected
changes.

## Required handoff

```text
Task / worker / exact model and variant (or unknown):
Base commit / branch / worktree:
Candidate commit or coordinator-captured patch identity:
Files changed and reason for each:
Acceptance criteria: pass / fail / partial / not-run, with evidence
Sources, exact revisions, and date checked:
Commands actually run, working directory, results:
Checks delegated to coordinator or not run:
Known failures / uncertainty / provenance or licensing concerns:
Durable learning / canonical report or note links (not a raw transcript):
Out-of-scope changes requested, not made:
Status: submitted / blocked (not self-approved)
Next action for coordinator:
```

The coordinator captures the exact candidate, obtains independent review,
records its own check results, and decides integration. Worker confidence,
model branding, or a generic successful tool response is not acceptance.

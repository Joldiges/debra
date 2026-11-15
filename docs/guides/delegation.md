# Delegation: role profiles and the record of delegated work

Two small things make coordinator-assigned AI work reviewable: a worker whose
*permissions* stop it wandering, and a durable record of what was assigned, what
came back, what a reviewer saw, and where each file went. This page covers both.
Neither is required for ordinary work — see [Cost to development](#cost-to-development).

The operating model itself (one coordinator session, subagents as workers,
independent review before integration) is in the [AI workflow](../ai-workflow.md#operating-model-as-practised-2026-11-15).
The cross-clone claim registry in [task chains](../task-chains.md) is a different
mechanism and remains closed at F05; this page does not open it.

## Restricted role profiles

Two read-only profiles are committed:

| Agent file | Role | Cannot |
|---|---|---|
| `.opencode/agents/debra-research.md` | source research, cited report back | edit, shell, subagent, Code Mode, MCP, `.local/` reads |
| `.opencode/agents/debra-review.md` | independent review of a frozen candidate | edit, shell, subagent, Code Mode, MCP; may read `.local/coord/` and `.local/reviews/` |

Both deny everything first, then allow only reading, `glob`, `grep`,
`webfetch` and `websearch`, and deny reads outside the repository, `.git/`,
`.local/` and `.env` files. The reviewer is the one exception: it may read the
candidate paths under `.local/coord/` and `.local/reviews/`. An editing
assignment gets a **generated** profile instead, because only the assignment
knows the allowed paths:

```bash
python tools/coord.py profile --task CMP02 --role edit \
    --path docs/research/x.md --path tests/test_x.py
# → .opencode/agents/local-cmp02.md, edit allowed only on those two paths
```

Generated profiles are ignored by Git (`/.opencode/agents/local-*.md`): they are
per-task state, not shared configuration. OpenCode watches its config, so the
file is picked up without a restart; launch the subagent with that agent ID.

What this is and is not:

- OpenCode's permission layer enforces these rules — the deny/allow ordering is
  the documented V2 behaviour (last matching rule wins). A worker does not
  negotiate its way past them by prompt.
- It is **not a sandbox**: a profile is a narrowing of one tool-using process
  running as your user, not a filesystem or network boundary. Shell is denied
  because a shell would erase the distinction.
- **Loaded, not executed.** On 2026-11-15 the running service returned both
  profiles — and a generated editing profile — from
  `GET /api/agent?location[directory]=<repo>`, with the rules composed as
  intended: `edit`, `shell`, `subagent`, `execute` and external reads resolve to
  `deny`, while `read`, `grep` and `webfetch` resolve to `allow`, and the secret
  paths stay denied. That is configuration evidence, not execution evidence: no
  tool call has been attempted under these rules, so a real denial has not been
  observed here. F05 stays partial and production editing dispatch stays closed.
- **Lexical path resolution.** Matching is lexical, and the F05 source review
  found an upstream patch test that follows a symlink inside the repository to an
  external file without external-directory approval. A symlink planted in the
  workspace is therefore a way around a path rule. Treat the path rules as scope
  control, not as containment, and keep real secrets out of reach by permissions
  that do not depend on path text.
- **One working directory.** Resource patterns are relative to the session's
  working directory, and copying a generated profile into another checkout does
  not re-scope it. Generate the profile for the directory the worker will use.
- `external_directory: deny` is what stops a profile reading outside the repo;
  the built-in default allows it.
- Agent rules are appended *after* the global ones, so the profile's broad
  `read: *` allow would otherwise re-open the global secret denies (`~/.ssh`,
  `~/.gnupg`, `~/.aws`, `auth.json`, `.env`). The profiles restate those denies
  after the allow for that reason; keep that order if you edit them.

## The record of one delegated task

```bash
# 1. record the assignment before the work exists
python tools/coord.py launch --task CMP02 --role research \
    --model openrouter/deepseek/deepseek-v4.1-flash-1017#high \
    --base HEAD --prompt-file .local/coord/cmp02-brief.md

# 2. after the subagent replies (model, cost and tokens come from OpenCode)
python tools/coord.py capture --task CMP02 --session ses_abc123
#    or, when the session id is not available
python tools/coord.py capture --task CMP02 --report reply.md

# 3. freeze the candidate a reviewer will read
python tools/coord.py snapshot --task CMP02 --path docs/research/CMP02-x.md

# 4. record the separate review, naming the candidate hash
python tools/coord.py verdict --task CMP02 --reviewer "capable reviewer" \
    --model openrouter/openai/gpt-6.1-sol#high --verdict approve \
    --report .local/coord/cmp02-findings.md
```

Then `status` shows every task with its stage and recorded spend, and `check`
verifies the records still agree with each other.

| File under `.local/coord/<task>/` | Holds |
|---|---|
| `launch.json` | task, role, exact model, base commit, allowed paths, budget, brief hash |
| `brief.md` | the prompt that was actually sent |
| `submitted.md` | the reply, hashed at capture |
| `metadata.json` | model, agent, cost, tokens, outcome, report hash, session errors |
| `review/candidate.patch` | the frozen diff against the base, including untracked files |
| `review/manifest.json` | base, patch hash, per-path hashes, byte counts |
| `review/verdict.md` | reviewer, reviewer model, verdict, and the candidate hash reviewed |

The refusals are the point: a report cannot be rewritten after capture, a
verdict cannot exist without a frozen candidate, a verdict cannot approve a hash
different from the candidate's, and a second report or verdict needs `--force`.
`check` catches the rest — a tampered report, a missing brief, a base commit that
no longer resolves, a manifest without its patch.

```bash
python tools/coord.py status
python tools/coord.py check
```

`check` reports consistency of bookkeeping only. It cannot tell whether the
review was honest, the model was the one recorded, or the claims are true. Those
stay with the reviewer and the coordinator.

## Cost to development

Nothing here is a gate on ordinary work:

- No subagent has to use a restricted profile; the default agents still work.
  Use the profiles when a worker is lower-cost, when its inputs are untrusted, or
  when you want a denied edit to be a refusal rather than an instruction.
- No task has to be recorded. A small change made by the coordinator directly
  needs no `launch`, no `capture`, and no verdict.
- Recording is cheap because it is one command at each end of work you already
  do, and `capture` fills model/cost/tokens from OpenCode rather than from memory.
- The records are local and ignored. Nothing is committed, so nothing has to be
  rebased, reviewed, or cleaned up before a push. Historical waves under
  `.local/delegation/` stay as they are; this tool does not rewrite them.

## Privacy and retention

`.local/` is ignored by Git and is not a backup. Records are written `0600`
inside `0700` directories. Keep populated device configs, keys, tokens and raw
logs out of briefs and reports — reference them by name. Do not automate expiry:
records are evidence, and a deleted record is a review nobody can check later.

## Non-goals

- It does not launch, route, or select models. The coordinator launches the
  subagent; the model is recorded, not chosen here.
- It does not review anything, and it cannot enforce that a review happened. A
  verdict file records a claim by a named reviewer.
- It does not merge, commit, or push, and it does not replace the task-chain
  claim registry, F05's executed permission evidence, or CI.
- It does not make a captured report into an accepted result.

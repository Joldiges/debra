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

Both deny everything first, then allow only `read`, `webfetch` and `websearch`,
and deny reads outside the repository, `.git/`, `.local/` and `.env` files. The
reviewer is the one exception: it may read the candidate paths under
`.local/coord/` and `.local/reviews/`. They have no `grep` or `glob` — see
[the probe result](#what-a-probe-observed) for why search is not the same as
read. An editing assignment gets a **generated** profile instead, because only
the assignment knows the allowed paths:

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
  `deny`, while `read` and `webfetch` resolve to `allow`, and the secret paths
  stay denied. That is configuration evidence; the first live probe is
  [below](#what-a-probe-observed). F05 stays partial and production editing
  dispatch stays closed.
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

## What a probe observed

2026-11-15, three short sessions, $0.0071 total, canary files only. The full
record is [the F05 probe note](../notes/2026-11-15-f05-live-permission-probes.md);
the short version:

| Attempt | Result |
|---|---|
| `read AGENTS.md` | succeeded — positive control |
| `read /etc/hostname` | refused, `Permission denied: external_directory` |
| `read .local/scratch/…/sentinel.txt` | refused, `Permission denied: read` |
| `grep SENTINEL-7f3a` in that same `.local/` directory | **succeeded — returned the denied file's content** |
| `glob .local/scratch/**` | no files, no error; inconclusive, because dot-directories are hidden by default |
| `edit AGENTS.md` from a one-path editing profile | refused, `Permission denied: edit` |
| `edit` the one allowed path | succeeded |
| `write` a new file | refused, `Permission denied: edit` (write is gated by `edit`) |
| `opencode_worktree_remove`, listed in a denied profile | refused, `Permission denied: edit` — listed is not usable |
| edit, write, shell, subagent in a deny-everything profile | tool not present: nothing to attempt |

Three conclusions, all uncomfortable:

1. **A path deny is a per-tool deny.** `grep` authorises its pattern, not each
   file's `read` rule, so a path whose read is denied is still readable through
   search. The restricted profiles therefore carry no `grep` or `glob` by
   default, leaving `read` as the route that respects the path rules.
   `--allow-search` opts both back in for a checkout with no private state, and
   says what it costs when you use it.
2. **Absent is not refused.** A deny-everything profile removes the tool
   entirely, so an editing or shell attempt cannot happen and no refusal string
   exists to record. That is stronger for safety and weaker as evidence: it says
   nothing about rule ordering. Proving the ordering needs a profile that allows
   the tool and denies one target — which is what a generated editing profile is,
   and it did refuse an out-of-scope edit.
3. **A listed tool is not a usable one.** A denied profile still advertised
   `opencode_worktree_remove`, and the call was refused. Judge a worker by its
   refusals, not by its tool list.

One model, one location, three short sessions: this moves F05 forward and does
not close it.

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

## Defaults, and what this will never do

The defaults are the frictionless ones, deliberately:

- The built-in `build`, `general` and `explore` agents are untouched. The
  coordinator still edits, commits and integrates directly, and no ordinary task
  needs a profile, a record, or a verdict.
- A restricted profile is chosen per assignment, not imposed globally, and the
  only thing it can ever do is *narrow* what one subagent session may touch.
- `--allow-search` turns `grep`/`glob` back on when a worker needs to search and
  the checkout has no private state, instead of leaving it unable to work.

Four things this tooling must never grow, because they would be safety theatre:

1. **No auto-approval.** `verdict` transcribes a review that a named reviewer
   wrote; it cannot review, and no command changes a verdict to `approve` on its
   own. Nothing here can mark work accepted, merged or done.
2. **No permission approval.** It writes an agent file; it never replies to a
   permission prompt, sets "allow always", or edits saved approvals.
3. **No silent broadening.** A generated profile's allowlist comes from the
   assignment's named paths. Widening it is a new command someone can see and
   review, not a side effect.
4. **No enforcement claim.** Records are evidence of what was assigned and what
   came back. They are not proof a review happened, and passing `check` means the
   bookkeeping agrees with itself, nothing more.

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

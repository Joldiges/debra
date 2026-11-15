---
title: Scoping the agent permission relaxation to this project
date: 2026-11-15
type: project-learning
status: unreviewed
task: F06
author: OpenCode subagent
author_model: openai/gpt-6.1-terra
author_variant: flex-high
sources:
  - /home/james/.config/opencode/opencode.jsonc, read-only inspection, 2026-11-15
  - /home/james/AI-Work/Memory/memory/decisions.md, decision 18
  - docs/roadmap.md, F06
  - docs/testing/results/2026-11-15-f05-source-feasibility.md
  - https://opencode.ai/docs/config, consulted 2026-11-15
  - https://opencode.ai/docs/permissions, consulted 2026-11-15
  - https://opencode.ai/docs/agents, consulted 2026-11-15
  - https://opencode.ai/docs/api, consulted 2026-11-15
supersedes: []
---

# Scoping the agent permission relaxation to this project

## Summary

**Documented:** Project-level configuration exists. Ordinary project settings
can override global settings, but **top-level permission rules are a special
case**: global rules are appended after project rules. A project top-level
shell allow therefore does not beat a matching global shell ask. Agent-specific
rules are appended after global rules and can refine them. See [configuration
locations](https://opencode.ai/docs/config#locations), [permission
matching](https://opencode.ai/docs/permissions#matching), and [agent
merging](https://opencode.ai/docs/agents#merging).

**Inference / proposal:** Change the existing global shell rule to `ask`, and
add project-local shell allows for the four built-in interactive/worker agents.
This is a candidate for review and an actual two-location test, **not an
applied or verified change**. It is narrower than a blanket project rule: custom
agents retain their own rules and may ask or deny. Agent/session rules, saved
approvals, policies and location discovery can affect the final result.

**Documented:** Removing the global shell rule alone would **not** restore
asking: V2's base policy allows `*` actions/resources, including shell. Use an
explicit `ask` instead. The F06 roadmap's suggestion to remove the global ask
is therefore insufficient for the desired outside-project behavior; this note
does not change the roadmap or decide policy.
([Defaults](https://opencode.ai/docs/permissions#defaults).)

## Observed configuration

- **Observed:** `opencode --version` returned `opencode v2.3.0` on 2026-11-15.
  `/home/james/.config/opencode/opencode.jsonc` lines 480–490 contain a
  top-level `permissions` array beginning with exactly:

  ```json
  { "action": "shell", "resource": "*", "effect": "allow" }
  ```

  Its `read` rules allow `*`, then deny `**/.ssh/**`, `**/.gnupg/**`,
  `**/.aws/**`, `**/auth.json`, `**/.env`, and `**/.env.*`. The array also
  contains Basic Memory rules; these must not be changed. The same file's
  comment claims a deny always wins over an allow, which is too broad under the
  documented matching rules below.
- **Observed:** No `opencode.json` or `opencode.jsonc` was found at the Debra
  root, in its `.opencode/`, or anywhere in the repository by the hidden-file
  glob search. Neither direct nor `.opencode/` config was found in `/`, `/home`,
  `/home/james`, `/home/james/Projects`, or `/etc/opencode` by the targeted
  filename check. `/home/james/.config/opencode/opencode.json` and the global
  `agents/` directory were absent. The global JSONC had no `agents`,
  `default_agent`, or `policies` key in the targeted search. This is not an
  inventory of environment-supplied config, plugins, saved approvals, nested
  worktrees, system policies, session-specific permissions, or other locations.
- **Documented:** Shell `*` covers every scanner-produced command resource,
  including subcommands of compound commands; it does not remove independent
  external-directory checks, scanner errors, agent restrictions or hard
  policies. Shell patterns match command text, not project path. The default
  external-directory policy also allows access. See
  [permissions](https://opencode.ai/docs/permissions#actions),
  [directories](https://opencode.ai/docs/permissions#directories) and
  [scanner](https://opencode.ai/docs/permissions#scanner).
- **Documented:** The last matching rule for a given check wins. For an
  operation checking multiple resources, any resolved deny blocks it; saved
  approvals cannot override a configured deny. A later matching configured
  allow **can** override an earlier deny for the same check. The shell allow is
  a different action from the read denies, so it does not itself override them.
  See [matching](https://opencode.ai/docs/permissions#matching) and
  [approvals](https://opencode.ai/docs/permissions#approvals).
- **Inference:** The listed global denies remain in the configuration and are
  expected to apply to matching `read` resources unless a later applicable
  read rule changes the result. They are not universal secrecy guarantees:
  shell, grep, glob, MCP and other routes are separate actions. In particular,
  the documented internal resource is location-relative and `*` is a
  whole-value wildcard; whether a root-relative `.env` matches `**/.env`
  needs a synthetic runtime test. Do not test with real credentials. The
  `**/.env.*` deny also appears to cover `.env.example` where it matches.
  [F05 source inspection](../testing/results/2026-11-15-f05-source-feasibility.md)
  separately notes that grep/glob authorize patterns, not each file's read rule.

## Proposed snippet

**Proposal, not executed:** After James reviews the tradeoffs and recovery,
change **only** the first shell rule in
`/home/james/.config/opencode/opencode.jsonc` from `allow` to `ask`, leaving
the remaining rules and settings in place:

```jsonc
{ "action": "shell", "resource": "*", "effect": "ask" }
```

Also update the adjacent shell-policy comment so it no longer claims
allow-all or an unconditional deny precedence. Then create
`/home/james/Projects/debra/opencode.jsonc` with exactly:

```jsonc
{
  "$schema": "https://opencode.ai/config.json",
  "agents": {
    "build": {
      "permissions": [
        { "action": "shell", "resource": "*", "effect": "allow" }
      ]
    },
    "plan": {
      "permissions": [
        { "action": "shell", "resource": "*", "effect": "allow" }
      ]
    },
    "general": {
      "permissions": [
        { "action": "shell", "resource": "*", "effect": "allow" }
      ]
    },
    "explore": {
      "permissions": [
        { "action": "shell", "resource": "*", "effect": "allow" }
      ]
    }
  }
}
```

**Documented:** The four names are built-in agent IDs; a same-ID entry refines
that agent, and its permissions follow global rules. The project entry contains
no read rule and so does not itself replace the existing read denies. Agent
definitions and permission rules merge, rather than replacing all other agent
settings. See [built-ins](https://opencode.ai/docs/agents#built-ins) and
[merging](https://opencode.ai/docs/agents#merging).

**Inference:** For these four agents in the Debra location, absent later
restrictions, this should retain the present shell non-prompt; outside the
location they should instead receive a global ask. It does not promise that
custom agents, session-restricted workers, other tools or another checkout have
the same behavior. An agent-level `shell` allow may override an earlier
agent-level shell restriction if the definitions merge in that order: audit
the effective rules for each selected agent before using this proposal, and
do not use it to bypass a worker's assigned restrictions. Hard policies and
session restrictions must also be tested. The plain project-level
`permissions` array is **not** an equivalent alternative. This is only a prompt
policy; a project config inherited by descendants or present in a separately
copied checkout follows OpenCode's discovery rules, not an absolute-path
security boundary. A linked worktree must be checked separately.

## What this does not protect

- **Documented:** Shell runs with the host user's filesystem, process and
  network authority; external-directory inference is best effort
  ([directories](https://opencode.ai/docs/permissions#directories)). Once
  allowed, a command can access files or services outside Debra, including
  credentials available to the user, run destructive commands, or contact the
  network. Read-tool denies do not constrain a shell command.
- **Inference:** Prompt injection in project files, an over-permissioned MCP
  tool, a compromised plugin, a malicious command, symlink escapes and accidental
  writes outside the project are not stopped by this project-scoped rule.
  Written Debra scope rules guide behavior but do not enforce isolation.
- **Documented / observed source report:** A separately restricted dedicated
  agent can reduce available tool actions, but its permissions must be tested
  and are not an OS sandbox. A separately configured, tested filesystem jail,
  such as the organizer's bubblewrap boundary described in
  `/home/james/AI-Work/Memory/memory/decisions.md` decision 17, can hide host
  files; that particular boundary still permits network. A suitable isolated
  environment, restricted integrations and network controls are required for
  stronger protection. F05's source review explicitly warns about symlinks and
  incomplete interception; it is not a sandbox certification.

## Rollback and verification

**Proposal:** Before any separately authorized edit, save a complete, private
copy of the original global JSONC, and after the reviewed change save copies of
both resulting files under an owner-only directory
`/home/james/.config/opencode/backups/f06-2026-11-15/` as
`global-before.jsonc`, `global-after.jsonc`, and `project-after.jsonc`.
Refuse to overwrite existing backup names; verify the copies byte-for-byte,
permissions and recovery before relying on them. These copies may contain
sensitive configuration and must not enter Git. Record the exact changes and
review the global file and its configuration-management source before editing.

**Proposal:** If those three verified backups exist, neither live file has
changed since the proposed edit, and the project file was newly created and
contains only this proposal, the exact rollback command is:

```sh
(
  set -eu
  b="$HOME/.config/opencode/backups/f06-2026-11-15"
  g="$HOME/.config/opencode/opencode.jsonc"
  p="/home/james/Projects/debra/opencode.jsonc"
  d="/home/james/Projects/debra/PendingDiscarding/2026-11-15-f06-opencode.jsonc"
  cmp -s "$g" "$b/global-after.jsonc"
  cmp -s "$p" "$b/project-after.jsonc"
  test -f "$b/global-before.jsonc"
  test ! -e "$d"
  mkdir -p "${d%/*}"
  cp -p -- "$b/global-before.jsonc" "$g"
  mv -n -- "$p" "$d"
)
```

**Inference:** This restores the old global **allow-all shell**, including its
old comment, and preserves rather than deletes the proposed project file. It
does not roll back saved approvals or separate edits. If a comparison fails,
stop: preserve later work and manually reverse only the reviewed F06 edits;
do not overwrite changed files with the older backup. Verify restoration with
`cmp -s "$HOME/.config/opencode/opencode.jsonc" "$HOME/.config/opencode/backups/f06-2026-11-15/global-before.jsonc"` and check the preserved project file is at the stated destination. Watch for errors or a destination race; this is a proposed recovery procedure, not a demonstrated restore.

**Proposal:** With separate authorization, test after the change as follows;
retain sanitized evidence and have James observe the client, not just an agent's
summary:

1. Inspect the effective agent rules and saved approvals using the local client
   and the documented read-only `GET /api/agent/{agentID}` and
   `GET /api/permission/saved` endpoints. Confirm no existing saved shell
   approval matches the harmless test commands; do not publish raw responses.
   Do not remove approvals without separate review.
2. In the **same session**, select `build` and run a harmless shell tool call
   such as `printf 'F06-debra-probe\n'` while located at Debra. James observes
   the actual tool result and absence of a prompt. Move that session to a
   separately authorized location outside Debra using the session-move facility;
   request a distinct harmless `printf 'F06-outside-probe\n'` shell tool call.
   James observes an actual approval prompt; reject it or choose **once**,
   never **always**, so no durable approval alters the test. The client UI or
   `GET /api/permission/request` provides independent prompt evidence. Move
   the same session back and repeat the non-prompt check. Record location,
   agent, command, request/output and whether the session ID stayed the same.
3. Repeat for the other selected built-in agents where applicable and with a
   synthetic denied-path canary, including a root-relative `.env` and a nested
   `auth.json`: request the **read tool**, not shell, and observe the actual
   rejection. Use only separately authorized, nonsecret fixture files and
   preserve them. A denial or an unexpected prompt means the proposed behavior
   is not fully verified; investigate precedence rather than weakening rules.
4. Perform and observe the guarded rollback above, then rerun the same harmless
   location checks and compare restored files. A complete F06 handoff also
   needs independent review and the separately authorized decision update;
   this note itself changes neither.

**Documented:** The client can list agent configuration and pending/saved
permissions via the [OpenCode API](https://opencode.ai/docs/api); saved
approvals can affect subsequent decisions. The actual installed build and its
client behavior, not only the current online documentation, must settle the
test.

## Not verified

- **Observed:** This task changed no OpenCode configuration or permissions;
  it did not commit or push. It created only this proposal note.
- **Not verified:** No effective-policy API response, agent/session rule merge,
  prompt/non-prompt, saved-approval inventory, credential-pattern match, jail,
  or rollback was exercised. Online docs may drift from installed 2.3.0.
- **Not verified:** Other OpenCode locations, environment overrides, plugins,
  custom agents, linked worktrees, Windows settings and configuration-management
  reconciliation were not audited. The next action is James's review, followed
  by separately authorized implementation and observed verification if approved.

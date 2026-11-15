# Unattended runner

**Implemented and exercised 2026-11-15 UTC.** `tools/scheduled_runner.py` runs
one queued task at a time from a systemd user timer so bounded research keeps
moving while no coordinator session is open. It is a review and throughput
control, **not** a permission boundary.

## Design rules

1. A task is an explicitly written prompt with a model, an agent, a timeout and
   the date it was added. Nothing is generated from a roadmap title.
2. One task per invocation, one invocation at a time (a lock file refuses
   overlap). The next task starts as soon as the previous one finishes.
3. Every task carries fixed guardrails appended after its prompt: use the tools
   the task needs, do not install system packages or touch the operator's
   devices and services, never put a credential in a report or on a command
   line, do not delete things you did not create, cite and label every claim,
   and finish with a bounded handoff.
4. The runner never passes `--auto`. A task that would need a new permission
   fails rather than being silently approved.
5. **There is no local spend cap by default** (`daily_budget_usd: null`). James
   enforces spend at the provider by controlling OpenRouter credits. Reported
   cost is still recorded per task and per day so the burn rate is visible.
6. Everything the runner writes lives in the git-ignored `.local/runner/` tree.

## State

| Path | Purpose |
| --- | --- |
| `.local/runner/queue.json` | tasks and their status |
| `.local/runner/config.json` | optional spend cap, default model and agent, timeout |
| `.local/runner/state.json` | per-day reported cost and per-task outcome |
| `.local/runner/activity.log` | one JSON line per finished task; `tail -f` this |
| `.local/runner/runs/<day>-<id>/` | raw event stream, stderr, report and record per task |
| `.local/runner/STOP` | if this file exists, every run exits immediately |
| `.local/runner/prompts/` | prompt files, one per task |

## Commands

```sh
python tools/scheduled_runner.py init
python tools/scheduled_runner.py add --id ID --title "..." --prompt-file .local/runner/prompts/ID.txt
python tools/scheduled_runner.py status
python tools/scheduled_runner.py log --lines 10
python tools/scheduled_runner.py run --once [--dry-run]
```

A report is written to `.local/runner/runs/<day>-<id>/<ID>.report.md` and is
**unreviewed evidence**, not a promoted finding. Promote it the ordinary way:
review the diff and sources, then add a note or a document under `docs/`.

## Schedule

Installed as user units outside the repository (they contain this machine's
paths):

| Unit | Behaviour |
| --- | --- |
| `~/.config/systemd/user/debra-runner.service` | `Type=oneshot`, runs `run --once`, `Nice=10` |
| `~/.config/systemd/user/debra-runner.timer` | one minute after boot, then one minute after each run finishes |

```sh
systemctl --user list-timers debra-runner.timer
systemctl --user status debra-runner.service
tail -f .local/runner/activity.log                  # finished tasks
tail -f "$(ls -td .local/runner/runs/*/ | head -1)"*.events.jsonl   # the live one
```

The event stream is written line by line while a task runs, so the second
command shows what a worker is doing right now rather than only its result.
`activity.log` gets its line when the task finishes.

Stop it without touching the queue:

```sh
systemctl --user disable --now debra-runner.timer   # no new runs
touch .local/runner/STOP                            # belt and braces
```

## Limits worth stating plainly

- **Reported cost is not billing truth.** It is the figure OpenCode prints for
  the session; the provider's invoice remains authoritative. With no local cap,
  the only brake is the credit balance; set `daily_budget_usd` to a number if
  you want a local brake as well.
- **Linger is off** for this user, so the timer only fires while James is logged
  in. That is a deliberate boundary, not a bug.
- **The guardrails are instructions, not enforcement.** What actually constrains
  a task is the permission configuration and what it is able to reach; the
  runner relies on both and on later review of every report.
- A task that blocks on a permission request will sit until its timeout and be
  recorded as failed.
- The runner does not verify the worker's sources. A confidently wrong report
  costs money and produces nothing usable until a coordinator reads it.

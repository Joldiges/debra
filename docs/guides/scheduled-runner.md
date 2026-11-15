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
| `.local/runner/activity.log` | JSON lines for task starts and finishes; `tail -f` this |
| `.local/runner/runs/<day>-<8 hex>/` | raw event stream, stderr, report and record per task |
| `.local/runner/run.lock` | created by the runner when acquiring its exclusive lock; prevents overlapping runs |
| `.local/runner/STOP` | if this file exists, every run exits immediately |

For a normal completed run, `activity.log` has two lines: `start` carries the
UTC time, task ID, title, run directory and model; `finish` carries the task ID,
success flag, reported cost, duration and report path. The `finish` line's
`utc` is the task's **start time**, not its finish time. An interrupted run may
have a `start` without a `finish`, and a report file is only written if the
task produces report text.

The run directory starts with the UTC date (`YYYY-MM-DD`); its suffix is the
first eight hexadecimal characters of a new UUID4, not the task ID. Use the
`start` line's `run_dir` or the `finish` line's report path to find the
directory; its name alone does not identify the task.

The runner writes its PID and start time to `run.lock`, removes it on normal
exit and attempts to reclaim a lock whose owner is no longer alive.

## Commands

```sh
python tools/scheduled_runner.py init
python tools/scheduled_runner.py add --id ID --title "..." --prompt-file /path/to/task-prompt.txt
python tools/scheduled_runner.py status
python tools/scheduled_runner.py log --lines 10
python tools/scheduled_runner.py run --once [--dry-run]
```

Supply an existing prompt file for `--prompt-file`, or pass the text with
`--prompt`; the runner does not create a prompt-files directory. When a report
has text, it is written to `.local/runner/runs/<day>-<8 hex>/<ID>.report.md`
and is **unreviewed evidence**, not a promoted finding. Promote it the ordinary
way: review the diff and sources, then add a note or a document under `docs/`.

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
tail -f .local/runner/activity.log                  # task starts and finishes
tail -f "$(ls -td .local/runner/runs/*/ | head -1)"*.events.jsonl   # the live one
```

The event stream is written line by line while a task runs, so its `tail`
command shows what a worker is doing right now rather than only its result.
`activity.log` records the start and, on normal completion, the finish.

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

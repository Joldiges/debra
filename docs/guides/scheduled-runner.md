# Unattended runner

**Runner exercised 2026-11-15 UTC; automatic refill awaits review and integration.**
`tools/scheduled_runner.py` runs one queued task at a time from a systemd user
timer so bounded research keeps moving while no coordinator session is open.
It is a review and throughput control, **not** a permission boundary.

## Design rules

1. A task is an explicitly written prompt with a model, an agent, a timeout and
   the date it was added. Nothing is generated from a roadmap title.
2. One task per invocation, one invocation at a time (a lock file refuses
   overlap). The timer invokes the next task one minute after the previous one
   finishes. A committed runner refills from the explicit backlog first.
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
| `.local/runner/lock.guard` | persistent coordination file that serializes lock acquisition and stale-lock recovery |
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
exit and attempts to reclaim a lock whose owner is no longer alive. An unreadable
or invalid lock is treated as busy, not guessed to be stale; investigate before
manual recovery. `run`, `add`, and non-dry `refill` use the same lock. An `add`
or refill while a task is running is refused; retry after it finishes. This keeps
the runner's in-memory queue snapshot from overwriting a concurrent addition.

## Commands

```sh
python tools/scheduled_runner.py init
python tools/scheduled_runner.py add --id ID --title "..." --prompt-file /path/to/task-prompt.txt
python tools/scheduled_runner.py refill [--min-pending 3] [--dry-run]
python tools/scheduled_runner.py status
python tools/scheduled_runner.py log --lines 10
python tools/scheduled_runner.py run --once [--dry-run]
```

Supply an existing prompt file for `--prompt-file`, or pass the text with
`--prompt`; the runner does not create a prompt-files directory. When a report
has text, it is written to `.local/runner/runs/<day>-<8 hex>/<ID>.report.md`
and is **unreviewed evidence**, not a promoted finding. Promote it the ordinary
way: review the diff and sources, then add a note or a document under `docs/`.

`refill` reads the single strict block in [the research backlog](../research-backlog.md).
Each line contains an ID, readiness, title and complete one-line scope/prompt;
the tool invents no prompt text. It skips malformed lines, duplicate backlog
IDs, not-ready entries and IDs already in the queue in **any** state, and prints
the reason. In file order it adds only enough ready entries to reach the pending
threshold (default 3); there may be fewer available. A second refill does not
repeat any previously queued ID, including failed tasks. Scope is copied exactly;
the ordinary execution guardrails are appended separately at run time. The
backlog documents the precise format and how to add a new question.

`refill --dry-run` reads but does not create or modify runner state or acquire a
lock. Its count is a point-in-time preview, not a reservation: during a running
task the old runner may still show that task as pending, and the queue can change
before a real refill. A manual non-dry refill is queue editing, not execution:
it can add tasks even if STOP or the spend cap prevents a run. It never changes
an existing task or bypasses execution checks.

## Schedule

Installed as user units outside the repository (they contain this machine's
paths):

| Unit | Behaviour |
| --- | --- |
| `~/.config/systemd/user/debra-runner.service` | `Type=oneshot`, runs `run --once`, `Nice=10`; the existing installed unit needs no edit |
| `~/.config/systemd/user/debra-runner.timer` | one minute after boot, then one minute after each run finishes |

The actual installed `ExecStart` invokes this repository's runner, which after
the STOP and budget checks refills to 3 under the same lock before selecting
the next task. No separate service or extra model call is needed. Automatic
refill is **disabled while `tools/scheduled_runner.py` differs from Git HEAD**,
or if the committed file cannot be read: this prevents an active timer from
queueing unreviewed changes. A coordinator's reviewed integration commit makes
it eligible on the next timer invocation; the backlog itself may be edited
without committing it first. This check is a review aid, not a security boundary.
Existing pending tasks may still run while automatic refill is disabled. A bad
or missing backlog is reported and the existing queue can still run.

This is not a promise that the queue can never be empty: the backlog is finite,
already-used IDs are not retried, entries can be blocked or malformed, and the
timer only works while its user manager is running. Replenishment occurs on
each invocation, not continuously; after a task finishes there can be fewer than
three pending until the next invocation. Review reports and add genuinely new
ready questions as the research evolves. STOP and an exhausted daily cap prevent
automatic refill as well as execution; neither is overridden.

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

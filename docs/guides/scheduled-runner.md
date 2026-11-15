# Unattended runner

**Implemented and exercised 2026-11-15 UTC.** `tools/scheduled_runner.py` runs
one queued task at a time from a systemd user timer so bounded research keeps
moving while no coordinator session is open. It is a spend and review control,
**not** a permission boundary.

## Design rules

1. A task is an explicitly written prompt with a model, an agent, a timeout and
   the date it was added. Nothing is generated from a roadmap title.
2. One task per invocation, one invocation at a time (a lock file refuses
   overlap). A queue drains; it does not fan out.
3. Every task carries fixed guardrails appended after its prompt: read-only, no
   shell, no installs, no device or operator-server contact, public sources
   only, per-claim evidence labels, and a bounded handoff.
4. The runner never passes `--auto`, so a task that would need a new permission
   fails instead of being silently approved.
5. Cost is taken from OpenCode's own event stream, accumulated per day, and
   compared against a budget before the next task starts.
6. Everything the runner writes lives in the git-ignored `.local/runner/` tree.

## State

| Path | Purpose |
| --- | --- |
| `.local/runner/queue.json` | tasks and their status |
| `.local/runner/config.json` | daily budget, default model and agent, timeout |
| `.local/runner/state.json` | per-day reported cost and per-task outcome |
| `.local/runner/runs/<day>-<id>/` | raw event stream, stderr, report and record per task |
| `.local/runner/STOP` | if this file exists, every run exits immediately |
| `.local/runner/prompts/` | prompt files, one per task |

## Commands

```sh
python tools/scheduled_runner.py init
python tools/scheduled_runner.py add --id ID --title "..." --prompt-file .local/runner/prompts/ID.txt
python tools/scheduled_runner.py status
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
| `~/.config/systemd/user/debra-runner.timer` | first run 4 minutes after the timer starts, then every 30 minutes |

```sh
systemctl --user list-timers debra-runner.timer
systemctl --user status debra-runner.service
journalctl --user -u debra-runner.service -n 50
```

Stop it without touching the queue:

```sh
systemctl --user disable --now debra-runner.timer   # no new runs
touch .local/runner/STOP                            # belt and braces
```

## Limits worth stating plainly

- **Reported cost is not billing truth.** It is the figure OpenCode prints for
  the session; the provider's invoice remains authoritative.
- **Linger is off** for this user, so the timer only fires while James is logged
  in. That is deliberate: an unattended runner should not outlive the desktop
  session until someone has reviewed its spending.
- **The guardrails are instructions, not enforcement.** What actually constrains
  a task is the permission configuration and what the task is allowed to reach;
  the runner relies on both and on later review of every report.
- A task that blocks on a permission request will sit until its timeout and be
  recorded as failed. That is the intended outcome, not a bug.
- The runner does not verify the worker's sources. A confidently wrong report
  costs money and produces nothing usable until a coordinator reads it.

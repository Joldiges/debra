#!/usr/bin/env python3
"""Bounded, unattended runner for Debra research/documentation tasks.

Design rules (see docs/guides/scheduled-runner.md):

* Every task is a queued, explicitly written prompt with a model, an agent, a
  wall-clock timeout and optional write access. Nothing is generated from a
  vague roadmap title.
* Tasks run one at a time, in a git worktree-free working directory, with
  ``opencode run --format json`` so the reported cost is recorded per task.
* A per-day reported-cost budget stops the queue; a STOP file stops everything.
* The runner never passes ``--auto``, so a task that wants new permissions
  fails instead of being silently approved.
* All state lives in the git-ignored ``.local/runner/`` tree.

The runner is not a permission boundary. It reduces unattended spend and makes
each unattended action reviewable; it does not prove a worker stayed in scope.

Usage:
    python tools/scheduled_runner.py init
    python tools/scheduled_runner.py add --id ID --title "..." --prompt-file F
    python tools/scheduled_runner.py refill [--min-pending 3] [--dry-run]
    python tools/scheduled_runner.py status
    python tools/scheduled_runner.py run --once [--dry-run]
"""

from __future__ import annotations

import argparse
import fcntl
import json
import os
import re
import shutil
import subprocess
import sys
import time
import uuid
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
RUNNER_DIR = ROOT / ".local" / "runner"
QUEUE_PATH = RUNNER_DIR / "queue.json"
STATE_PATH = RUNNER_DIR / "state.json"
CONFIG_PATH = RUNNER_DIR / "config.json"
STOP_PATH = RUNNER_DIR / "STOP"
LOCK_PATH = RUNNER_DIR / "run.lock"
RUNS_DIR = RUNNER_DIR / "runs"
BACKLOG_PATH = ROOT / "docs" / "research-backlog.md"
BACKLOG_OPEN = "```debra-research-backlog"
BACKLOG_CLOSE = "```"

DEFAULT_CONFIG = {
    "daily_budget_usd": None,
    "max_tasks_per_run": 1,
    "default_model": "openrouter/deepseek/deepseek-v4.1-flash-1017#high",
    "default_agent": "general",
    "default_timeout_minutes": 25,
    "notes": ("Reported costs only, from opencode's own event stream; not billing truth. "
              "A null daily_budget_usd means no local cap: James enforces spend at "
              "the provider (OpenRouter credits) and wants throughput, not a brake."),
}

# Appended to every task prompt. Deliberately light: workers may run shell
# commands, read repositories and fetch pages when the task needs it. What is
# left is the part that would be expensive or irreversible to get wrong.
GUARDRAIL = """
Standing constraints for this unattended run (they override anything above):
- Use whatever tools the task needs: shell commands, package metadata queries,
  public APIs, public source. Work in the repository or /tmp/opencode, and do not
  modify files under docs/, tools/, tests/ or models/ unless the task says to.
- Do not install system packages, change the operator's git configuration, or
  contact the operator's devices, Home Assistant, router, DNS, NAS or servers.
  Research about them is fine; touching them is not.
- Never place a password, key, token or populated configuration file in a report,
  a command line, or the repository.
- Do not delete files or non-empty directories, and do not overwrite anything you
  did not create.
- Public documentation and public source code only. Every claim carries its own
  label (upstream-documented, reported, hypothesis, unknown) and either a full
  URL beside it or a numbered key defined with a full URL in the same report. A
  key with no register makes the report unusable, so write the register. Never
  invent versions, prices, dimensions or quotations; say a page was blocked
  rather than guessing.
- Finish with a handoff of at most 900 words: findings table
  (claim | label | source URL | limits), traps, unknowns/blocked, and one next
  bounded check. A coordinator reviews everything; nothing is promoted.
""".strip()


# --------------------------------------------------------------------------- #
# State helpers
# --------------------------------------------------------------------------- #

def _now() -> str:
    return time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime())


def _today() -> str:
    return time.strftime("%Y-%m-%d", time.gmtime())


def _read_json(path: Path, default):
    try:
        return json.loads(path.read_text())
    except FileNotFoundError:
        return default


def _valid_task_id(value) -> bool:
    return isinstance(value, str) and re.fullmatch(r"[A-Za-z0-9][A-Za-z0-9_-]{0,127}", value) is not None


def _write_json(path: Path, data) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    tmp = path.with_suffix(path.suffix + ".tmp")
    tmp.write_text(json.dumps(data, indent=2) + "\n")
    os.replace(tmp, path)


def _activity_write(entry: dict) -> None:
    """Append one JSON line to activity.log. `tail -f` on it is the live view."""
    RUNNER_DIR.mkdir(parents=True, exist_ok=True)
    with (RUNNER_DIR / "activity.log").open("a") as fh:
        fh.write(json.dumps(entry) + "\n")


def ensure_layout() -> None:
    RUNNER_DIR.mkdir(parents=True, exist_ok=True)
    RUNS_DIR.mkdir(parents=True, exist_ok=True)
    if not CONFIG_PATH.exists():
        _write_json(CONFIG_PATH, DEFAULT_CONFIG)
    if not QUEUE_PATH.exists():
        _write_json(QUEUE_PATH, {"version": 1, "tasks": []})
    if not STATE_PATH.exists():
        _write_json(STATE_PATH, {"version": 1, "days": {}, "tasks": {}})


def load_config() -> dict:
    cfg = dict(DEFAULT_CONFIG)
    cfg.update(_read_json(CONFIG_PATH, {}))
    return cfg


def spent_today(state: dict, day: str | None = None) -> float:
    day = day or _today()
    return round(float(state.get("days", {}).get(day, {}).get("cost_usd", 0.0)), 6)


def budget_remaining(state: dict, cfg: dict, day: str | None = None) -> float:
    cap = cfg.get("daily_budget_usd")
    if cap is None:
        return float("inf")
    return round(float(cap) - spent_today(state, day), 6)


def next_pending(queue: dict) -> dict | None:
    for task in queue.get("tasks", []):
        if task.get("status", "pending") == "pending":
            return task
    return None


# --------------------------------------------------------------------------- #
# Run lock
# --------------------------------------------------------------------------- #

def acquire_lock() -> bool:
    """Create an exclusive lock file, reclaiming one whose owner is gone."""
    RUNNER_DIR.mkdir(parents=True, exist_ok=True)
    # Serialize stale-lock reclamation: two reclaimers must not unlink each
    # other's new lock. A permanent guard file is safe even after a crash.
    guard_fd = os.open(RUNNER_DIR / "lock.guard", os.O_CREAT | os.O_RDWR, 0o600)
    try:
        fcntl.flock(guard_fd, fcntl.LOCK_EX)
        for _ in range(2):
            try:
                fd = os.open(LOCK_PATH, os.O_CREAT | os.O_EXCL | os.O_WRONLY, 0o600)
                with os.fdopen(fd, "w") as f:
                    json.dump({"pid": os.getpid(), "started": _now()}, f)
                return True
            except FileExistsError:
                try:
                    owner = json.loads(LOCK_PATH.read_text()).get("pid")
                except (OSError, ValueError, AttributeError):
                    # Another process may still be writing its PID. Never guess.
                    return False
                if type(owner) is not int or owner <= 0:
                    return False
                try:
                    os.kill(owner, 0)
                    return False
                except PermissionError:
                    return False
                except ProcessLookupError:
                    LOCK_PATH.unlink(missing_ok=True)
        return False
    finally:
        os.close(guard_fd)


def release_lock() -> None:
    LOCK_PATH.unlink(missing_ok=True)


# --------------------------------------------------------------------------- #
# Backlog: a deliberately small, deterministic format
# --------------------------------------------------------------------------- #

def _backlog_entries(path: Path) -> list[tuple[int, str, str, str, str]]:
    lines = path.read_text(encoding="utf-8").splitlines()
    starts = [i for i, line in enumerate(lines) if line == BACKLOG_OPEN]
    if len(starts) != 1:
        raise ValueError("expected exactly one backlog block")
    start = starts[0]
    ends = [i for i in range(start + 1, len(lines)) if lines[i] == BACKLOG_CLOSE]
    if not ends:
        raise ValueError("backlog block is not closed")
    entries = []
    for index in range(start + 1, ends[0]):
        line = lines[index]
        if not line:
            continue
        fields = line.split(" | ")
        if (len(fields) != 4 or any(not f or f != f.strip() or "|" in f for f in fields)
                or not _valid_task_id(fields[0]) or fields[1] not in ("ready", "not-ready")
                or len(fields[3]) < 40):
            print(f"skipped backlog line {index + 1}: malformed", file=sys.stderr)
            continue
        entries.append((index + 1, *fields))
    return entries


def _refill_queue(queue: dict, cfg: dict, minimum: int, *, dry_run: bool) -> bool:
    """Append only new ready tasks; caller holds the run lock unless previewing."""
    entries = _backlog_entries(BACKLOG_PATH)
    counts = {}
    for _, task_id, _, _, _ in entries:
        counts[task_id] = counts.get(task_id, 0) + 1
    tasks = queue["tasks"]
    existing = {task["id"] for task in tasks}
    pending = sum(task.get("status", "pending") == "pending" for task in tasks)
    added = 0
    for line, task_id, readiness, title, prompt in entries:
        if counts[task_id] > 1:
            reason = "duplicate backlog id"
        elif task_id in existing:
            reason = "already in queue"
        elif readiness != "ready":
            reason = "not ready"
        elif pending >= minimum:
            reason = "threshold met"
        else:
            tasks.append({"id": task_id, "title": title, "prompt": prompt,
                          "model": None, "agent": None,
                          "timeout_minutes": cfg["default_timeout_minutes"],
                          "status": "pending", "added_utc": _now()})
            existing.add(task_id)
            pending += 1
            added += 1
            print(f"{'would add' if dry_run else 'added'} {task_id}: {title}")
            continue
        print(f"skipped {task_id} (line {line}): {reason}")
    print(f"pending after {'preview' if dry_run else 'refill'}: {pending}; "
          f"{'would add' if dry_run else 'added'} {added} (target {minimum})")
    return bool(added)


def _runner_is_committed() -> bool:
    """Do not let the installed timer execute an unreviewed runner change."""
    try:
        result = subprocess.run(["git", "show", "HEAD:tools/scheduled_runner.py"],
                                cwd=ROOT, stdout=subprocess.PIPE, stderr=subprocess.DEVNULL,
                                check=False)
        return result.returncode == 0 and result.stdout == Path(__file__).read_bytes()
    except OSError:
        return False


# --------------------------------------------------------------------------- #
# Task execution
# --------------------------------------------------------------------------- #

def build_prompt(task: dict) -> str:
    body = task["prompt"].strip()
    return f"{body}\n\n{GUARDRAIL}"


def opencode_available() -> bool:
    return shutil.which("opencode") is not None


def run_task(task: dict, cfg: dict, run_dir: Path) -> dict:
    """Run one task, streaming its event stream to disk as it arrives.

    The stream is written line by line so ``tail -f`` shows the task working,
    not just its result. A watchdog kills the process at the timeout, which is
    the only reason a run stops early.
    """
    import threading

    if not _valid_task_id(task.get("id")):
        raise ValueError("invalid task id")
    if not run_dir.resolve().is_relative_to(RUNS_DIR.resolve()):
        raise ValueError("run directory outside runner state")
    model = task.get("model") or cfg["default_model"]
    agent = task.get("agent") or cfg["default_agent"]
    timeout_s = int(task.get("timeout_minutes", cfg["default_timeout_minutes"]) * 60)
    cmd = ["opencode", "run", "--archived", "--format", "json",
           "--agent", agent, "--model", model, build_prompt(task)]
    started = time.time()
    record = {
        "task": task["id"], "title": task.get("title", ""), "model": model,
        "agent": agent, "started_utc": _now(), "timeout_s": timeout_s,
        "run_dir": str(run_dir),
    }
    events_path = run_dir / f"{task['id']}.events.jsonl"
    stderr_path = run_dir / f"{task['id']}.stderr.txt"
    session = None
    cost = 0.0
    texts: list[str] = []
    timed_out = False
    rc = 1
    err = ""
    with events_path.open("w") as events, stderr_path.open("w") as errfh:
        proc = subprocess.Popen(cmd, cwd=str(ROOT), stdout=subprocess.PIPE,
                                stderr=errfh, text=True, bufsize=1)

        def _kill() -> None:
            nonlocal timed_out
            timed_out = True
            try:
                proc.kill()
            except OSError:
                pass

        watchdog = threading.Timer(timeout_s, _kill)
        watchdog.start()
        try:
            for line in proc.stdout:
                events.write(line)
                events.flush()
                stripped = line.strip()
                if not stripped:
                    continue
                try:
                    event = json.loads(stripped)
                except ValueError:
                    continue
                session = event.get("sessionID") or session
                part = event.get("part") or {}
                if event.get("type") == "step_finish":
                    cost += float(part.get("cost") or 0.0)
                elif event.get("type") == "text" and part.get("text"):
                    texts.append(part["text"])
            rc = proc.wait()
        finally:
            watchdog.cancel()
            if proc.poll() is None:
                proc.kill()
    if timed_out:
        rc = 124
        err = f"timed out after {timeout_s}s"
        with stderr_path.open("a") as fh:
            fh.write(err + "\n")
    record["rc"] = rc
    record["duration_s"] = round(time.time() - started, 1)

    report = "\n\n".join(texts).strip()
    if report:
        (run_dir / f"{task['id']}.report.md").write_text(report + "\n")
    else:
        try:
            err = err or stderr_path.read_text()[-2000:]
        except OSError:
            pass
    record.update({"session": session, "cost_usd": round(cost, 6),
                   "report_chars": len(report),
                   "ok": rc == 0 and bool(report)})
    if rc == 124:
        record["error"] = "timeout"
    elif rc != 0:
        record["error"] = (err or "non-zero exit").strip()[:400]
    _write_json(run_dir / f"{task['id']}.record.json", record)
    return record


# --------------------------------------------------------------------------- #
# Commands
# --------------------------------------------------------------------------- #

def cmd_init(_args) -> int:
    ensure_layout()
    print(f"runner state: {RUNNER_DIR}")
    print(f"config: {CONFIG_PATH}")
    return 0


def cmd_add(args) -> int:
    if not _valid_task_id(args.id):
        print("refusing: invalid task id", file=sys.stderr)
        return 2
    ensure_layout()
    if args.prompt_file:
        prompt = Path(args.prompt_file).read_text()
    elif args.prompt:
        prompt = args.prompt
    else:
        print("refusing: a task needs --prompt or --prompt-file", file=sys.stderr)
        return 2
    if len(prompt.strip()) < 40:
        print("refusing: prompt is too short to be a bounded assignment", file=sys.stderr)
        return 2
    if not acquire_lock():
        print("runner active; task not added", file=sys.stderr)
        return 1
    try:
        queue = _read_json(QUEUE_PATH, {"version": 1, "tasks": []})
        if any(t["id"] == args.id for t in queue["tasks"]):
            print(f"refusing: task id {args.id!r} already exists", file=sys.stderr)
            return 2
        queue["tasks"].append({
            "id": args.id, "title": args.title, "prompt": prompt.strip(),
            "model": args.model, "agent": args.agent,
            "timeout_minutes": args.timeout_minutes,
            "status": "pending", "added_utc": _now(),
        })
        _write_json(QUEUE_PATH, queue)
        print(f"queued {args.id} ({len(queue['tasks'])} tasks)")
        return 0
    finally:
        release_lock()


def cmd_refill(args) -> int:
    if args.min_pending < 0:
        print("refusing: --min-pending must be nonnegative", file=sys.stderr)
        return 2
    if args.dry_run:
        queue = _read_json(QUEUE_PATH, {"version": 1, "tasks": []})
        _refill_queue(queue, load_config(), args.min_pending, dry_run=True)
        return 0
    if not acquire_lock():
        print("runner active; refill skipped", file=sys.stderr)
        return 1
    try:
        ensure_layout()
        queue = _read_json(QUEUE_PATH, {"version": 1, "tasks": []})
        if _refill_queue(queue, load_config(), args.min_pending, dry_run=False):
            _write_json(QUEUE_PATH, queue)
        return 0
    finally:
        release_lock()


def cmd_status(_args) -> int:
    ensure_layout()
    cfg = load_config()
    queue = _read_json(QUEUE_PATH, {"tasks": []})
    state = _read_json(STATE_PATH, {"days": {}, "tasks": {}})
    pending = [t for t in queue.get("tasks", []) if t.get("status", "pending") == "pending"]
    cap = cfg.get("daily_budget_usd")
    cap_text = "no local cap" if cap is None else f"of ${float(cap):.2f}"
    print(f"stop file: {'PRESENT' if STOP_PATH.exists() else 'absent'}")
    print(f"spent today ({_today()}): ${spent_today(state):.4f} {cap_text}")
    print(f"pending tasks: {len(pending)}")
    for task in queue.get("tasks", []):
        print(f"  {task['status']:9} {task['id']:24} {task.get('title', '')}")
    for day in sorted(state.get("days", {}))[-5:]:
        entry = state["days"][day]
        print(f"  day {day}: {entry.get('tasks', 0)} task(s), ${entry.get('cost_usd', 0):.4f}")
    return 0


def cmd_log(args) -> int:
    """Recent activity, newest last: one line per finished task."""
    ensure_layout()
    seen: dict[str, dict] = {}
    for path in RUNS_DIR.glob("*/*.record.json"):
        try:
            rec = json.loads(path.read_text())
        except (OSError, ValueError):
            continue
        key = f"{rec.get('started_utc')}|{rec.get('task')}"
        seen[key] = rec
    ordered = sorted(seen.values(), key=lambda r: r.get("started_utc") or "")[-args.lines:]
    if not ordered:
        print("no runs yet")
        return 0
    for rec in ordered:
        ok = "ok  " if rec.get("ok") else "FAIL"
        print(f"{rec.get('started_utc')}  {ok}  {rec.get('task',''):24} "
              f"${rec.get('cost_usd', 0):.4f}  {rec.get('duration_s', 0):6.1f}s  "
              f"{rec.get('title','')}")
    total = sum(r.get("cost_usd", 0) for r in ordered)
    print(f"{'':20}  total for these {len(ordered)}: ${total:.4f}")
    return 0


def cmd_run(args) -> int:
    ensure_layout()
    if STOP_PATH.exists():
        print("stop file present; nothing to do")
        return 0
    if args.dry_run:
        return _run_locked(args)
    if not acquire_lock():
        print("another runner is active; nothing to do")
        return 0
    try:
        return _run_locked(args)
    finally:
        release_lock()


def _run_locked(args) -> int:
    """Run from a fresh queue snapshot under the lock (except dry-run)."""
    cfg = load_config()
    if STOP_PATH.exists():
        print("stop file present; nothing to do")
        return 0
    queue = _read_json(QUEUE_PATH, {"tasks": []})
    state = _read_json(STATE_PATH, {"version": 1, "days": {}, "tasks": {}})
    task = next_pending(queue)
    if task is not None and not _valid_task_id(task.get("id")):
        print("refusing: invalid task id", file=sys.stderr)
        return 2
    auto_refill = not args.dry_run and _runner_is_committed()
    if task is None and not auto_refill:
        print("queue empty")
        return 0
    remaining = budget_remaining(state, cfg)
    if remaining <= 0:
        print(f"daily budget exhausted (${spent_today(state):.4f} spent); not running")
        return 0
    if auto_refill:
        try:
            added = _refill_queue(queue, cfg, 3, dry_run=False)
        except (OSError, UnicodeError, ValueError) as exc:
            print(f"automatic refill skipped: {exc}", file=sys.stderr)
        else:
            if added:
                _write_json(QUEUE_PATH, queue)
    task = next_pending(queue)
    if task is None:
        print("queue empty")
        return 0
    if not _valid_task_id(task.get("id")):
        print("refusing: invalid task id", file=sys.stderr)
        return 2
    if args.dry_run:
        print(f"would run {task['id']} with {task.get('model') or cfg['default_model']}")
        return 0
    if not opencode_available():
        print("opencode executable not found on PATH", file=sys.stderr)
        return 1
    exit_code = 0
    run_dir = RUNS_DIR / f"{_today()}-{uuid.uuid4().hex[:8]}"
    run_dir.mkdir(parents=True, exist_ok=True)
    _activity_write({"event": "start", "utc": _now(), "task": task["id"],
                     "title": task.get("title", ""), "run_dir": str(run_dir),
                     "model": task.get("model") or cfg["default_model"]})
    record = run_task(task, cfg, run_dir)
    task["status"] = "done" if record["ok"] else "failed"
    task["finished_utc"] = _now()
    task["last_record"] = str(run_dir / f"{task['id']}.record.json")
    _write_json(QUEUE_PATH, queue)
    day = state["days"].setdefault(_today(), {"tasks": 0, "cost_usd": 0.0})
    day["tasks"] += 1
    day["cost_usd"] = round(day["cost_usd"] + record["cost_usd"], 6)
    state["tasks"][task["id"]] = {
        "status": task["status"], "rc": record["rc"],
        "cost_usd": record["cost_usd"], "session": record.get("session"),
        "finished_utc": task["finished_utc"],
    }
    _write_json(STATE_PATH, state)
    _activity_write({
        "event": "finish", "utc": record.get("started_utc"),
        "task": record["task"], "ok": record["ok"],
        "cost_usd": record["cost_usd"],
        "duration_s": record.get("duration_s"),
        "report": str(run_dir / f"{task['id']}.report.md"),
    })
    print(json.dumps({k: record[k] for k in
                      ("task", "ok", "rc", "cost_usd", "duration_s", "session")
                      if k in record}, indent=2))
    cap = cfg.get("daily_budget_usd")
    cap_text = "no local cap" if cap is None else f"of ${float(cap):.2f}"
    print(f"spent today: ${spent_today(state):.4f} {cap_text}")
    if not record["ok"]:
        exit_code = 1
    return exit_code


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    sub = parser.add_subparsers(dest="command", required=True)

    sub.add_parser("init", help="create the runner layout").set_defaults(func=cmd_init)

    add = sub.add_parser("add", help="queue one bounded task")
    add.add_argument("--id", required=True)
    add.add_argument("--title", default="")
    add.add_argument("--prompt", default=None)
    add.add_argument("--prompt-file", default=None)
    add.add_argument("--model", default=None)
    add.add_argument("--agent", default=None)
    add.add_argument("--timeout-minutes", type=int, default=25)
    add.set_defaults(func=cmd_add)

    refill = sub.add_parser("refill", help="queue ready tasks from the research backlog")
    refill.add_argument("--min-pending", type=int, default=3)
    refill.add_argument("--dry-run", action="store_true")
    refill.set_defaults(func=cmd_refill)

    sub.add_parser("status", help="queue, budget and recent history").set_defaults(func=cmd_status)

    log = sub.add_parser("log", help="recent finished tasks, newest last")
    log.add_argument("--lines", type=int, default=10)
    log.set_defaults(func=cmd_log)

    run = sub.add_parser("run", help="run at most one pending task")
    run.add_argument("--once", action="store_true", help="accepted for the timer; one task per call")
    run.add_argument("--dry-run", action="store_true")
    run.set_defaults(func=cmd_run)

    args = parser.parse_args(argv)
    try:
        return args.func(args)
    except (OSError, ValueError, UnicodeError) as exc:
        print(f"runner unavailable ({exc.__class__.__name__})", file=sys.stderr)
        return 1


if __name__ == "__main__":
    sys.exit(main())

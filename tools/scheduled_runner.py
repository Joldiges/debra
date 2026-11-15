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
    python tools/scheduled_runner.py status
    python tools/scheduled_runner.py run --once [--dry-run]
"""

from __future__ import annotations

import argparse
import json
import os
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
- Public documentation and public source code only. Record a URL and the date
  checked for every claim, and label each claim upstream-documented, reported,
  hypothesis or unknown. Never invent versions, prices, dimensions or quotations;
  say a page was blocked rather than guessing.
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


def _write_json(path: Path, data) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    tmp = path.with_suffix(path.suffix + ".tmp")
    tmp.write_text(json.dumps(data, indent=2) + "\n")
    os.replace(tmp, path)


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
    for _ in range(2):
        try:
            fd = os.open(LOCK_PATH, os.O_CREAT | os.O_EXCL | os.O_WRONLY, 0o600)
            with os.fdopen(fd, "w") as f:
                json.dump({"pid": os.getpid(), "started": _now()}, f)
            return True
        except FileExistsError:
            try:
                owner = json.loads(LOCK_PATH.read_text()).get("pid")
            except (OSError, ValueError):
                owner = None
            alive = False
            if isinstance(owner, int):
                try:
                    os.kill(owner, 0)
                    alive = True
                except OSError:
                    alive = False
            if alive:
                return False
            LOCK_PATH.unlink(missing_ok=True)
    return False


def release_lock() -> None:
    LOCK_PATH.unlink(missing_ok=True)


# --------------------------------------------------------------------------- #
# Task execution
# --------------------------------------------------------------------------- #

def build_prompt(task: dict) -> str:
    body = task["prompt"].strip()
    return f"{body}\n\n{GUARDRAIL}"


def opencode_available() -> bool:
    return shutil.which("opencode") is not None


def run_task(task: dict, cfg: dict, run_dir: Path) -> dict:
    """Run one task. Returns a record describing the outcome."""
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
    try:
        proc = subprocess.run(cmd, cwd=str(ROOT), capture_output=True, text=True,
                              timeout=timeout_s)
        rc, out, err = proc.returncode, proc.stdout, proc.stderr
    except subprocess.TimeoutExpired as exc:
        rc = 124
        out = (exc.stdout or b"").decode() if isinstance(exc.stdout, bytes) else (exc.stdout or "")
        err = f"timed out after {timeout_s}s"
    record["rc"] = rc
    record["duration_s"] = round(time.time() - started, 1)
    (run_dir / f"{task['id']}.events.jsonl").write_text(out)
    if err:
        (run_dir / f"{task['id']}.stderr.txt").write_text(err)

    session = None
    cost = 0.0
    texts: list[str] = []
    for line in out.splitlines():
        line = line.strip()
        if not line:
            continue
        try:
            event = json.loads(line)
        except ValueError:
            continue
        session = event.get("sessionID") or session
        part = event.get("part") or {}
        if event.get("type") == "step_finish":
            cost += float(part.get("cost") or 0.0)
        elif event.get("type") == "text" and part.get("text"):
            texts.append(part["text"])
    report = "\n\n".join(texts).strip()
    if report:
        (run_dir / f"{task['id']}.report.md").write_text(report + "\n")
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
    ensure_layout()
    queue = _read_json(QUEUE_PATH, {"version": 1, "tasks": []})
    if any(t["id"] == args.id for t in queue["tasks"]):
        print(f"refusing: task id {args.id!r} already exists", file=sys.stderr)
        return 2
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
    queue["tasks"].append({
        "id": args.id, "title": args.title, "prompt": prompt.strip(),
        "model": args.model, "agent": args.agent,
        "timeout_minutes": args.timeout_minutes,
        "status": "pending", "added_utc": _now(),
    })
    _write_json(QUEUE_PATH, queue)
    print(f"queued {args.id} ({len(queue['tasks'])} tasks)")
    return 0


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
    cfg = load_config()
    if STOP_PATH.exists():
        print("stop file present; nothing to do")
        return 0
    queue = _read_json(QUEUE_PATH, {"tasks": []})
    state = _read_json(STATE_PATH, {"version": 1, "days": {}, "tasks": {}})
    task = next_pending(queue)
    if task is None:
        print("queue empty")
        return 0
    remaining = budget_remaining(state, cfg)
    if remaining <= 0:
        print(f"daily budget exhausted (${spent_today(state):.4f} spent); not running")
        return 0
    if args.dry_run:
        print(f"would run {task['id']} with {task.get('model') or cfg['default_model']}")
        return 0
    if not opencode_available():
        print("opencode executable not found on PATH", file=sys.stderr)
        return 1
    if not acquire_lock():
        print("another runner is active; nothing to do")
        return 0
    exit_code = 0
    try:
        run_dir = RUNS_DIR / f"{_today()}-{uuid.uuid4().hex[:8]}"
        run_dir.mkdir(parents=True, exist_ok=True)
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
        activity = RUNNER_DIR / "activity.log"
        with activity.open("a") as fh:
            fh.write(json.dumps({
                "utc": record.get("started_utc"), "task": record["task"],
                "ok": record["ok"], "cost_usd": record["cost_usd"],
                "duration_s": record.get("duration_s"),
                "report": str(run_dir / f"{task['id']}.report.md"),
            }) + "\n")
        print(json.dumps({k: record[k] for k in
                          ("task", "ok", "rc", "cost_usd", "duration_s", "session")
                          if k in record}, indent=2))
        cap = cfg.get("daily_budget_usd")
        cap_text = "no local cap" if cap is None else f"of ${float(cap):.2f}"
        print(f"spent today: ${spent_today(state):.4f} {cap_text}")
        if not record["ok"]:
            exit_code = 1
    finally:
        release_lock()
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

    sub.add_parser("status", help="queue, budget and recent history").set_defaults(func=cmd_status)

    log = sub.add_parser("log", help="recent finished tasks, newest last")
    log.add_argument("--lines", type=int, default=10)
    log.set_defaults(func=cmd_log)

    run = sub.add_parser("run", help="run at most one pending task")
    run.add_argument("--once", action="store_true", help="accepted for the timer; one task per call")
    run.add_argument("--dry-run", action="store_true")
    run.set_defaults(func=cmd_run)

    args = parser.parse_args(argv)
    return args.func(args)


if __name__ == "__main__":
    sys.exit(main())

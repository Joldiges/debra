"""One read-only snapshot of what is running right now.

    python tools/activity.py             # print once
    python tools/activity.py --watch 5   # refresh every 5 seconds

It reads the research runner's own state, the local OpenCode session list, and
whether the development web server is listening, then prints a Markdown
snapshot and rewrites ``.local/status/activity.md`` so an editor that reloads
files can show it live. It starts nothing, stops nothing, writes nothing
outside ``.local/status``, and never calls a model.

OpenCode sessions need the background service; when it is unreachable that
section says so instead of guessing. Dispatch claims are not shown: dispatch is
closed, so there is nothing to claim.
"""

from __future__ import annotations

import argparse
import calendar
import json
import math
import os
import socket
import subprocess
import sys
import time
from pathlib import Path

SOURCE = Path(__file__).resolve().parent.parent
if __name__ == "__main__":
    sys.dont_write_bytecode = True
if str(SOURCE) not in sys.path:
    sys.path.insert(0, str(SOURCE))

import tools.scheduled_runner as runner  # noqa: E402  (path set above)

STATUS_DIR = SOURCE / ".local" / "status"
OPENCODE_TIMEOUT_S = 15
# Explicit endpoint only: never ask the CLI to discover or start a service.
OPENCODE_MAX_BYTES = 2 * 1024 * 1024


def _local(utc_stamp: str) -> str:
    """Render an ISO UTC stamp from the runner log in local time."""
    try:
        parsed = time.strptime(utc_stamp, "%Y-%m-%dT%H:%M:%SZ")
    except (TypeError, ValueError):
        return utc_stamp or "unknown"
    return time.strftime("%Y-%m-%d %H:%M:%S", time.localtime(calendar.timegm(parsed)))


def _lock_owner() -> dict | None:
    """Return the live lock holder, or None when no run holds the lock."""
    path = runner.RUNNER_DIR / "run.lock"
    try:
        holder = json.loads(path.read_text())
    except FileNotFoundError:
        return None
    if not isinstance(holder, dict):
        raise ValueError("invalid lock record")
    pid = holder.get("pid")
    if type(pid) is not int or pid <= 0:
        raise ValueError("invalid lock pid")
    try:
        os.kill(pid, 0)
    except ProcessLookupError:
        return None
    except PermissionError:
        pass
    return holder


def _last_event() -> dict | None:
    """The newest activity.log entry, which is the current or last task."""
    path = runner.RUNNER_DIR / "activity.log"
    try:
        lines = path.read_text().splitlines()
    except FileNotFoundError:
        return None
    for line in reversed(lines):
        entry = json.loads(line)
        if isinstance(entry, dict):
            return entry
    return None


def runner_snapshot() -> dict:
    state = runner._read_json(runner.STATE_PATH, {"days": {}, "tasks": {}})
    queue = runner._read_json(runner.QUEUE_PATH, {"tasks": []})
    cfg = runner.load_config()
    holder = _lock_owner()
    last = _last_event()
    running = None
    if holder:
        event = last if last and last.get("event") == "start" else {}
        started = event.get("utc", holder.get("started", ""))
        running = {
            "task": event.get("task", "unknown"),
            "title": event.get("title", ""),
            "model": event.get("model", "unknown"),
            "since": started,
            "elapsed_s": _seconds_since(started),
        }
    pending = [t.get("id") for t in queue.get("tasks", [])
               if t.get("status", "pending") == "pending"]
    done_today = sum(1 for t in queue.get("tasks", [])
                     if t.get("status") == "done")
    recent = []
    for task_id, info in list(state.get("tasks", {}).items())[-5:]:
        recent.append({"task": task_id, "status": info.get("status", "unknown"),
                       "cost": info.get("cost_usd", 0.0),
                       "finished": info.get("finished_utc", "")})
    return {
        "running": running,
        "pending": pending,
        "done": done_today,
        "total": len(queue.get("tasks", [])),
        "spent_today": runner.spent_today(state),
        "cap": cfg.get("daily_budget_usd"),
        "stop_file": (runner.RUNNER_DIR / "STOP").exists(),
        "recent": recent,
    }


def _seconds_since(utc_stamp: str) -> int | None:
    try:
        started = calendar.timegm(time.strptime(utc_stamp, "%Y-%m-%dT%H:%M:%SZ"))
    except (TypeError, ValueError):
        return None
    return max(0, int(time.time() - started))


def _ago(stamp) -> str:
    """Render a session timestamp as a rough age. Accepts seconds or milliseconds."""
    try:
        value = float(stamp)
    except (TypeError, ValueError):
        return "unknown"
    if not value:
        return "unknown"
    seconds = time.time() - (value / 1000 if value > 10**11 else value)
    seconds = max(0.0, seconds)
    if seconds < 90:
        return f"{int(seconds)}s ago"
    if seconds < 5400:
        return f"{int(seconds / 60)}m ago"
    if seconds < 172800:
        return f"{seconds / 3600:.1f}h ago"
    return f"{seconds / 86400:.1f}d ago"


def _session_rows(payload) -> list[dict]:
    if not isinstance(payload, dict) or not isinstance(payload.get("data"), list):
        raise ValueError("invalid session list")
    rows = []
    for item in payload["data"]:
        if not isinstance(item, dict):
            raise ValueError("invalid session record")
        times = item.get("time") if item.get("time") is not None else {}
        model = item.get("model") if item.get("model") is not None else {}
        if not isinstance(times, dict) or not isinstance(model, dict):
            raise ValueError("invalid session details")
        for obj, keys in ((item, ("id", "title", "agent", "parentID")),
                          (model, ("providerID", "id", "variant"))):
            for key in keys:
                if obj.get(key) is not None and not isinstance(obj[key], str):
                    raise ValueError("invalid session text")
        for obj, keys in ((item, ("cost",)), (times, ("busy", "idle", "updated", "created"))):
            for key in keys:
                value = obj.get(key)
                if value is not None and (type(value) not in (int, float) or
                        not 0 <= value <= 10**20 or not math.isfinite(value)):
                    raise ValueError("invalid session number")
        busy, idle = times.get("busy"), times.get("idle")
        # `busy` and `idle` are the timestamps of the last turn start and end.
        # A turn that has started and not ended is working; a session that has
        # never had a turn has neither and stays unknown.
        if busy is None and idle is None:
            working = None
        elif idle is None:
            working = True
        elif busy is None:
            working = False
        else:
            working = busy > idle
        rows.append({
            "id": item.get("id") or "",
            "title": item.get("title") or "(untitled)",
            "agent": item.get("agent") or "",
            "model": "/".join(filter(None, [model.get("providerID"), model.get("id")]))
                     + (f"#{model['variant']}" if model.get("variant") else ""),
            "child": bool(item.get("parentID")),
            "working": working,
            "cost": item.get("cost") or 0.0,
            "updated": times.get("updated") or times.get("created") or 0,
        })
    rows.sort(key=lambda row: row["updated"], reverse=True)
    return rows


def sessions_snapshot() -> dict:
    try:
        return _sessions_snapshot()
    except OSError as exc:
        # Closing a failed connection can itself fail.
        return {"error": f"opencode unavailable ({exc.__class__.__name__})", "sessions": []}


def _sessions_snapshot() -> dict:
    # `opencode api` talks to the running background service by itself; the CLI
    # is the supported way to find its port, which changes on every start. Any
    # environment override that could redirect it is removed, and no --server
    # argument is ever passed.
    env = {name: value for name, value in os.environ.items()
           if not name.upper().startswith(("OPENCODE_SERVER", "OPENCODE_API"))}
    try:
        proc = subprocess.run(["opencode", "api", "get", "/api/session"],
                              capture_output=True, timeout=OPENCODE_TIMEOUT_S,
                              env=env, check=False)
    except (OSError, subprocess.TimeoutExpired) as exc:
        return {"error": f"opencode unavailable ({exc.__class__.__name__})", "sessions": []}
    if proc.returncode != 0:
        return {"error": f"opencode unavailable (exit {proc.returncode})", "sessions": []}
    if len(proc.stdout) > OPENCODE_MAX_BYTES:
        return {"error": "opencode unavailable (session list too large)", "sessions": []}
    try:
        rows = _session_rows(json.loads(proc.stdout))
    except (ValueError, UnicodeError):
        return {"error": "opencode unavailable (unreadable session list)", "sessions": []}
    return {"error": None, "sessions": rows}


def web_snapshot(port: int) -> dict:
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as sock:
        sock.settimeout(1.0)
        listening = sock.connect_ex(("127.0.0.1", port)) == 0
    return {"port": port, "listening": listening}


def render(port: int) -> str:
    now = time.strftime("%Y-%m-%d %H:%M:%S")
    try:
        run = runner_snapshot()
    except (OSError, ValueError, TypeError, AttributeError, KeyError, UnicodeError) as exc:
        run = {"error": f"unavailable ({exc.__class__.__name__})"}
    agents = sessions_snapshot()
    try:
        web = web_snapshot(port)
    except OSError as exc:
        web = {"error": f"unavailable ({exc.__class__.__name__})"}
    out = [f"# What is running — {now}", ""]

    out.append("## Research runner")
    if run.get("error"):
        out.append(f"- Research runner {run['error']}")
    elif run["running"]:
        r = run["running"]
        elapsed = f"{r['elapsed_s'] // 60}m {r['elapsed_s'] % 60}s" if r["elapsed_s"] is not None else "unknown"
        out.append(f"- **Running now:** `{r['task']}` — {r['title']}")
        out.append(f"- Started {_local(r['since'])} local ({elapsed} ago) · model `{r['model']}`")
    elif run["stop_file"]:
        out.append("- **Stopped by STOP file**; nothing will start until it is removed.")
    else:
        out.append("- **Idle** — no task is running at this moment.")
    if not run.get("error"):
        out.append(f"- Queue: {len(run['pending'])} pending, {run['done']} done of {run['total']}")
        if run["pending"]:
            out.append(f"- Next: `{run['pending'][0]}`")
        cap = run["cap"]
        spend = f"- Spent today: **${run['spent_today']:.4f}**"
        out.append(spend + (f" of ${float(cap):.2f} cap" if cap is not None else " (no local cap)"))
        if run["recent"]:
            out.append("- Recent: " + ", ".join(
                f"`{r['task']}` {r['status']} ${r['cost']:.4f}" for r in run["recent"]))
    out.append("")

    out.append("## Agent sessions")
    if agents["error"]:
        out.append(f"- {agents['error']}")
    else:
        working = [s for s in agents["sessions"] if s["working"]]
        idle = len(agents["sessions"]) - len(working)
        out.append(f"- {len(working)} working · {idle} idle · {len(agents['sessions'])} known sessions")
        for s in agents["sessions"][:8]:
            state = "**working**" if s["working"] is True else "idle" if s["working"] is False else "unknown"
            kind = "subagent" if s["child"] else "session"
            out.append(f"- {state} · {kind} · {s['title']} · `{s['model']}` · ${s['cost']:.4f}"
                       f" · updated {_ago(s['updated'])}")
        out.append("- A point-in-time snapshot: a session between turns shows idle, which is not the")
        out.append("  same as abandoned. Run with `--watch 5` for a live view.")
    out.append("")

    out.append("## Development web server")
    if web.get("error"):
        out.append(f"- Development web server {web['error']}")
    elif web["listening"]:
        out.append(f"- Listening on http://127.0.0.1:{web['port']}/")
    else:
        out.append(f"- Not listening on port {web['port']}")
    out.append("")
    return "\n".join(out)


def write(markdown: str) -> Path:
    STATUS_DIR.mkdir(parents=True, exist_ok=True)
    target = STATUS_DIR / "activity.md"
    tmp = target.with_suffix(".md.tmp")
    tmp.write_text(markdown + "\n")
    os.replace(tmp, target)
    return target


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("--watch", type=float, metavar="SECONDS",
                        help="refresh continuously instead of printing once")
    parser.add_argument("--port", type=int, default=8787,
                        help="development web server port to probe")
    args = parser.parse_args(argv)
    while True:
        text = render(args.port)
        try:
            target = write(text)
        except OSError as exc:
            print(text)
            print(f"status file unavailable ({exc.__class__.__name__})", file=sys.stderr)
            return 1
        if args.watch:
            print("\033[2J\033[H" + text, flush=True)
            print(f"(written to {target}; refresh every {args.watch:g}s; Ctrl+C to stop)")
            time.sleep(max(1.0, args.watch))
        else:
            print(text)
            print(f"(written to {target})")
            return 0


if __name__ == "__main__":
    try:
        sys.exit(main())
    except KeyboardInterrupt:
        sys.exit(130)

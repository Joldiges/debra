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
import re
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

GREEN = "\033[1;32m"
YELLOW = "\033[33m"
RED = "\033[31m"
DIM = "\033[2m"
COST_CELL = re.compile(r"^\$(\d+(?:\.\d+)?)$")
AGE_CELL = re.compile(r"^(\d+(?:\.\d+)?)([smhd])$")
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


def _age(stamp) -> str:
    """Render a session timestamp as a compact age for a table cell."""
    try:
        value = float(stamp)
    except (TypeError, ValueError):
        return "unknown"
    if not value:
        return "unknown"
    seconds = time.time() - (value / 1000 if value > 10**11 else value)
    seconds = max(0.0, seconds)
    if seconds < 90:
        return f"{int(seconds)}s"
    if seconds < 5400:
        return f"{int(seconds / 60)}m"
    if seconds < 172800:
        return f"{seconds / 3600:.1f}h"
    return f"{seconds / 86400:.1f}d"


def _ago(stamp) -> str:
    """Render a session timestamp as a rough age in prose."""
    age = _age(stamp)
    return "unknown" if age == "unknown" else f"{age} ago"


def _table(headers: list[str], rows: list[list[str]], caps: dict[int, int] | None = None) -> list[str]:
    """A padded Markdown table. Long cells are truncated to a per-column cap."""
    caps = caps or {}
    widths = []
    for index, header in enumerate(headers):
        cells = [header] + [row[index] for row in rows]
        widths.append(min(max(len(cell) for cell in cells), caps.get(index, 200)))

    def line(cells: list[str]) -> str:
        padded = []
        for cell, width in zip(cells, widths):
            if len(cell) > width:
                cell = cell[: max(1, width - 1)] + "…"
            padded.append(cell.ljust(width))
        return "| " + " | ".join(padded) + " |"

    out = [line(headers), "| " + " | ".join("-" * width for width in widths) + " |"]
    out.extend(line(row) for row in rows)
    return out


def _model_label(session: dict) -> str:
    """The model and variant, without a provider prefix that adds no information.

    Almost every session here runs through one provider, so printing
    ``openrouter/`` on every row only pushes the variant off the end of the
    column. A different provider is kept, because then it does distinguish.
    """
    label = session["model_id"] or "unknown"
    if session["variant"]:
        label += f"#{session['variant']}"
    provider = session["provider"]
    if provider and provider != "openrouter":
        label = f"{provider}/{label}"
    return label


def _session_table(sessions: list[dict]) -> list[str]:
    rows = []
    for session in sessions:
        state = ("working" if session["working"] is True
                 else "idle" if session["working"] is False else "unknown")
        rows.append([
            state,
            "sub" if session["child"] else "main",
            session["title"],
            _model_label(session),
            f"${session['cost']:.4f}",
            _age(session["updated"]),
        ])
    return _table(["State", "Kind", "Title", "Model", "Cost", "Age"], rows,
                  caps={2: 38, 3: 42})


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
        tokens = item.get("tokens") if isinstance(item.get("tokens"), dict) else {}
        cache = tokens.get("cache") if isinstance(tokens.get("cache"), dict) else {}

        def token_count(source: dict, key: str) -> float:
            value = source.get(key)
            if type(value) not in (int, float) or not math.isfinite(value) or value < 0:
                return 0.0
            return float(value)

        total_tokens = sum(token_count(tokens, key)
                           for key in ("input", "output", "reasoning"))
        total_tokens += sum(token_count(cache, key) for key in ("read", "write"))
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
            "provider": model.get("providerID") or "",
            "model_id": model.get("id") or "",
            "variant": model.get("variant") or "",
            "child": bool(item.get("parentID")),
            "working": working,
            "cost": item.get("cost") or 0.0,
            "created": times.get("created") or 0,
            "tokens": total_tokens,
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


def _paint(markdown: str, rates: dict[str, float] | None = None) -> str:
    """Colour a snapshot for a terminal. The file on disk stays plain Markdown.

    Colour carries state, not decoration: a working session is green, an idle one
    is dim (so the eye skips it), an unknown one is amber, a failure is red.
    Cost and age use the same direction: cheap and fresh are green, expensive
    and stale are red. The model cell is coloured by the model's blended rate
    across the sessions shown, so a cheaper model reads greener than a dear one.
    Table cells are painted after padding, so the columns still line up.
    """
    palette = {
        "working": GREEN,
        "idle": DIM,
        "unknown": YELLOW,
    }
    ordered = sorted(rates, key=lambda key: rates[key]) if rates else []

    def model_colour(label: str) -> str:
        # Absolute bands, not rank: one outlier model must not push a cheap one
        # into the amber band just because it is the fourth cheapest.
        if not ordered or label not in ordered:
            return ""
        rate = rates[label]
        return GREEN if rate < 0.05 else YELLOW if rate < 0.20 else RED

    def cell_colour(word: str) -> str:
        match = COST_CELL.match(word)
        if match:
            value = float(match.group(1))
            return GREEN if value < 0.10 else YELLOW if value < 0.50 else RED
        match = AGE_CELL.match(word)
        if match:
            seconds = float(match.group(1)) * {"s": 1, "m": 60, "h": 3600, "d": 86400}[match.group(2)]
            return GREEN if seconds < 120 else YELLOW if seconds < 1200 else RED
        if word in palette:
            return palette[word]
        return model_colour(word)

    lines = markdown.splitlines()
    out = []
    for index, line in enumerate(lines):
        following = lines[index + 1] if index + 1 < len(lines) else ""
        if line.startswith("|") and "---" not in line:
            cells = line.split("|")
            header = following.startswith("|") and "---" in following
            for cell_index, cell in enumerate(cells):
                word = cell.strip()
                if header and word:
                    cells[cell_index] = f"\033[1m{cell}\033[0m"
                    continue
                colour = cell_colour(word)
                if colour:
                    cells[cell_index] = f"{colour}{cell}\033[0m"
            out.append("|".join(cells))
        elif line.startswith("#"):
            out.append(f"\033[1m{line}\033[0m")
        elif line.startswith("- **Running now:**"):
            out.append(f"{GREEN}{line}\033[0m")
        elif "unavailable" in line:
            out.append(f"{RED}{line}\033[0m")
        else:
            out.append(line)
    return "\n".join(out)


def session_rates(sessions: list[dict]) -> dict[str, float]:
    """Blended cost per million tokens for each model label.

    This is the honest way to compare models without a price list: it uses the
    cost and token counts the session API already reports. It is a blend across
    input, output, reasoning and cache, so it is not a list price.
    """
    cost: dict[str, float] = {}
    tokens: dict[str, float] = {}
    for session in sessions:
        label = _model_label(session)
        if not session.get("tokens") or session["cost"] <= 0:
            continue
        cost[label] = cost.get(label, 0.0) + session["cost"]
        tokens[label] = tokens.get(label, 0.0) + session["tokens"]
    return {label: cost[label] / (tokens[label] / 1e6)
            for label in tokens if tokens[label] > 0}


def render(port: int, limit: int = 24, meta: dict | None = None) -> str:
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
            out.append("")
            out.extend(_table(
                ["Recent task", "Status", "Cost"],
                [[f"`{r['task']}`", r["status"], f"${r['cost']:.4f}"] for r in run["recent"]],
                caps={0: 34}))
    out.append("")

    out.append("## Agent sessions")
    if agents["error"]:
        out.append(f"- {agents['error']}")
    else:
        sessions = agents["sessions"]
        working = [s for s in sessions if s["working"] is True]
        idle = [s for s in sessions if s["working"] is False]
        unknown = [s for s in sessions if s["working"] is None]
        # Working sessions are ordered by when they were created, which never
        # changes, so the table does not reshuffle on every refresh. The recent
        # list is ordered by last activity, which only moves when a session
        # actually finishes a turn.
        working.sort(key=lambda s: s["created"], reverse=True)
        recent = sorted(idle + unknown, key=lambda s: s["updated"], reverse=True)
        total = sum(s["cost"] for s in sessions)
        shown = working + recent[: max(0, limit - len(working))]
        out.append(f"- {len(working)} working · {len(idle)} idle · {len(unknown)} unknown"
                   f" · {len(sessions)} known sessions")
        out.append(f"- Session cost: **${total:.4f}** in total, ${sum(s['cost'] for s in shown):.4f}"
                   f" across the {len(shown)} rows below")
        out.append("")
        if working:
            out.append(f"### Working now ({len(working)})")
            out.extend(_session_table(working))
        else:
            out.append("### Working now (0)")
            out.append("Nothing is working right now; the rows below are sessions between turns.")
        hidden = len(recent) - len(recent[: max(0, limit - len(working))])
        if recent:
            out.append("")
            out.append(f"### Recently active ({min(len(recent), max(0, limit - len(working)))} of {len(recent)}"
                       + (f", {hidden} hidden — `--all` to show every session" if hidden else "") + ")")
            out.extend(_session_table(recent[: max(0, limit - len(working))]))
        out.append("")
        out.append("- `working` is a turn in progress. `idle` is between turns, which is not the")
        out.append("  same as abandoned. `unknown` is a session that has not run a turn yet.")
        out.append("- Rows are ordered by creation (working) and last activity (recent), so the")
        out.append("  table stays put instead of reshuffling on every refresh.")
        rates = session_rates(sessions)
        if meta is not None:
            meta["rates"] = rates
        if rates:
            cheapest = sorted(rates, key=lambda label: rates[label])
            out.append("- Model rate, blended cost per million tokens, cheapest first: "
                       + " · ".join(f"`{label}` ${rates[label]:.2f}" for label in cheapest))
            out.append("  A blend, not a list price: it mixes input, output, reasoning and cache.")
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
    parser.add_argument("--limit", type=int, default=24, metavar="N",
                        help="most session rows to show; working sessions always all show")
    parser.add_argument("--all", action="store_true",
                        help="show every known session, ignoring --limit")
    parser.add_argument("--no-color", action="store_true",
                        help="never colour terminal output (NO_COLOR is also honoured)")
    args = parser.parse_args(argv)
    limit = 10**6 if args.all else max(0, args.limit)
    # Colour is for a terminal only: the status file stays plain Markdown, and a
    # redirected or captured run must not gain escape sequences.
    paint = (sys.stdout.isatty() and not args.no_color
             and not os.environ.get("NO_COLOR"))
    while True:
        meta: dict = {}
        text = render(args.port, limit, meta)
        try:
            target = write(text)
        except OSError as exc:
            print(_paint(text, meta.get("rates")) if paint else text)
            print(f"status file unavailable ({exc.__class__.__name__})", file=sys.stderr)
            return 1
        display = _paint(text, meta.get("rates")) if paint else text
        if args.watch:
            print("\033[2J\033[H" + display, flush=True)
            print(f"(written to {target}; refreshing every {args.watch:g}s; Ctrl+C to stop"
                  + ("; --all for every session)" if not args.all else ")"))
            time.sleep(max(1.0, args.watch))
        else:
            print(display)
            print(f"(written to {target})")
            return 0


if __name__ == "__main__":
    try:
        sys.exit(main())
    except KeyboardInterrupt:
        sys.exit(130)

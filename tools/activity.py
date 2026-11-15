"""One read-only snapshot of what is running right now.

    python tools/activity.py             # print once
    python tools/activity.py --watch 5   # refresh every 5 seconds
    python tools/activity.py --tui       # interactive terminal view

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
import curses
import json
import math
import os
import queue
import re
import socket
import subprocess
import sys
import threading
import time
import unicodedata
from pathlib import Path

SOURCE = Path(__file__).resolve().parent.parent
if __name__ == "__main__":
    sys.dont_write_bytecode = True
if str(SOURCE) not in sys.path:
    sys.path.insert(0, str(SOURCE))

import tools.scheduled_runner as runner  # noqa: E402  (path set above)

STATUS_DIR = SOURCE / ".local" / "status"

GREEN = "\033[1;32m"
ORANGE = "\033[38;5;208m"
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


def _span(seconds: float) -> str:
    """Render a duration in seconds as a compact table cell."""
    seconds = max(0.0, seconds)
    if seconds < 90:
        return f"{int(seconds)}s"
    if seconds < 5400:
        return f"{int(seconds / 60)}m"
    if seconds < 172800:
        return f"{seconds / 3600:.1f}h"
    return f"{seconds / 86400:.1f}d"


def _seconds_ago(stamp, now: float | None = None) -> float | None:
    """Seconds between a session timestamp and ``now``, or None if unusable.

    The service reports either seconds or milliseconds depending on version, so
    both are accepted. ``now`` is a parameter rather than a read of the clock so
    a caller that has already fixed a time cannot mix two clocks in one cell.
    """
    try:
        value = float(stamp)
    except (TypeError, ValueError):
        return None
    if not value:
        return None
    now = time.time() if now is None else now
    return max(0.0, now - (value / 1000 if value > 10**11 else value))


def _age(stamp, now: float | None = None) -> str:
    """Render a session timestamp as a compact age for a table cell."""
    seconds = _seconds_ago(stamp, now)
    return "unknown" if seconds is None else _span(seconds)


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


def _why(session: dict, by_id: dict, now: float) -> str:
    """Why this session is (or is not) running, from what the service reports.

    This is inference from timestamps and parentage, not a claim about what the
    agent is doing: the session list carries no message or tool data. So the
    words stay at what is provable - a turn ended, a parent is still busy, a
    turn has been open a long time - and never guess at a pending question.
    """
    if session.get("working") is None:
        return "never started"
    if session.get("working"):
        busy = session.get("busy_at")
        elapsed = _seconds_ago(busy, now)
        if elapsed is None:
            return "running"
        # A turn still open after five minutes is worth naming: it is either a
        # long build or a session that has stopped without saying so.
        return (f"running {_span(elapsed)}" if elapsed < 300
                else f"long turn {_span(elapsed)}")
    parent_id = session.get("parent") or ""
    if session.get("child"):
        parent = by_id.get(parent_id)
        if parent is None:
            # Only reachable when the parent is not in the session list at all:
            # a hidden parent is passed in, so this means deleted, not finished.
            return "parent deleted"
        if parent.get("working"):
            return "finished; parent busy"
        return "finished"
    ended = _seconds_ago(session.get("idle_at"), now)
    if ended is not None and ended < 90:
        return "just finished"
    return "waiting for you"


def _session_table(sessions: list[dict], by_id: dict | None = None,
                   now: float | None = None) -> list[str]:
    now = time.time() if now is None else now
    by_id = {row["id"]: row for row in sessions} if by_id is None else by_id
    rows = [_session_cells(session, by_id, now) for session in sessions]
    return _table(["State", "Kind", "Title", "Model", "Cost", "Age", "Why"], rows,
                  caps={2: 34, 3: 30, 6: 20})


def _session_cells(session: dict, by_id: dict, now: float) -> list[str]:
    state = ("working" if session["working"] is True
             else "idle" if session["working"] is False else "unknown")
    return [state, "sub" if session["child"] else "main", session["title"],
            _model_label(session), f"${session['cost']:.4f}",
            _age(session["updated"], now), _why(session, by_id, now)]


def _ordered_sessions(sessions: list[dict], limit: int) -> tuple[list[dict], list[dict]]:
    working = sorted((s for s in sessions if s["working"] is True),
                     key=lambda s: s["created"], reverse=True)
    idle = [s for s in sessions if s["working"] is False]
    unknown = [s for s in sessions if s["working"] is None]
    recent = sorted(idle + unknown, key=lambda s: s["updated"], reverse=True)
    return working, recent[:max(0, limit - len(working))]


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
            "parent": item.get("parentID") or "",
            "busy_at": busy,
            "idle_at": idle,
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
    across the sessions shown, so a cheaper model reads greener than a dear one,
    with yellow and orange separating the two middle tiers.
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
        # into a warmer band just because it is the fourth cheapest. Four bands,
        # because a three-band scale put terra (~$0.08/Mtok) and sol (~$0.17) in
        # the same yellow and hid the fact that sol costs about twice as much.
        if not ordered or label not in ordered:
            return ""
        rate = rates[label]
        if rate < 0.05:
            return GREEN
        if rate < 0.12:
            return YELLOW
        return ORANGE if rate < 0.30 else RED

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
    if meta is not None:
        meta.update(agents=agents, refreshed=now)
    out = [f"# What is running — {now}", ""]

    out.append("## Research runner")
    if run.get("error"):
        out.append(f"- Research runner {run['error']}")
    elif run["running"]:
        r = run["running"]
        elapsed = ("start time not readable" if r["elapsed_s"] is None
                   else f"started {r['elapsed_s'] // 60}m {r['elapsed_s'] % 60}s ago")
        title = f" — {r['title']}" if r["title"] else ""
        out.append(f"- **Running now:** `{r['task']}`{title}")
        out.append(f"- {elapsed} ({_local(r['since'])} local) · model `{r['model']}`")
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
        working, shown_recent = _ordered_sessions(sessions, limit)
        recent = sorted(idle + unknown, key=lambda s: s["updated"], reverse=True)
        # A parent is resolved against every known session, not the rows on
        # display: a parent hidden by --limit is still a parent that exists.
        now = time.time()
        by_id = {s["id"]: s for s in sessions}
        total = sum(s["cost"] for s in sessions)
        shown = working + shown_recent
        out.append(f"- {len(working)} working · {len(idle)} idle · {len(unknown)} unknown"
                   f" · {len(sessions)} known sessions")
        out.append(f"- Session cost: **${total:.4f}** in total, ${sum(s['cost'] for s in shown):.4f}"
                   f" across the {len(shown)} rows below")
        out.append("")
        if working:
            out.append(f"### Working now ({len(working)})")
            out.extend(_session_table(working, by_id=by_id, now=now))
        else:
            out.append("### Working now (0)")
            out.append("Nothing is working right now; the rows below are sessions between turns.")
        hidden = len(recent) - len(shown_recent)
        if recent:
            out.append("")
            out.append(f"### Recently active ({min(len(recent), max(0, limit - len(working)))} of {len(recent)}"
                       + (f", {hidden} hidden — `--all` to show every session" if hidden else "") + ")")
            out.extend(_session_table(shown_recent,
                                      by_id=by_id, now=now))
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
            out.append("  Colour bands on that rate: green under $0.05, yellow under $0.12,")
            out.append("  orange under $0.30, red at or above it.")
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


TUI_HEADERS = ["State", "Kind", "Title", "Model", "Cost", "Age", "Why"]
TUI_MIN_WIDTHS = [7, 4, 5, 5, 6, 3, 5]
TUI_MAX_WIDTHS = [7, 4, 34, 30, 12, 8, 20]
TUI_SEPARATOR = " | "


def _tui_widths(columns: int) -> list[int] | None:
    """Fit all seven columns, or return None if even their minima will not fit."""
    widths = TUI_MIN_WIDTHS.copy()
    remaining = columns - sum(widths) - len(TUI_SEPARATOR) * (len(widths) - 1)
    if remaining < 0:
        return None
    # Share additional space between the variable columns rather than letting a
    # long title push the model or explanation entirely off-screen.
    while remaining:
        grew = False
        for index in (2, 3, 6, 4, 5):
            if remaining and widths[index] < TUI_MAX_WIDTHS[index]:
                widths[index] += 1
                remaining -= 1
                grew = True
        if not grew:
            break
    return widths


def _tui_too_small(lines: int, columns: int) -> bool:
    return lines < 4 or _tui_widths(columns) is None


def _cell_width(char: str) -> int:
    if unicodedata.combining(char):
        return 0
    return 2 if unicodedata.east_asian_width(char) in ("W", "F") else 1


def _tui_fit(text: str, width: int) -> str:
    """Pad/truncate to terminal cells; never let a control character wrap a row."""
    text = "".join(" " if unicodedata.category(char).startswith("C") else char
                   for char in text)
    length = sum(_cell_width(char) for char in text)
    if length > width:
        if width <= 0:
            return ""
        chars, used = [], 0
        for char in text:
            size = _cell_width(char)
            if used + size > width - 1:
                break
            chars.append(char)
            used += size
        text = "".join(chars) + "…"
        length = used + 1
    return text + " " * max(0, width - length)


def _tui_text_window(text: str, width: int, offset: int) -> str:
    """Scroll supporting text horizontally; session table columns stay fixed."""
    text = "".join(" " if unicodedata.category(char).startswith("C") else char
                   for char in text)
    skipped = 0
    index = 0
    while index < len(text) and skipped < offset:
        skipped += _cell_width(text[index])
        index += 1
    if offset:
        return "…" + _tui_fit(text[index:], max(0, width - 1)) if width else ""
    return _tui_fit(text, width)


def _rate_band(rate: float | None) -> int:
    """Curses pair number for the existing absolute model-rate bands."""
    if rate is None:
        return 0
    return 1 if rate < 0.05 else 2 if rate < 0.12 else 3 if rate < 0.30 else 4


def _tui_content(text: str, meta: dict, limit: int) -> list:
    """Table rows first, then the same supporting information as Markdown."""
    agents = meta["agents"]
    sessions = agents["sessions"]
    working, recent = _ordered_sessions(sessions, limit)
    by_id = {s["id"]: s for s in sessions}
    now = time.time()
    rates = meta.get("rates", {})
    content = [(_session_cells(s, by_id, now), _rate_band(rates.get(_model_label(s))))
               for s in working + recent]
    if agents["error"]:
        content.append((agents["error"], 0))
    elif not content:
        content.append(("No sessions to display.", 0))

    # Preserve the runner, summary, explanatory text, model-rate legend and web
    # sections from this very snapshot. Session rows themselves are rebuilt from
    # their untruncated data so the TUI can use the available terminal width.
    lines = text.splitlines()
    agent_start = lines.index("## Agent sessions")
    content.extend((line, 0) for line in lines[:agent_start])
    summary_end = next((i for i in range(agent_start + 1, len(lines))
                        if lines[i].startswith("### Working now")), None)
    if summary_end is not None:
        content.extend((line, 0) for line in lines[agent_start:summary_end])
        details_start = next((i for i in range(summary_end, len(lines))
                              if lines[i].startswith("- `working`")), len(lines))
        content.extend((line, 0) for line in lines[summary_end:details_start]
                       if line.startswith("### "))
        content.extend((line, 0) for line in lines[details_start:])
    else:
        content.extend((line, 0) for line in lines[agent_start:])
    return content


def _tui_colours(enabled: bool) -> bool:
    if not enabled or not curses.has_colors():
        return False
    try:
        curses.start_color()
        try:
            curses.use_default_colors()
            background = -1
        except curses.error:
            background = curses.COLOR_BLACK
        orange = 208 if curses.COLORS > 208 else curses.COLOR_YELLOW
        for pair, colour in enumerate((curses.COLOR_GREEN, curses.COLOR_YELLOW,
                                       orange, curses.COLOR_RED), 1):
            curses.init_pair(pair, colour, background)
        return True
    except curses.error:
        return False


def _tui_put(screen, y: int, x: int, text: str, attr: int = 0) -> None:
    # A resize can happen between getmaxyx and addstr, and curses raises on the
    # bottom-right cell even when it successfully wrote it.
    try:
        screen.addstr(y, x, text, attr)
    except curses.error:
        pass


def _tui_screen(screen, port: int, limit: int, interval: float, colour: bool) -> None:
    screen.timeout(100)
    try:
        curses.curs_set(0)
    except curses.error:
        pass
    colours = _tui_colours(colour)
    results: queue.Queue = queue.Queue()
    pending = False
    next_refresh = 0.0
    snapshot = None
    error = None
    offset = 0
    text_offset = 0

    def collect() -> None:
        try:
            meta: dict = {}
            text = render(port, limit, meta)
            write(text)
            meta["refreshed"] = time.strftime("%Y-%m-%d %H:%M:%S")
            results.put((text, meta, None))
        except Exception as exc:
            results.put((None, None, f"refresh unavailable ({exc.__class__.__name__})"))

    while True:
        if not pending and time.monotonic() >= next_refresh:
            pending = True
            next_refresh = time.monotonic() + interval
            threading.Thread(target=collect, daemon=True).start()
        try:
            text, meta, error = results.get_nowait()
            pending = False
            if text is not None:
                snapshot = (text, meta)
        except queue.Empty:
            pass

        height, width = screen.getmaxyx()
        screen.erase()
        if _tui_too_small(height, width):
            if height and width:
                _tui_put(screen, 0, 0, _tui_fit("terminal too small", max(0, width - 1)))
        else:
            widths = _tui_widths(width)
            header = TUI_SEPARATOR.join(_tui_fit(cell, size)
                                        for cell, size in zip(TUI_HEADERS, widths))
            _tui_put(screen, 0, 0, header, curses.A_BOLD)
            if snapshot is None:
                content = [(error or "Loading snapshot…", 0)]
                working, total, refreshed = "?", "?", "pending"
            else:
                text, meta = snapshot
                content = _tui_content(text, meta, limit)
                if error:
                    content.insert(0, (error, 0))
                agents = meta["agents"]
                if agents["error"]:
                    working, total = "?", "?"
                else:
                    working = str(sum(s["working"] is True for s in agents["sessions"]))
                    total = f"${sum(s['cost'] for s in agents['sessions']):.4f}"
                refreshed = meta["refreshed"].split()[-1]
            visible = height - 2
            offset = max(0, min(offset, max(0, len(content) - visible)))
            for y, (row, band) in enumerate(content[offset:offset + visible], 1):
                if isinstance(row, str):
                    _tui_put(screen, y, 0, _tui_text_window(row, width, text_offset))
                else:
                    x = 0
                    for index, (cell, size) in enumerate(zip(row, widths)):
                        attr = curses.color_pair(band) if index == 3 and band and colours else 0
                        if index == 3 and band == 3 and colours and curses.COLORS <= 208:
                            attr |= curses.A_BOLD
                        _tui_put(screen, y, x, _tui_fit(cell, size), attr)
                        x += size
                        if index < len(widths) - 1:
                            _tui_put(screen, y, x, TUI_SEPARATOR)
                            x += len(TUI_SEPARATOR)
            footer = f"port:{port} | {working} working | {total} | {refreshed} | q ↑↓←→"
            if error:
                footer += f" | {error}"
            _tui_put(screen, height - 1, 0, _tui_fit(footer, width - 1), curses.A_REVERSE)
        try:
            screen.refresh()
            key = screen.getch()
        except curses.error:
            continue
        if key in (ord("q"), ord("Q")):
            return
        if key in (curses.KEY_DOWN, ord("j")):
            offset += 1
        elif key in (curses.KEY_UP, ord("k")):
            offset -= 1
        elif key == curses.KEY_NPAGE:
            offset += max(1, height - 2)
        elif key == curses.KEY_PPAGE:
            offset -= max(1, height - 2)
        elif key in (curses.KEY_RIGHT, ord("l")):
            text_offset += 10
        elif key in (curses.KEY_LEFT, ord("h")):
            text_offset = max(0, text_offset - 10)


def _positive_interval(value: str) -> float:
    try:
        interval = float(value)
        if math.isfinite(interval) and interval > 0:
            return interval
    except ValueError:
        pass
    raise argparse.ArgumentTypeError("interval must be a positive finite number")


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("--watch", type=float, metavar="SECONDS",
                        help="refresh continuously instead of printing once")
    parser.add_argument("--tui", action="store_true",
                        help="interactive terminal table (q quits; arrows scroll)")
    parser.add_argument("--interval", type=_positive_interval, default=2.0, metavar="SECONDS",
                        help="TUI refresh interval (default: 2 seconds)")
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
    if args.tui:
        if not sys.stdout.isatty():
            print("--tui requires a terminal on stdout", file=sys.stderr)
            return 1
        try:
            curses.wrapper(_tui_screen, args.port, limit, args.interval,
                           not args.no_color and not os.environ.get("NO_COLOR"))
        except (curses.error, OSError) as exc:
            print(f"TUI unavailable ({exc})", file=sys.stderr)
            return 1
        return 0
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

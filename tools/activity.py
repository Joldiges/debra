"""One read-only snapshot of what is running right now.

    python tools/activity.py             # tabbed view on a terminal
    python tools/activity.py --markdown  # the plain report, once
    python tools/activity.py --watch 5   # the tabbed view, refreshing

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
import queue
import re
import socket
import subprocess
import sys
import threading
import time
import unicodedata
from pathlib import Path

try:  # pragma: no cover - depends on how Python was built
    import curses
except ImportError:  # a Python without _curses must still print Markdown
    curses = None  # type: ignore[assignment]

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


def _needs(path: Path | None = None) -> dict:
    """What is waiting on James, read from the work queue's Needs table.

    The list lives in the repository so a person edits it, not an agent's
    memory, and this tool only reads it. A row that cannot be understood is
    counted and skipped rather than printed as a half-sentence.
    """
    path = Path(path) if path is not None else SOURCE / "docs" / "work-queue.md"
    try:
        text = path.read_text(encoding="utf-8")
    except OSError as exc:
        return {"items": [], "skipped": 0,
                "error": f"work queue not readable ({exc.__class__.__name__})"}
    lines = text.splitlines()
    try:
        start = lines.index("## Needs James")
    except ValueError:
        return {"items": [], "skipped": 0, "error": "no Needs James section in the work queue"}
    items, skipped = [], 0
    for line in lines[start + 1:]:
        if line.startswith("## "):
            break
        if not line.startswith("|"):
            continue
        cells = [cell.strip() for cell in line.strip().strip("|").split("|")]
        if len(cells) != 3 or cells[0] in ("Need", "") or set(cells[0]) <= set("-: "):
            if cells and set(cells[0]) <= set("-: ") and cells[0]:
                continue
            if cells and cells[0] not in ("Need", ""):
                skipped += 1
            continue
        items.append({"need": cells[0], "blocks": cells[1], "changes": cells[2]})
    return {"items": items, "skipped": skipped, "error": None}


def _needs_lines(needs: dict) -> list[str]:
    if needs["error"]:
        return [f"- {needs['error']}"]
    if not needs["items"]:
        return ["- Nothing is waiting on James; the blocked work below has no answer he holds."]
    out = []
    for item in needs["items"]:
        out.append(f"- **{item['need']}**")
        if item["blocks"]:
            out.append(f"  Blocks: {item['blocks']}")
        if item["changes"]:
            out.append(f"  The answer changes: {item['changes']}")
    if needs["skipped"]:
        out.append(f"- {needs['skipped']} further row(s) could not be read as a question and were skipped.")
    return out


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


def _tui_state(session: dict) -> str:
    return ("▶ run" if session["working"] is True
            else "◼ done" if session["working"] is False
            else "◻ new" if session["working"] is None else "?")


def _tui_why(session: dict, by_id: dict, now: float) -> str:
    """The same reason as the report, in a token short enough to never truncate.

    The report explains in prose; a column that repeats "finished; parent busy"
    on every row is noise, and truncating it to "finished; parent bu…" is worse.
    """
    why = _why(session, by_id, now)
    if why.startswith("running "):
        return "run " + why.split(" ", 1)[1]
    if why.startswith("long turn "):
        return "long " + why.split(" ", 2)[2]
    return {
        "running": "run",
        "never started": "never",
        "finished; parent busy": "done+busy",
        "finished": "done",
        "just finished": "done",
        "waiting for you": "yours",
        "parent deleted": "orphaned",
    }.get(why, why)


def _tui_model(label: str) -> str:
    """Shorten a model label to the word that distinguishes it.

    Every row used to print deepseek/deepseek-v4.1-flash-1017#high, which spent
    the column on a shared provider and version and still got cut.
    """
    model, _, variant = label.partition("#")
    tail = model.rsplit("/", 1)[-1]
    for word in ("flash", "terra", "sol", "opus", "sonnet"):
        if word in tail:
            return word + (f"·{variant}" if variant else "")
    return tail + (f"·{variant}" if variant else "")


def _tui_session_cells(session: dict, by_id: dict, now: float) -> list[str]:
    return [_tui_state(session), "sub" if session["child"] else "main",
            session["title"], _tui_model(_model_label(session)),
            f"${session['cost']:.2f}", _age(session["updated"], now),
            _tui_why(session, by_id, now)]


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
    needs = _needs()
    out = [f"# What is running — {now}", ""]

    # First, because it is the only section James can act on.
    out.append(f"## What I need from you ({len(needs['items'])})"
               if not needs["error"] else "## What I need from you")
    out.extend(_needs_lines(needs))
    out.append("")

    out.append("## Research runner")
    if run.get("error"):
        out.append(f"- Research runner {run['error']}")
    elif run["running"]:
        r = run["running"]
        elapsed = ("start time not readable" if r["elapsed_s"] is None
                   else f"{r['elapsed_s'] // 60}m {r['elapsed_s'] % 60}s ago")
        title = f" — {r['title']}" if r["title"] else ""
        out.append(f"- **Running now:** `{r['task']}`{title}")
        out.append(f"- Started {_local(r['since'])} local ({elapsed}) · model `{r['model']}`")
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
TUI_MIN_WIDTHS = [6, 4, 8, 5, 6, 3, 10]
TUI_MAX_WIDTHS = [6, 4, 48, 26, 8, 6, 18]
TUI_SEPARATOR = " | "
# How much of any extra width each column deserves. Why outranks Title because
# a Why cut to "finished; parent bu…" tells James nothing at all.
TUI_WEIGHTS = {0: 0, 1: 0, 2: 40, 3: 25, 4: 10, 5: 10, 6: 35}
# Always shown, in preference order: this is what a session table is for.
TUI_ESSENTIAL_COLUMNS = [0, 2, 6]
# The room a column needs to show a real value rather than "terr…". A column
# that can only reach its minimum is dropped instead of spoiling the values.
TUI_USEFUL_WIDTHS = [6, 4, 14, 11, 7, 3, 10]


def _tui_widths(columns: int, shown: list[int] | None = None) -> list[int] | None:
    """Widths for the shown columns, or None if even their minima will not fit.

    Extra space is shared by weight rather than handed out in a fixed order:
    growing Why first starved Model, and growing Title first truncated Why to
    "finished; parent bu…", which is worse than not showing it.
    """
    shown = list(range(len(TUI_MIN_WIDTHS))) if shown is None else list(shown)
    widths = [TUI_MIN_WIDTHS[index] for index in shown]
    remaining = columns - sum(widths) - len(TUI_SEPARATOR) * (len(shown) - 1)
    if remaining < 0:
        return None
    total = sum(TUI_WEIGHTS[index] for index in shown) or 1
    for position, index in enumerate(shown):
        grow = min(remaining * TUI_WEIGHTS[index] // total,
                   TUI_MAX_WIDTHS[index] - widths[position])
        widths[position] += grow
        remaining -= grow
    # Round-robin what is left (rounding, or a capped column) so no single
    # column swallows it.
    while remaining:
        grew = False
        for position, index in enumerate(shown):
            if remaining and widths[position] < TUI_MAX_WIDTHS[index]:
                widths[position] += 1
                remaining -= 1
                grew = True
        if not grew:
            break
    return widths


def _tui_can_show(columns: int, shown: list[int]) -> bool:
    """Every shown column must fit a real value, not just its minimum."""
    widths = _tui_widths(columns, shown)
    return widths is not None and all(
        width >= TUI_USEFUL_WIDTHS[index] for width, index in zip(widths, shown))


def _tui_visible_columns(columns: int) -> list[int]:
    """Drop the least useful columns while the important ones still fit.

    A narrow terminal used to truncate Why and Model into "done+b…" and
    "terra·fle…", which is noise. Kind, then Model, then Cost and Age go first.
    """
    shown = list(TUI_ESSENTIAL_COLUMNS)
    if not _tui_can_show(columns, shown):
        return shown
    for index in (5, 4, 3, 1):
        candidate = sorted(shown + [index])
        if _tui_can_show(columns, candidate):
            shown = candidate
    return shown


def _tui_too_small(lines: int, columns: int) -> bool:
    return lines < 4 or _tui_widths(columns, TUI_ESSENTIAL_COLUMNS) is None


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


def _rate_band(rate: float | None) -> int:
    """Curses pair number for the existing absolute model-rate bands."""
    if rate is None:
        return 0
    return 1 if rate < 0.05 else 2 if rate < 0.12 else 3 if rate < 0.30 else 4


# Each tab holds entries: ("text", text, style), ("header", cells), ("row", cells, band).
TUI_TABS = (("What I need from you", "Needs"), ("Agent sessions", "Sessions"),
            ("Research runner", "Research"), ("Development web server", "Status"))


def _tui_plain(text: str) -> str:
    """One Markdown line as terminal text: no asterisks, no backticks, no pipes."""
    text = text.replace("**", "").replace("`", "")
    text = text.replace("The answer changes: ", "→ ")
    stripped = text.lstrip()
    if stripped.startswith("- "):
        text = text[: len(text) - len(stripped)] + "• " + stripped[2:]
    return text.rstrip()


def _tui_sessions_entries(meta: dict, limit: int) -> list:
    """The session tab, built from data so it carries its own headings."""
    agents = meta.get("agents") or {}
    sessions = agents.get("sessions") or []
    if agents.get("error"):
        return [("text", agents["error"], "dim")]
    working_sessions, recent = _ordered_sessions(sessions, limit)
    by_id = {s["id"]: s for s in sessions}
    now = time.time()
    rates = meta.get("rates", {})
    entries = [("text", f"{len(working_sessions)} working · "
                        f"{sum(s['working'] is False for s in sessions)} idle · "
                        f"{len(sessions)} known · cost ${sum(s['cost'] for s in sessions):.2f}",
                "normal"), ("blank", "", 0)]
    for label, group in (("Working now", working_sessions), ("Recently active", recent)):
        if not group:
            continue
        entries.append(("text", f"{label} ({len(group)})", "bold"))
        entries.append(("header", list(TUI_HEADERS)))
        for session in group:
            entries.append(("row", _tui_session_cells(session, by_id, now),
                            _rate_band(rates.get(_model_label(session)))))
        entries.append(("blank", "", 0))
    if not working_sessions and not recent:
        entries.append(("text", "No sessions to display.", "normal"))
    return entries


def _tui_table_entries(block: list[str]) -> list[tuple]:
    """A Markdown table as aligned text: pipes and dashes are not information.

    The report keeps its pipes because it is Markdown; a terminal that drew
    them literally looked like escaped data, which is the noise this view exists
    to remove.
    """
    rows = []
    for line in block:
        cells = [cell.strip().replace("`", "").replace("**", "")
                 for cell in line.strip().strip("|").split("|")]
        if cells and all(re.fullmatch(r":?-{2,}:?", cell) for cell in cells):
            continue  # the | --- | --- | rule under the header
        rows.append(cells)
    if not rows:
        return []
    columns = max(len(row) for row in rows)
    widths = [max(len(row[index]) for row in rows if len(row) > index)
              for index in range(columns)]
    entries = []
    for number, row in enumerate(rows):
        text = " | ".join(cell.ljust(widths[index]) if index < columns - 1 else cell
                          for index, cell in enumerate(row)).rstrip()
        entries.append(("text", text, "bold" if number == 0 else "normal"))
    return entries


def _tui_tabs(text: str, meta: dict, limit: int) -> list[dict]:
    """Split the report into fixed-order tabs.

    Most tabs are the report's own words, because one source of truth means
    the terminal cannot drift from the file it writes. Sessions are rebuilt
    from data so the table fits the terminal and keeps its headings.
    """
    sections, order, current = {}, [], None
    for line in text.splitlines():
        if line.startswith("## "):
            current = line[3:].strip()
            order.append(current)
            sections[current] = []
            continue
        if current is not None:
            sections[current].append(line)
    allowed = {heading: label for heading, label in TUI_TABS}
    tabs = []
    for heading in order:
        base = heading.split(" (")[0].strip()
        if base not in allowed:
            continue
        if base == "Agent sessions":
            entries = _tui_sessions_entries(meta, limit)
        else:
            entries = []
            lines = sections[heading]
            index = 0
            while index < len(lines):
                line = lines[index]
                if line.startswith("|"):
                    block = []
                    while index < len(lines) and lines[index].startswith("|"):
                        block.append(lines[index])
                        index += 1
                    entries.extend(_tui_table_entries(block))
                    continue
                index += 1
                plain = _tui_plain(line)
                if not plain:
                    entries.append(("blank", "", 0))
                    continue
                if line.startswith(("- ", "  ")):
                    entries.append(("text", plain,
                                    "bold" if line.startswith("- ") else "normal"))
                else:
                    entries.append(("text", plain, "normal"))
        tabs.append({"label": allowed[base], "base": base, "entries": entries})
    rank = {heading: index for index, (heading, _label) in enumerate(TUI_TABS)}
    tabs.sort(key=lambda tab: rank[tab["base"]])
    if not tabs:
        tabs.append({"label": "Report", "base": "",
                     "entries": [("text", _tui_plain(line), "normal")
                                 for line in text.splitlines()]})
    return tabs


def _tui_wrap(text: str, width: int, indent: int = 0) -> list[str]:
    """Wrap to the terminal instead of truncating: the question matters most."""
    width = max(12, width - indent)
    if not text.strip():
        return [""]
    out, line = [], ""
    for word in text.split():
        if not line:
            line = word
        elif len(line) + 1 + len(word) <= width:
            line += " " + word
        else:
            out.append(line)
            line = word
    out.append(line)
    return out


def _tui_lines(tab: dict, width: int) -> list[tuple]:
    """Flatten a tab into display rows, wrapped for this width."""
    rows = []
    for entry in tab["entries"]:
        if entry[0] == "row":
            rows.append(("cells", entry[1], entry[2]))
        elif entry[0] == "header":
            rows.append(("cells", entry[1], None))
        elif entry[0] == "blank":
            rows.append(("text", "", "dim"))
        else:
            raw = entry[1]
            indent = len(raw) - len(raw.lstrip(" "))
            body = raw.strip()
            bullet = body.startswith("• ")
            for index, piece in enumerate(_tui_wrap(body, width, indent)):
                pad = indent + 2 if bullet and index else indent
                rows.append(("text", " " * pad + piece, entry[2]))
    return rows


def _tui_clamp(offset: int, total: int, visible: int) -> int:
    """Keep a scroll position inside the content instead of past its end."""
    return max(0, min(int(offset), max(0, total - max(0, visible))))


def _tui_key_action(key, tab_count: int) -> tuple[str, int] | None:
    """Map a key press to an action. Returned, not performed, so it is testable."""
    down = (ord("j"),) + ((curses.KEY_DOWN,) if curses else ())
    up = (ord("k"),) + ((curses.KEY_UP,) if curses else ())
    next_tab = (9, ord("l")) + ((curses.KEY_RIGHT,) if curses else ())
    prev_tab = (ord("h"),) + ((curses.KEY_LEFT,) if curses else ())
    if key in (ord("q"), ord("Q")):
        return ("quit", 0)
    if key in down:
        return ("scroll", 1)
    if key in up:
        return ("scroll", -1)
    if key == ord("g"):
        return ("top", 0)
    if key == ord("G"):
        return ("bottom", 0)
    if key == ord(" "):
        return ("pause", 0)
    if key in (ord("r"), ord("R")):
        return ("refresh", 0)
    if key in next_tab:
        return ("tab", 1)
    if key in prev_tab:
        return ("tab", -1)
    if curses and key == curses.KEY_NPAGE:
        return ("page", 1)
    if curses and key == curses.KEY_PPAGE:
        return ("page", -1)
    if isinstance(key, int) and ord("1") <= key < ord("1") + min(9, max(1, tab_count)):
        return ("select", key - ord("1"))
    return None


def _tui_colours(enabled: bool) -> bool:
    if not enabled or curses is None or not curses.has_colors():
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


def _tui_paint(screen, frame: dict, previous: dict | None, width: int) -> dict:
    """Write only the lines that changed; return the frame now on screen.

    Repainting every line on every tick flickers and, on a slow link, redraws a
    page of identical text. A line is rewritten when any of its pieces changed,
    and a line that has gone is blanked so nothing stale is left behind.
    """
    blank = " " * max(0, width)
    for y in sorted(set(previous or ()) - set(frame)):
        _tui_put(screen, y, 0, blank)
    for y in sorted(frame):
        pieces = frame[y]
        if previous is not None and previous.get(y) == pieces:
            continue
        if previous is not None:
            _tui_put(screen, y, 0, blank)  # a shorter line must not leave a tail
        for x, text, attr in pieces:
            _tui_put(screen, y, x, text, attr)
    return {y: pieces for y, pieces in frame.items()}


def _tui_tab_bar(tabs: list[dict], active: int, width: int) -> str:
    """A one-line tab bar; it degrades to numbers when the labels do not fit."""
    labels = [f" {index + 1}:{tab['label']} " for index, tab in enumerate(tabs)]
    bar = "".join(("[" + label + "]") if index == active else " " + label + " "
                  for index, label in enumerate(labels))
    if len(bar) > width:
        bar = " ".join(("[%d]" if index == active else "%d") % (index + 1)
                        for index in range(len(tabs)))
    return bar


def _tui_rule(width: int) -> str:
    return "─" * max(0, width)


def _tui_screen(screen, port: int, limit: int, interval: float, colour: bool) -> None:
    screen.timeout(100)
    try:
        curses.curs_set(0)
    except curses.error:
        pass
    colours = _tui_colours(colour)
    results: queue.Queue = queue.Queue()
    pending = False
    paused = False
    next_refresh = 0.0
    snapshot = None
    error = None
    active = 0
    offsets: dict[int, int] = {}
    frame = None
    size = (0, 0)

    def collect() -> None:
        try:
            meta: dict = {}
            text = render(port, limit, meta)
            write(text)
            meta["refreshed"] = time.strftime("%H:%M:%S")
            results.put((text, meta, None))
        except Exception as exc:  # the view must survive a failed probe
            results.put((None, None, f"refresh unavailable ({exc.__class__.__name__})"))

    def dim() -> int:
        return getattr(curses, "A_DIM", 0) if curses else 0

    while True:
        if not pending and not paused and time.monotonic() >= next_refresh:
            pending = True
            next_refresh = time.monotonic() + interval
            threading.Thread(target=collect, daemon=True).start()
        if not paused or snapshot is None:
            try:
                text, meta, error = results.get_nowait()
                pending = False
                if text is not None:
                    snapshot = (text, meta)
            except queue.Empty:
                pass

        height, width = screen.getmaxyx()
        if (height, width) != size:
            screen.erase()
            frame, size = None, (height, width)
        if _tui_too_small(height, width):
            if height and width:
                _tui_put(screen, 0, 0, _tui_fit("terminal too small", max(0, width - 1)))
            try:
                screen.refresh()
                key = screen.getch()
            except curses.error:
                continue
            if _tui_key_action(key, 1) == ("quit", 0):
                return
            continue

        tabs = (_tui_tabs(snapshot[0], snapshot[1], limit) if snapshot
                else [{"label": "Loading", "base": "",
                       "entries": [("text", error or "Loading snapshot…", "normal")]}])
        active = max(0, min(active, len(tabs) - 1))

        if snapshot:
            meta = snapshot[1]
            agents = meta.get("agents") or {"sessions": []}
            sessions = agents["sessions"]
            working = sum(s["working"] is True for s in sessions)
            total = f"${sum(s['cost'] for s in sessions):.2f}"
            refreshed = meta["refreshed"]
        else:
            working, total, refreshed = 0, "$?", "…"
        title = (f" activity · {refreshed} · {working} working · {total}"
                 + (" · PAUSED" if paused else "") + (" · loading" if pending and not snapshot else ""))
        if error:
            title += f" · {error}"
        pieces: dict[int, list] = {
            0: [(0, _tui_fit(title, width), curses.A_BOLD)],
            1: [(0, _tui_fit(_tui_tab_bar(tabs, active, width), width), curses.A_BOLD)],
            2: [(0, _tui_rule(width), dim())],
        }

        rows = _tui_lines(tabs[active], width)
        visible = max(1, height - 5)
        offset = _tui_clamp(offsets.get(active, 0), len(rows), visible)
        offsets[active] = offset
        shown = _tui_visible_columns(width)
        widths = _tui_widths(width, shown) or TUI_MIN_WIDTHS[:len(shown)]
        for y, row in enumerate(rows[offset:offset + visible], 3):
            if row[0] == "cells":
                cells, band = row[1], row[2]
                x = 0
                line = []
                for position, index in enumerate(shown):
                    cell, cell_width = cells[index], widths[position]
                    attr = 0
                    if band is None:
                        attr = curses.A_BOLD | dim()
                    elif index == 3 and band and colours:
                        attr = curses.color_pair(band)
                        if band == 3 and getattr(curses, "COLORS", 0) <= 208:
                            attr |= curses.A_BOLD
                    line.append((x, _tui_fit(cell, cell_width), attr))
                    x += cell_width
                    if position < len(shown) - 1:
                        line.append((x, TUI_SEPARATOR, dim()))
                        x += len(TUI_SEPARATOR)
                pieces[y] = line
            else:
                attr = curses.A_BOLD if row[2] == "bold" else dim() if row[2] == "dim" else 0
                pieces[y] = [(0, _tui_fit(row[1], width), attr)]

        span = (f" rows {offset + 1}-{min(len(rows), offset + visible)}/{len(rows)}"
                if len(rows) > visible else "")
        footer = (" j/k scroll · h/l tab · 1-4 select · space pause · r refresh · q quit"
                  + span + f" · {tabs[active]['label']}")
        pieces[height - 2] = [(0, _tui_rule(width), dim())]
        pieces[height - 1] = [(0, _tui_fit(footer, width), curses.A_REVERSE)]
        frame = _tui_paint(screen, pieces, frame, width)
        try:
            screen.refresh()
            key = screen.getch()
        except curses.error:
            continue
        action = _tui_key_action(key, len(tabs))
        if action is None:
            continue
        kind, amount = action
        if kind == "quit":
            return
        if kind == "tab":
            active = (active + amount) % len(tabs)
        elif kind == "select":
            active = min(amount, len(tabs) - 1)
        elif kind == "scroll":
            offsets[active] = _tui_clamp(offset + amount, len(rows), visible)
        elif kind == "page":
            offsets[active] = _tui_clamp(offset + amount * max(1, visible - 1),
                                         len(rows), visible)
        elif kind == "top":
            offsets[active] = 0
        elif kind == "bottom":
            offsets[active] = _tui_clamp(len(rows), len(rows), visible)
        elif kind == "pause":
            paused = not paused
        elif kind == "refresh":
            paused = False
            next_refresh = 0.0


def _positive_interval(value: str) -> float:
    try:
        interval = float(value)
        if math.isfinite(interval) and interval > 0:
            return interval
    except ValueError:
        pass
    raise argparse.ArgumentTypeError("interval must be a positive finite number")


def _watch_page(text: str) -> str:
    """The report minus its timestamp line, for deciding whether anything changed."""
    lines = text.splitlines()
    return "\n".join(line for line in lines
                     if not line.startswith("# What is running"))


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("--watch", type=float, metavar="SECONDS",
                        help="refresh continuously instead of printing once "
                             "(the TUI is the interactive view)")
    parser.add_argument("--tui", action="store_true",
                        help="interactive terminal table (the default on a terminal)")
    parser.add_argument("--markdown", action="store_true",
                        help="write the plain Markdown report even on a terminal")
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
    terminal = sys.stdout.isatty()
    # A terminal gets the tabbed view unless Markdown is asked for. Dumping the
    # report into a terminal produced pages of scrolling text in a watch loop,
    # which is what the view exists to replace.
    if not args.markdown and (args.tui or (terminal and curses is not None)):
        if not terminal:
            print("--tui requires a terminal on stdout; use --markdown for the "
                  "plain report", file=sys.stderr)
            return 1
        if curses is None:
            print("--tui needs the curses module, which this Python lacks; "
                  "use --markdown for the plain report", file=sys.stderr)
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
    paint = terminal and not args.no_color and not os.environ.get("NO_COLOR")
    previous_page = None
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
            if terminal:
                print("\033[2J\033[H" + display, flush=True)
                print(f"(written to {target}; refreshing every {args.watch:g}s; "
                      "Ctrl+C to stop" + ("; --all for every session)" if not args.all else ")"))
            else:
                # Piped or redirected, a cleared screen is just a wall of text.
                # Compare everything except the clock on the title line, or every
                # tick looks like a change and the log fills with copies.
                page = _watch_page(display)
                if page != previous_page:
                    previous_page = page
                    print(page, flush=True)
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

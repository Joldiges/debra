"""Notices: the things worth not missing, and which ones have been checked off.

A notice is *derived*, never stored. It exists because something in the
repository or on the machine says so: a blocker in the work queue, a failed
research task, a session that has been "working" for hours. Only the check mark
is stored, keyed by a stable id, so the same notice stays checked off across
refreshes and a notice that has gone away leaves nothing behind.

The point is not to alert. It is to let James look once, tick what he has dealt
with, and trust that the rest is still there.
"""

from __future__ import annotations

import hashlib
import json
import os
import time
from datetime import datetime, timezone
from pathlib import Path

STATE_PATH = Path(__file__).resolve().parent.parent / ".local" / "status" / "notices.json"

# Ordered worst first. A blocker stops work; a confirmation is an assumption the
# work continues on; attention is something that failed and may need a look;
# info is worth knowing and nothing more.
KINDS = ("blocker", "confirm", "attention", "info")
RANK = {kind: index for index, kind in enumerate(KINDS)}

MAX_READ = 500
# Half an hour in one turn: long enough that a normal turn is never mistaken
# for a stuck one, short enough to notice before the day is gone.
STALE_TURN_S = 1800


def stable_id(kind: str, source: str, title: str) -> str:
    """A short id that survives a refresh but not a change of wording.

    Recomputing it from the notice's own text means no counter, no ordering and
    no "which one was that?" bookkeeping: the same notice is the same id on the
    next run, and a genuinely different notice is a different id.
    """
    raw = f"{kind}|{source}|{title}".encode("utf-8", "replace")
    return hashlib.sha1(raw).hexdigest()[:12]


def _notice(kind: str, source: str, title: str, detail: str = "") -> dict:
    return {"id": stable_id(kind, source, title), "kind": kind, "source": source,
            "title": title, "detail": detail}


def _stamp(now=None) -> str:
    moment = datetime.fromtimestamp(now, timezone.utc) if now else datetime.now(timezone.utc)
    return moment.strftime("%Y-%m-%dT%H:%M:%SZ")


def collect(needs: dict | None = None, run: dict | None = None,
            agents: dict | None = None, web: dict | None = None,
            now: float | None = None) -> list[dict]:
    """Every notice the current snapshots justify. Pure: no files, no clocks.

    Nothing here invents a notice from an absence. "The web server is not
    listening" is normal, so it is not a notice; "a research task failed" is.
    """
    needs = needs or {}
    run = run or {}
    agents = agents or {}
    web = web or {}
    out: list[dict] = []

    for item in needs.get("items") or []:
        if item.get("kind") == "confirm":
            detail = item.get("blocks") or item.get("changes") or ""
            out.append(_notice("confirm", "Needs", item.get("need", ""),
                               f"assumes {detail}" if detail else ""))
        else:
            detail = item.get("blocks") or item.get("changes") or ""
            out.append(_notice("blocker", "Needs", item.get("need", ""),
                               f"blocks {detail}" if detail else ""))
    if needs.get("error"):
        out.append(_notice("attention", "Needs", needs["error"]))

    if run.get("error"):
        out.append(_notice("attention", "Research", f"Research runner {run['error']}"))
    else:
        if run.get("stop_file"):
            out.append(_notice("attention", "Research",
                               "Research runner stopped by a STOP file",
                               "Nothing starts until the STOP file is removed."))
        for task in run.get("recent") or []:
            if task.get("status") != "failed":
                continue
            # The finish time is part of the id, so the same task failing twice
            # is two notices and the second one is not silently pre-ticked.
            title = f"Research task failed: {task.get('task', 'unknown')}"
            if task.get("finished"):
                title += f" ({task['finished']})"
            out.append(_notice("attention", "Research", title,
                               f"cost ${float(task.get('cost') or 0):.4f}"))

    if agents.get("error"):
        out.append(_notice("attention", "Sessions", agents["error"]))
    else:
        for session in agents.get("sessions") or []:
            # A single turn running past half an hour is either stuck or
            # enormous. Both are worth one line. `busy_at` is the start of the
            # turn that has not ended yet.
            busy = session.get("busy_at")
            if session.get("working") is not True or not busy:
                continue
            elapsed = (time.time() if now is None else now) - busy
            if elapsed <= STALE_TURN_S:
                continue
            minutes = int(elapsed // 60)
            out.append(_notice("attention", "Sessions",
                               f"Session working for {minutes}m: "
                               f"{session.get('title') or session.get('id', '')}",
                               "Still a turn in progress, or stuck."))

    if web.get("error"):
        out.append(_notice("attention", "Status", f"Web probe {web['error']}"))

    # Two notices with the same id are the same notice; keep the first.
    seen, unique = set(), []
    for notice in out:
        if not notice["title"] or notice["id"] in seen:
            continue
        seen.add(notice["id"])
        unique.append(notice)
    return unique


def load(path: Path | None = None) -> dict:
    """The check marks. A missing or unreadable file means nothing is checked."""
    path = Path(path) if path is not None else STATE_PATH
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, ValueError):
        return {"version": 1, "read": {}}
    read = data.get("read") if isinstance(data, dict) else None
    if not isinstance(read, dict):
        return {"version": 1, "read": {}}
    return {"version": 1,
            "read": {str(key): str(value) for key, value in read.items()}}


def save(state: dict, path: Path | None = None) -> Path:
    """Write the check marks atomically and owner-only."""
    path = Path(path) if path is not None else STATE_PATH
    path.parent.mkdir(parents=True, exist_ok=True)
    read = dict(state.get("read") or {})
    # A bounded file: the oldest marks go before the newest, never the other way.
    if len(read) > MAX_READ:
        keep = sorted(read.items(), key=lambda item: item[1])[-MAX_READ:]
        read = dict(keep)
    payload = json.dumps({"version": 1, "read": read}, indent=1, sort_keys=True) + "\n"
    tmp = path.with_suffix(path.suffix + ".tmp")
    fd = os.open(tmp, os.O_WRONLY | os.O_CREAT | os.O_TRUNC, 0o600)
    with os.fdopen(fd, "w", encoding="utf-8") as stream:
        stream.write(payload)
        stream.flush()
        os.fsync(stream.fileno())
    os.replace(tmp, path)
    return path


def apply(notices: list[dict], state: dict) -> list[dict]:
    """Add the read flag and order unread first, worst first.

    Checked-off notices stay in the list rather than vanishing, so a mis-tick is
    one keystroke to undo and the count never lies about how much there was.
    """
    read = (state or {}).get("read") or {}
    decorated = []
    for notice in notices:
        copy = dict(notice)
        copy["read_at"] = read.get(notice["id"])
        copy["read"] = bool(copy["read_at"])
        decorated.append(copy)
    decorated.sort(key=lambda item: (item["read"], RANK.get(item["kind"], 9)))
    return decorated


def mark(notices: list[dict], state: dict, ids, read: bool = True,
         now: float | None = None, path: Path | None = None) -> dict:
    """Check or uncheck `ids`, pruning marks for notices that no longer exist."""
    present = {notice["id"] for notice in notices}
    marks = {key: value for key, value in ((state or {}).get("read") or {}).items()
             if key in present}
    for key in ids:
        if read:
            marks[key] = _stamp(now)
        else:
            marks.pop(key, None)
    state = {"version": 1, "read": marks}
    save(state, path)
    return state


def counts(notices: list[dict]) -> dict:
    unread = [notice for notice in notices if not notice.get("read")]
    return {"total": len(notices), "unread": len(unread),
            "blockers": sum(1 for notice in unread if notice["kind"] == "blocker"),
            "checked": len(notices) - len(unread)}


def label(notice: dict) -> str:
    """One short word for the kind, for a checkbox line."""
    return {"blocker": "Blocker", "confirm": "Confirm",
            "attention": "Attention", "info": "Info"}.get(notice.get("kind"), "Notice")


def lines(notices: list[dict], limit: int | None = None) -> list[str]:
    """The Markdown form, so the written report says what the terminal says."""
    if not notices:
        return ["- Nothing to report; no notice is outstanding."]
    shown = notices if limit is None else notices[:limit]
    out = []
    for notice in shown:
        mark_text = "[x]" if notice.get("read") else "[ ]"
        out.append(f"- {mark_text} **{label(notice)}** · {notice['title']}")
        if notice.get("detail"):
            out.append(f"  {notice['detail']}")
    if limit is not None and len(notices) > limit:
        out.append(f"- … {len(notices) - limit} more not shown here; the TUI lists them all.")
    return out

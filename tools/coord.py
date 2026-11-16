"""Bookkeeping for delegated AI work, and restricted role profiles.

    python tools/coord.py launch  --task CMP02 --role research \
        --model openrouter/deepseek/deepseek-v4.1-flash-1017#high \
        --base HEAD --prompt-file .local/coord/brief.txt
    python tools/coord.py capture --task CMP02 --session ses_abc
    python tools/coord.py snapshot --task CMP02 --path docs/research/x.md
    python tools/coord.py verdict --task CMP02 --reviewer "capable reviewer" \
        --model openrouter/openai/gpt-6.1-sol#high --verdict approve \
        --report .local/coord/verdict-body.md
    python tools/coord.py profile --task CMP02 --role edit --path docs/research/x.md
    python tools/coord.py status
    python tools/coord.py check

One directory per task under ``.local/coord/<task>/`` (ignored, owner-only):

    launch.json            what was assigned, to which model, from which base
    brief.md               the exact prompt that was sent
    submitted.md           the report that came back
    metadata.json           cost/tokens/model from OpenCode, report hash
    review/candidate.patch  the frozen candidate the reviewer reads
    review/manifest.json    base, patch hash, per-path hashes
    review/verdict.md       the verdict, naming the patch hash it reviewed

``profile`` writes an OpenCode agent file whose permissions are deny-by-default
and allow edits only for the named paths. OpenCode enforces those rules; this
tool only writes the file. Neither command launches a model, reviews a result,
merges anything, or grants a claim: the coordinator still runs the subagent,
reads the verdict, and integrates.

Records are local coordination state, not acceptance. A captured report is not a
reviewed result, and a verdict here is a pointer to a review that a person or a
separate session actually performed.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import os
import re
import subprocess
import sys
from datetime import datetime, timezone
from pathlib import Path

SOURCE = Path(__file__).resolve().parent.parent
if __name__ == "__main__":
    sys.dont_write_bytecode = True

TASK_RE = re.compile(r"^[A-Za-z0-9][A-Za-z0-9._-]{0,39}$")
ROLES = ("research", "edit", "review")
VERDICTS = ("approve", "changes", "reject")
PROTECTED_PATHS = (".local/*", ".git/*", "*.env", "*.env.*")
OPENCODE_TIMEOUT_S = 15
# Explicit HTTP only: never ask the CLI to discover or start a service.
OPENCODE_MAX_BYTES = 2 * 1024 * 1024


class CoordError(Exception):
    """A refusal with a message a coordinator can act on."""


def utc_now() -> str:
    return datetime.now(timezone.utc).isoformat(timespec="seconds")


def sha256_bytes(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def _slug(text: str) -> str:
    slug = re.sub(r"[^a-z0-9]+", "-", text.lower()).strip("-")
    if not slug:
        raise CoordError("task needs at least one letter or digit")
    return slug


def _task(value: str) -> str:
    if not TASK_RE.match(value or ""):
        raise CoordError(f"invalid task id {value!r}: use letters, digits, '.', '_' or '-'")
    return value


def _relative(value: str) -> str:
    """One assignment path, relative to the session's working directory."""
    raw = (value or "").strip()
    if not raw:
        raise CoordError("empty path")
    path = Path(raw)
    if path.is_absolute() or raw.startswith("~") or "$" in raw:
        raise CoordError(f"path {raw!r} must be relative, not absolute or expanded")
    if ".." in path.parts:
        raise CoordError(f"path {raw!r} must not climb out with '..'")
    if any(part in ("", ".") for part in path.parts):
        raise CoordError(f"path {raw!r} is not normalized")
    return path.as_posix()


def _write_private(path: Path, data: bytes) -> None:
    path.parent.mkdir(parents=True, exist_ok=True, mode=0o700)
    tmp = path.with_name(path.name + ".tmp")
    tmp.write_bytes(data)
    os.chmod(tmp, 0o600)
    tmp.replace(path)


def _json_text(value) -> bytes:
    return (json.dumps(value, indent=2, sort_keys=False) + "\n").encode()


def _read_json(path: Path, what: str) -> dict:
    try:
        value = json.loads(path.read_text())
    except FileNotFoundError:
        raise CoordError(f"{what} is missing: {path}")
    except (OSError, ValueError) as exc:
        raise CoordError(f"{what} is unreadable: {path} ({exc.__class__.__name__})")
    if not isinstance(value, dict):
        raise CoordError(f"{what} is not an object: {path}")
    return value


def _git(repo: Path, *args: str, ok_codes=(0,)) -> subprocess.CompletedProcess:
    try:
        result = subprocess.run(["git", *args], cwd=repo, capture_output=True,
                                text=True, timeout=60)
    except (OSError, subprocess.TimeoutExpired) as exc:
        raise CoordError(f"git unavailable ({exc.__class__.__name__})")
    if result.returncode not in ok_codes:
        raise CoordError(f"git {' '.join(args)} failed: {result.stderr.strip()[:300]}")
    return result


def _commit(repo: Path, value: str) -> str:
    if not re.fullmatch(r"[0-9A-Za-z][0-9A-Za-z._/~^@{}-]{0,119}", value or ""):
        raise CoordError(f"base {value!r} is not a revision")
    try:
        text = _git(repo, "rev-parse", "--verify", f"{value}^{{commit}}").stdout.strip()
    except CoordError:
        raise CoordError(f"base {value!r} did not resolve to a commit")
    if not re.fullmatch(r"[0-9a-f]{40}", text):
        raise CoordError(f"base {value!r} did not resolve to a commit")
    return text


def _records(args) -> Path:
    return Path(args.records).expanduser().resolve()


def _task_dir(args, task: str) -> Path:
    return _records(args) / _task(task)


def _launch_of(args, task: str) -> dict:
    launch = _read_json(_task_dir(args, task) / "launch.json", "launch record")
    if launch.get("task") != task:
        raise CoordError(f"launch record names {launch.get('task')!r}, not {task!r}")
    return launch


def _report_text(path_arg: str) -> bytes:
    if path_arg == "-":
        return sys.stdin.buffer.read()
    try:
        return Path(path_arg).expanduser().read_bytes()
    except OSError as exc:
        raise CoordError(f"report unreadable: {path_arg} ({exc.__class__.__name__})")


def _api_get(path: str):
    """One authenticated GET through the CLI, with no environment redirect."""
    env = {name: value for name, value in os.environ.items()
           if not name.upper().startswith(("OPENCODE_SERVER", "OPENCODE_API"))}
    try:
        proc = subprocess.run(["opencode", "api", "get", path], capture_output=True,
                              timeout=OPENCODE_TIMEOUT_S, env=env, check=False)
    except (OSError, subprocess.TimeoutExpired) as exc:
        raise CoordError(f"opencode unavailable ({exc.__class__.__name__})")
    if proc.returncode != 0:
        raise CoordError(f"opencode api get {path} failed (exit {proc.returncode})")
    if len(proc.stdout) > OPENCODE_MAX_BYTES:
        raise CoordError(f"opencode api get {path} returned too much data")
    try:
        return json.loads(proc.stdout)
    except (ValueError, UnicodeError):
        raise CoordError(f"opencode api get {path} returned unreadable JSON")


def session_record(session: str) -> dict:
    """Model, cost and token counts for one session, as the host reports them."""
    if not re.fullmatch(r"ses_[A-Za-z0-9]+", session or ""):
        raise CoordError(f"invalid session id {session!r}")
    payload = _api_get(f"/api/session/{session}")
    item = payload.get("data") if isinstance(payload, dict) else None
    if not isinstance(item, dict) or item.get("id") != session:
        raise CoordError(f"session {session} was not returned by the service")
    model = item.get("model") if isinstance(item.get("model"), dict) else {}
    tokens = item.get("tokens") if isinstance(item.get("tokens"), dict) else {}
    cost = item.get("cost")
    return {
        "id": session,
        "agent": item.get("agent") if isinstance(item.get("agent"), str) else "unknown",
        "title": item.get("title") if isinstance(item.get("title"), str) else "",
        "model": {
            "providerID": model.get("providerID") or "unknown",
            "id": model.get("id") or "unknown",
            "variant": model.get("variant") or "",
        },
        "cost": float(cost) if isinstance(cost, (int, float)) else None,
        "tokens": tokens,
        "directory": (item.get("location") or {}).get("directory", "")
        if isinstance(item.get("location"), dict) else "",
    }


def last_reply_text(session: str) -> str:
    """The last assistant text of a session, or '' when it cannot be read."""
    payload = _api_get(f"/api/session/{session}/message")
    items = payload.get("data") if isinstance(payload, dict) else None
    if not isinstance(items, list):
        return ""
    for item in reversed(items):
        if not isinstance(item, dict) or item.get("type") != "assistant":
            continue
        parts = item.get("content")
        if not isinstance(parts, list):
            continue
        texts = [part.get("text") for part in parts
                 if isinstance(part, dict) and part.get("type") == "text"
                 and isinstance(part.get("text"), str)]
        if texts:
            return "\n\n".join(texts)
    return ""


def cmd_launch(args) -> int:
    task = _task(args.task)
    if args.role not in ROLES:
        raise CoordError(f"role must be one of {', '.join(ROLES)}")
    paths = [_relative(path) for path in (args.path or [])]
    if args.role == "edit" and not paths:
        raise CoordError("an editing assignment must name at least one --path")
    if args.role in ("research", "review") and paths:
        raise CoordError(f"a {args.role} assignment is read-only: drop --path")
    if not (args.model or "").strip():
        raise CoordError("record the exact model, or 'unknown'; do not leave it blank")
    if args.budget is not None and not 1 <= args.budget <= 10:
        raise CoordError("--budget is a small attempt count between 1 and 10")
    repo = Path(args.repo).expanduser().resolve()
    base_commit = _commit(repo, args.base)
    directory = _task_dir(args, task)
    launch_path = directory / "launch.json"
    if launch_path.exists() and not args.force:
        raise CoordError(f"launch already recorded for {task}; use --force only to correct it")
    brief = _report_text(args.prompt_file)
    if not brief.strip():
        raise CoordError("the brief is empty")
    record = {
        "task": task,
        "role": args.role,
        "model": args.model.strip(),
        "base": args.base,
        "base_commit": base_commit,
        "paths": paths,
        "budget": args.budget,
        "created_utc": utc_now(),
        "brief": "brief.md",
        "brief_sha256": sha256_bytes(brief),
        "status": "launched; not captured",
    }
    _write_private(directory / "brief.md", brief)
    _write_private(launch_path, _json_text(record))
    print(f"launched {task} ({args.role}) at {launch_path}")
    print(f"base {base_commit[:12]}  model {record['model']}")
    if paths:
        print("allowed paths: " + ", ".join(paths))
    print("next: run the subagent, then `coord.py capture`")
    return 0


def cmd_capture(args) -> int:
    task = _task(args.task)
    launch = _launch_of(args, task)
    directory = _task_dir(args, task)
    report_path = directory / "submitted.md"
    meta_path = directory / "metadata.json"
    if report_path.exists() and not args.force:
        raise CoordError(f"{task} already has submitted.md; do not overwrite a frozen report")
    if args.outcome not in ("succeeded", "partial", "failed"):
        raise CoordError("outcome must be succeeded, partial or failed")

    session = None
    session_error = None
    text = None
    if args.session:
        try:
            session = session_record(args.session)
        except CoordError as exc:
            session_error = str(exc)
        if not args.report and not session_error:
            try:
                text = last_reply_text(args.session) or None
            except CoordError as exc:
                session_error = str(exc)
    if args.report:
        text = _report_text(args.report).decode("utf-8", "replace")
    if text is None:
        raise CoordError("no report: pass --report, or --session with a readable text reply")
    report = text.encode()
    if not report.strip():
        raise CoordError("the report is empty")

    model = launch["model"]
    cost = None
    if session:
        model = "/".join(filter(None, [
            session["model"]["providerID"], session["model"]["id"]])) \
            + (f"#{session['model']['variant']}" if session["model"]["variant"] else "")
        cost = session["cost"]
    metadata = {
        "task": task,
        "captured_utc": utc_now(),
        "session": args.session or None,
        "agent": (session or {}).get("agent", "unknown"),
        "model": model,
        "launched_model": launch["model"],
        "cost": cost,
        "tokens": (session or {}).get("tokens", {}),
        "outcome": args.outcome,
        "report_sha256": sha256_bytes(report),
        "report_bytes": len(report),
        "base_commit": launch["base_commit"],
        "session_error": session_error,
        "status": "captured; not reviewed",
    }
    _write_private(report_path, report)
    _write_private(meta_path, _json_text(metadata))
    print(f"captured {task} ({metadata['outcome']}) at {report_path}")
    print(f"model {model}" + (f"  cost ${cost:.4f}" if isinstance(cost, float) else ""))
    if session_error:
        print(f"note: session data unavailable ({session_error})")
    print("next: `coord.py snapshot` the candidate, then have it reviewed")
    return 0


def _untracked(repo: Path, path: str) -> list[str]:
    result = _git(repo, "ls-files", "--others", "--exclude-standard", "--", path)
    return [line for line in result.stdout.splitlines() if line.strip()]


def _diff_for(repo: Path, base: str, path: str) -> str:
    chunks = []
    tracked = _git(repo, "diff", "--binary", base, "--", path, ok_codes=(0,))
    if tracked.stdout.strip():
        chunks.append(tracked.stdout)
    for untracked in _untracked(repo, path):
        new_file = _git(repo, "diff", "--binary", "--no-index", "--",
                        os.devnull, untracked, ok_codes=(0, 1))
        if new_file.stdout.strip():
            chunks.append(new_file.stdout)
    return "".join(chunks)


def cmd_snapshot(args) -> int:
    task = _task(args.task)
    launch = _launch_of(args, task)
    directory = _task_dir(args, task) / "review"
    patch_path = directory / "candidate.patch"
    manifest_path = directory / "manifest.json"
    if patch_path.exists() and not args.force:
        raise CoordError(f"{task} already has a frozen candidate; a new one needs --force")
    repo = Path(args.repo).expanduser().resolve()
    base = _commit(repo, args.base or launch["base_commit"])
    paths = [_relative(path) for path in (args.path or launch.get("paths") or [])]
    if not paths:
        raise CoordError("nothing to snapshot: pass --path or record paths at launch")

    patch = "".join(_diff_for(repo, base, path) for path in paths)
    if not patch.strip():
        raise CoordError("the snapshot is empty: no change against the base on those paths")
    files = []
    for path in paths:
        target = repo / path
        if target.is_file():
            data = target.read_bytes()
            files.append({"path": path, "kind": "file",
                          "sha256": sha256_bytes(data), "bytes": len(data)})
        elif target.is_dir():
            files.append({"path": path, "kind": "directory"})
        else:
            files.append({"path": path, "kind": "absent"})
    manifest = {
        "task": task,
        "base_commit": base,
        "paths": paths,
        "files": files,
        "untracked": _untracked(repo, "."),
        "created_utc": utc_now(),
        "patch_sha256": sha256_bytes(patch.encode()),
        "patch_bytes": len(patch.encode()),
    }
    _write_private(patch_path, patch.encode())
    _write_private(manifest_path, _json_text(manifest))
    print(f"frozen candidate for {task} at {patch_path}")
    print(f"patch sha256 {manifest['patch_sha256']}")
    print("give that hash to the reviewer; the verdict must name it")
    return 0


def cmd_verdict(args) -> int:
    task = _task(args.task)
    directory = _task_dir(args, task) / "review"
    manifest = _read_json(directory / "manifest.json", "review manifest")
    verdict_path = directory / "verdict.md"
    if verdict_path.exists() and not args.force:
        raise CoordError(f"{task} already has a verdict; do not rewrite a review")
    if args.verdict not in VERDICTS:
        raise CoordError(f"verdict must be one of {', '.join(VERDICTS)}")
    if not (args.reviewer or "").strip():
        raise CoordError("name the reviewer; a verdict without an author is not a review")
    body = _report_text(args.report).decode("utf-8", "replace")
    if not body.strip():
        raise CoordError("the verdict body is empty")
    text = (
        f"# Verdict: {task}\n\n"
        f"- candidate sha256: {manifest['patch_sha256']}\n"
        f"- base commit: {manifest['base_commit']}\n"
        f"- reviewer: {args.reviewer.strip()}\n"
        f"- reviewer model: {(args.model or 'unknown').strip()}\n"
        f"- verdict: {args.verdict}\n"
        f"- recorded utc: {utc_now()}\n\n"
        f"{body}"
    )
    _write_private(verdict_path, text.encode())
    print(f"recorded {args.verdict} for {task} at {verdict_path}")
    if args.verdict != "approve":
        print("the candidate stays unreviewed-failed until it is repaired and re-reviewed")
    return 0


def _verdict_fields(path: Path) -> dict:
    fields = {}
    try:
        lines = path.read_text().splitlines()
    except OSError:
        return fields
    for line in lines:
        match = re.match(r"^- ([a-z0-9 ]+?): (.*)$", line)
        if match:
            fields[match[1]] = match[2]
    return fields


def _record_states(records: Path) -> list[dict]:
    states = []
    for launch_path in sorted(records.glob("*/launch.json")):
        directory = launch_path.parent
        try:
            launch = json.loads(launch_path.read_text())
        except (OSError, ValueError):
            launch = None
        state = {
            "directory": directory,
            "launch": launch if isinstance(launch, dict) else None,
            "task": (launch or {}).get("task") or directory.name
            if isinstance(launch, dict) else directory.name,
            "submitted": (directory / "submitted.md").exists(),
            "metadata": None,
            "manifest": None,
            "verdict": None,
        }
        meta_path = directory / "metadata.json"
        if meta_path.exists():
            try:
                state["metadata"] = json.loads(meta_path.read_text())
            except (OSError, ValueError):
                state["metadata"] = None
        manifest_path = directory / "review" / "manifest.json"
        if manifest_path.exists():
            try:
                state["manifest"] = json.loads(manifest_path.read_text())
            except (OSError, ValueError):
                state["manifest"] = None
        verdict_path = directory / "review" / "verdict.md"
        if verdict_path.exists():
            state["verdict"] = _verdict_fields(verdict_path)
        states.append(state)
    return states


def _short(value: str, width: int) -> str:
    if len(value) <= width:
        return value
    return value[: width - 1] + "…"


def cmd_status(args) -> int:
    records = _records(args)
    states = _record_states(records)
    if not states:
        print(f"no delegated tasks recorded under {records}")
        return 0
    rows = [("TASK", "ROLE", "MODEL", "BASE", "STATE", "COST")]
    total = 0.0
    for state in states:
        launch = state["launch"] or {}
        metadata = state["metadata"] or {}
        verdict = state["verdict"] or {}
        cost = metadata.get("cost")
        if isinstance(cost, (int, float)):
            total += float(cost)
        if verdict.get("verdict"):
            stage = f"reviewed: {verdict['verdict']}"
        elif state["manifest"]:
            stage = "candidate frozen"
        elif state["submitted"]:
            stage = "captured, unreviewed"
        else:
            stage = "launched"
        rows.append((
            state["task"],
            launch.get("role", "?"),
            _short(launch.get("model", "unknown"), 34),
            str(launch.get("base_commit", ""))[:8] or "?",
            stage,
            f"${cost:.4f}" if isinstance(cost, (int, float)) else "-",
        ))
    widths = [max(len(row[index]) for row in rows) for index in range(len(rows[0]))]
    for row in rows:
        print("  ".join(cell.ljust(widths[index]) for index, cell in enumerate(row)).rstrip())
    print(f"\n{len(states)} task(s), recorded spend ${total:.4f}")
    print("status shows records, not acceptance; integration is the coordinator's step")
    return 0


def cmd_check(args) -> int:
    records = _records(args)
    repo = Path(args.repo).expanduser().resolve()
    problems, checked = [], []
    for state in _record_states(records):
        directory = state["directory"]
        launch = state["launch"]
        if launch is None:
            problems.append(f"{directory.name}: launch.json is unreadable")
            continue
        task = launch.get("task")
        if task != directory.name or not TASK_RE.match(str(task or "")):
            problems.append(f"{directory.name}: launch names task {task!r}")
        if launch.get("role") not in ROLES:
            problems.append(f"{directory.name}: role {launch.get('role')!r} is not one of {ROLES}")
        if not str(launch.get("model") or "").strip():
            problems.append(f"{directory.name}: no model recorded")
        try:
            _commit(repo, str(launch.get("base_commit") or ""))
        except CoordError as exc:
            problems.append(f"{directory.name}: {exc}")
        brief_path = directory / "brief.md"
        try:
            brief = brief_path.read_bytes()
        except OSError:
            problems.append(f"{directory.name}: brief.md is missing")
        else:
            if sha256_bytes(brief) != launch.get("brief_sha256"):
                problems.append(f"{directory.name}: brief.md does not match its recorded hash")
        for path in launch.get("paths") or []:
            try:
                _relative(path)
            except CoordError as exc:
                problems.append(f"{directory.name}: recorded path: {exc}")
        metadata = state["metadata"]
        if state["submitted"]:
            if metadata is None:
                problems.append(f"{directory.name}: submitted.md without metadata.json")
            else:
                report = (directory / "submitted.md").read_bytes()
                if sha256_bytes(report) != metadata.get("report_sha256"):
                    problems.append(
                        f"{directory.name}: submitted.md changed after capture")
        elif metadata is not None:
            problems.append(f"{directory.name}: metadata.json without submitted.md")
        manifest = state["manifest"]
        if manifest is not None:
            patch_path = directory / "review" / "candidate.patch"
            try:
                patch = patch_path.read_bytes()
            except OSError:
                problems.append(f"{directory.name}: manifest without candidate.patch")
            else:
                if sha256_bytes(patch) != manifest.get("patch_sha256"):
                    problems.append(
                        f"{directory.name}: candidate.patch does not match its manifest")
        verdict = state["verdict"]
        if verdict is not None:
            if manifest is None:
                problems.append(f"{directory.name}: verdict without a frozen candidate")
            elif verdict.get("candidate sha256") != manifest.get("patch_sha256"):
                problems.append(
                    f"{directory.name}: verdict names a different candidate than the manifest")
            if not verdict.get("reviewer"):
                problems.append(f"{directory.name}: verdict names no reviewer")
            if verdict.get("verdict") not in VERDICTS:
                problems.append(f"{directory.name}: verdict value {verdict.get('verdict')!r}")
        checked.append(directory.name)
    for problem in problems:
        print(f"FAIL {problem}")
    if problems:
        print(f"FAIL: {len(problems)} problem(s) across {len(checked)} recorded task(s)")
        return 1
    print(f"PASS: {len(checked)} delegated task record(s) are internally consistent")
    print("This checks bookkeeping only: not review quality, model isolation, or truth")
    return 0


def _permissions(role: str, paths: list[str],
                 search: bool = False) -> list[tuple[str, str, str]]:
    rules = [("*", "*", "deny"), ("external_directory", "*", "deny")]
    rules += [
        ("read", "*", "allow"),
        # Agent rules are appended after the global ones, so a broad read allow
        # would otherwise re-open the global secret denies. Restate them here.
        ("read", "~/.ssh/*", "deny"),
        ("read", "~/.gnupg/*", "deny"),
        ("read", "~/.aws/*", "deny"),
        ("read", "*/auth.json", "deny"),
        ("read", "*.env", "deny"),
        ("read", "*.env.*", "deny"),
        ("read", ".local/*", "deny"),
        ("read", ".git/*", "deny"),
    ]
    if role == "review":
        rules += [("read", ".local/coord/*", "allow"),
                  ("read", ".local/reviews/*", "allow")]
    rules += [
        # No grep or glob by default: their permission resource is the pattern,
        # not the path, so they cannot respect the read denies above. A probe on
        # 2026-11-15 returned the contents of a `.local` file whose read was
        # denied. `read` is the search-free route that stays enforceable;
        # `--allow-search` opts back in for a checkout with no private state.
        ("webfetch", "*", "allow"),
        ("websearch", "*", "allow"),
    ]
    if search:
        rules += [("glob", "*", "allow"), ("grep", "*", "allow")]
    if role == "edit":
        # Reading the assignment's own brief is not needed: it is in the prompt.
        rules += [("edit", path, "allow") for path in paths]
    return rules


PROMPTS = {
    "research": (
        "You are a bounded Debra research worker. Read AGENTS.md, docs/evidence.md "
        "and the named inputs, then answer only the question you were given.\n\n"
        "Label every claim upstream-documented, reported, hypothesis or unknown, "
        "with a source URL and the date checked. Never invent a version, price, "
        "dimension or URL; report a blocked page instead. Write no files and run no "
        "commands: your permissions deny them. Return the report as your reply, in "
        "the handoff fields from docs/templates/worker-task.md.\n\n"
        "If an input is missing, stale, or contradicts the assignment, stop and say "
        "so rather than guessing or widening the task."
    ),
    "review": (
        "You are an independent Debra reviewer with fresh context. Read the "
        "assignment, the frozen candidate patch, and the sources the candidate "
        "cites. Judge requirements, correctness, safety, provenance, missing tests "
        "and acceptance criteria. You may not edit or run commands: your "
        "permissions deny them.\n\n"
        "Report findings in severity order with file and line references, name what "
        "you verified yourself, and state approve, changes or reject. A verdict must "
        "name the candidate hash you reviewed; do not approve a hash you were not "
        "given."
    ),
    "edit": (
        "You are a bounded Debra editing worker. Make only the assigned change, "
        "inside the allowed paths named in your permissions. Do not commit, push, "
        "widen scope, or change shared interfaces, pins, tests or acceptance "
        "criteria. Shell and nested delegation are denied; if a check needs them, "
        "report that instead of improvising.\n\n"
        "Before editing, restate the goal, the allowed paths, the checks you were "
        "given and your stop conditions. If the working tree contains unexplained "
        "work, a stale base, or a missing input, stop and report it."
    ),
}


def cmd_profile(args) -> int:
    task = _task(args.task)
    if args.role not in ROLES:
        raise CoordError(f"role must be one of {', '.join(ROLES)}")
    paths = [_relative(path) for path in (args.path or [])]
    if args.role == "edit" and not paths:
        raise CoordError("an editing profile must name at least one --path")
    if args.role != "edit" and paths:
        raise CoordError(f"a {args.role} profile is read-only: drop --path")
    name = f"local-{_slug(task)}"
    out = Path(args.out).expanduser() if args.out else \
        Path(args.repo).expanduser().resolve() / ".opencode" / "agents" / f"{name}.md"
    if out.exists() and not args.force:
        raise CoordError(f"profile already exists: {out}")
    description = (f"Task-scoped {args.role} profile for Debra {task}: deny-by-default, "
                   "generated by tools/coord.py")
    lines = ["---", f"description: {json.dumps(description)}", "mode: subagent",
             "permissions:"]
    for action, resource, effect in _permissions(args.role, paths, args.allow_search):
        lines += [f"  - action: {json.dumps(action)}",
                  f"    resource: {json.dumps(resource)}",
                  f"    effect: {effect}"]
    lines += ["---", "", PROMPTS[args.role], "",
              f"Assignment: {task}. Your allowed paths are the ones this profile "
              "permits; anything else is a refusal, not a negotiation."]
    _write_private(out, ("\n".join(lines) + "\n").encode())
    print(f"wrote {name} at {out}")
    print(f"launch the subagent as agent {json.dumps(name)}")
    print("these rules are enforced by OpenCode's permission layer; this tool only wrote them")
    if args.allow_search:
        print("note: grep and glob authorise a pattern, not a path, so they can read a "
              "denied path's contents; use this only in a checkout with no private state")
    return 0


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="Bookkeeping for delegated AI work, and restricted role profiles. "
                    "It records assignments and snapshots candidates; it does not launch "
                    "models, review results, or merge.")
    parser.add_argument("--records", default=str(SOURCE / ".local" / "coord"),
                        help="records directory (default: .local/coord)")
    parser.add_argument("--repo", default=str(SOURCE), help="repository root")
    sub = parser.add_subparsers(dest="command", required=True)

    launch = sub.add_parser("launch", help="record one bounded assignment")
    launch.add_argument("--task", required=True)
    launch.add_argument("--role", required=True, choices=ROLES)
    launch.add_argument("--model", required=True,
                        help="exact host-reported provider/model#variant, or 'unknown'")
    launch.add_argument("--base", default="HEAD")
    launch.add_argument("--prompt-file", required=True, help="the brief actually sent")
    launch.add_argument("--path", action="append", default=[],
                        help="one allowed path; required for editing, refused otherwise")
    launch.add_argument("--budget", type=int, default=None,
                        help="bounded attempts, 1-10")
    launch.add_argument("--force", action="store_true")
    launch.set_defaults(func=cmd_launch)

    capture = sub.add_parser("capture", help="freeze the returned report and cost")
    capture.add_argument("--task", required=True)
    capture.add_argument("--session", help="OpenCode session id, for model/cost/tokens")
    capture.add_argument("--report", help="file with the report text, or - for stdin")
    capture.add_argument("--outcome", default="succeeded",
                         choices=("succeeded", "partial", "failed"))
    capture.add_argument("--force", action="store_true")
    capture.set_defaults(func=cmd_capture)

    snapshot = sub.add_parser("snapshot", help="freeze the review candidate")
    snapshot.add_argument("--task", required=True)
    snapshot.add_argument("--path", action="append", default=[])
    snapshot.add_argument("--base")
    snapshot.add_argument("--force", action="store_true")
    snapshot.set_defaults(func=cmd_snapshot)

    verdict = sub.add_parser("verdict", help="record a review verdict")
    verdict.add_argument("--task", required=True)
    verdict.add_argument("--reviewer", required=True)
    verdict.add_argument("--model", default="unknown")
    verdict.add_argument("--verdict", required=True, choices=VERDICTS)
    verdict.add_argument("--report", required=True, help="file with the findings, or -")
    verdict.add_argument("--force", action="store_true")
    verdict.set_defaults(func=cmd_verdict)

    profile = sub.add_parser("profile", help="write a restricted OpenCode agent file")
    profile.add_argument("--task", required=True)
    profile.add_argument("--role", default="research", choices=ROLES)
    profile.add_argument("--path", action="append", default=[])
    profile.add_argument("--allow-search", action="store_true",
                         help="also allow grep and glob; they bypass path denies")
    profile.add_argument("--out")
    profile.add_argument("--force", action="store_true")
    profile.set_defaults(func=cmd_profile)

    status = sub.add_parser("status", help="show recorded delegated work")
    status.set_defaults(func=cmd_status)

    check = sub.add_parser("check", help="verify records are internally consistent")
    check.set_defaults(func=cmd_check)
    return parser


def main(argv=None) -> int:
    args = build_parser().parse_args(argv)
    try:
        return args.func(args)
    except CoordError as exc:
        print(f"coord: {exc}", file=sys.stderr)
        return 2


if __name__ == "__main__":
    sys.exit(main())

"""The onboarding state, persisted so a reboot does not restart the journey.

One small JSON file is the whole record: which phase the device is in, what it
last tried, and what it last failed with. It deliberately never holds a Wi-Fi
passphrase — NetworkManager owns the keyfile, and a copy here would be a second
place to leak it from.
"""

from __future__ import annotations

import json
import os
import tempfile
from datetime import datetime, timezone
from pathlib import Path

# unconfigured: nothing joined yet, nothing running.
# hotspot:      the setup access point is up and the portal is serving.
# connecting:   the access point is down and an association is being tried.
# online:       joined, with a routable address; the access point is down.
# failed:       an attempt failed; the access point is coming back with a reason.
PHASES = ("unconfigured", "hotspot", "connecting", "online", "failed")

SCHEMA = 1


def now():
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def blank(hostname=""):
    return {
        "schema": SCHEMA,
        "phase": "unconfigured",
        "hostname": hostname,
        "country": None,
        "ssid": None,
        "address": None,
        "last_error": None,
        "attempts": 0,
        "hotspot": None,
        "baseline": None,
        "updated": now(),
    }


def validate(data):
    """Refuse anything this module did not write, rather than guessing."""
    if not isinstance(data, dict):
        raise ValueError("Setup state must be an object")
    allowed = set(blank())
    extra = set(data) - allowed
    if extra:
        raise ValueError(f"Unknown setup state keys: {', '.join(sorted(extra))}")
    if data.get("schema") != SCHEMA:
        raise ValueError(f"Unsupported setup state schema: {data.get('schema')!r}")
    if data.get("phase") not in PHASES:
        raise ValueError(f"Unknown setup phase: {data.get('phase')!r}")
    for key in ("hostname", "ssid", "address", "last_error"):
        value = data.get(key)
        if value is not None and (not isinstance(value, str) or len(value) > 200):
            raise ValueError(f"Setup state {key} must be text up to 200 characters")
    if data.get("country") is not None:
        if not isinstance(data["country"], str) or len(data["country"]) != 2:
            raise ValueError("Country must be a two-letter code or null")
    if not isinstance(data.get("attempts"), int) or not 0 <= data["attempts"] <= 1000:
        raise ValueError("Attempts must be a whole number up to 1000")
    hotspot = data.get("hotspot")
    if hotspot is not None:
        if not isinstance(hotspot, dict) or set(hotspot) != {"ssid", "interface"}:
            raise ValueError("Hotspot must be {ssid, interface}")
        for value in hotspot.values():
            if not isinstance(value, str) or not 1 <= len(value) <= 64:
                raise ValueError("Hotspot values must be text of 1-64 characters")
    baseline = data.get("baseline")
    if baseline is not None and (not isinstance(baseline, str) or len(baseline) > 200):
        raise ValueError("Baseline must be a path up to 200 characters")
    return data


def read(path):
    """Read the state, or return a blank record when there is none yet.

    A corrupt file is an error, not a reason to silently reset: resetting would
    hide the fact that a device had already been configured.
    """
    path = Path(path)
    try:
        raw = path.read_text(encoding="utf-8")
    except FileNotFoundError:
        return blank()
    data = json.loads(raw)
    return validate(data)


def write(path, data):
    """Replace the file atomically, owner-only, without following a symlink."""
    path = Path(path)
    validate(data)
    data = dict(data, updated=now())
    payload = json.dumps(data, indent=1, sort_keys=True).encode() + b"\n"
    path.parent.mkdir(parents=True, exist_ok=True, mode=0o700)
    fd, staged = tempfile.mkstemp(prefix=".setup.staged-", dir=path.parent)
    try:
        with os.fdopen(fd, "wb") as stream:
            stream.write(payload)
            stream.flush()
            os.fsync(stream.fileno())
        os.chmod(staged, 0o600)
        os.replace(staged, path)
    except BaseException:
        try:
            os.unlink(staged)
        except OSError:
            pass
        raise
    return data

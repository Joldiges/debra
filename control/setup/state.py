"""The onboarding state, persisted so a reboot does not restart the journey.

One small JSON file is the whole record: which phase the device is in, what it
last tried, and what it last failed with. It deliberately never holds the
household Wi-Fi passphrase — NetworkManager owns that keyfile, and a copy here
would be a second place to leak it from.

The setup network's own password is a different credential and is deliberately
not here either: it lives in its own owner-only file beside this one, because
this file is the record the status API reports. It is generated, not derived: a
password computed from the device name is computable by anyone who can see the
name broadcast, which is everyone in range. It is also written to the
boot-partition note, which is how the owner learns it.
"""

from __future__ import annotations

import json
import logging
import os
import tempfile
from datetime import datetime, timezone
from pathlib import Path

LOGGER = logging.getLogger(__name__)

# unconfigured: nothing joined yet, nothing running.
# hotspot:      the setup access point is up and the portal is serving.
# connecting:   the access point is down and an association is being tried.
# online:       joined, with a routable address; the access point is down.
# failed:       an attempt failed; the access point is coming back with a reason.
PHASES = ("unconfigured", "hotspot", "connecting", "online", "failed")

SCHEMA = 2

# Keys an earlier schema kept and this one does not. `hotspot_password` held the
# setup network's password inside the record the status API reports; it now
# lives in its own owner-only file. Such a key is dropped on read rather than
# refused: `validate` rejects anything it did not write, so refusing an older
# record would leave an upgraded device with no setup network at all, and the
# journal would say only "ValueError".
DROPPED = ("hotspot_password",)

# Paths whose migrated record could not be written back. `read` is on the status
# path, so a read-only state directory would otherwise log the same warning on
# every poll; one line is enough for anyone to notice the filesystem.
_WRITE_BACK_FAILED = set()


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
        "last_attempt": None,
        # Which in-flight attempt this record belongs to. `last_attempt` is a
        # one-second timestamp, so two attempts in the same second - a retry
        # after a lost reply is exactly that - would share it. A worker that was
        # superseded must not be able to match its reservation by accident.
        "attempt_token": None,
        # Set by the worker that claimed the token, under the lock, before it
        # touches the radio. Checking a token is not claiming it: two workers
        # holding the same valid token both passed the check.
        "attempt_claimed": False,
        "hotspot": None,
        "baseline": None,
        # Why the last baseline attempt failed, in words a person can read. It
        # is separate from last_error, which is about joining: a device can be
        # online and still have no baseline.
        "baseline_error": None,
        "updated": now(),
    }


def migrate(data):
    """Bring an older record up to the current schema, or return it unchanged.

    Only a *lower* schema is touched. A record from a newer one is left alone so
    that `validate` refuses it: a downgraded service must not silently discard a
    field it does not understand. Migration fills keys the older schema did not
    have from `blank()`, which is what makes an upgrade a restart rather than a
    failed unit.
    """
    if not isinstance(data, dict):
        return data
    schema = data.get("schema")
    if isinstance(schema, bool) or not isinstance(schema, int):
        return data
    if schema >= SCHEMA:
        return data
    migrated = {key: value for key, value in data.items() if key not in DROPPED}
    for key, value in blank().items():
        migrated.setdefault(key, value)
    migrated["schema"] = SCHEMA
    return migrated


def validate(data):
    """Refuse anything this module did not write, rather than guessing."""
    if not isinstance(data, dict):
        raise ValueError("Setup state must be an object")
    allowed = set(blank())
    extra = set(data) - allowed
    if extra:
        raise ValueError(f"Unknown setup state keys: {', '.join(sorted(extra))}")
    missing = allowed - set(data)
    if missing:
        # A record that validates but then raises KeyError in status() is worse
        # than one refused at the boundary.
        raise ValueError(f"Setup state is missing keys: {', '.join(sorted(missing))}")
    schema = data.get("schema")
    # `True == 1`, so a JSON `true` would otherwise pass as schema 1.
    if isinstance(schema, bool) or schema != SCHEMA:
        raise ValueError(f"Unsupported setup state schema: {schema!r}")
    if data.get("phase") not in PHASES:
        raise ValueError(f"Unknown setup phase: {data.get('phase')!r}")
    for key in ("hostname", "ssid", "address", "last_error", "baseline_error"):
        value = data.get(key)
        if value is not None and (not isinstance(value, str) or len(value) > 200):
            raise ValueError(f"Setup state {key} must be text up to 200 characters")
    if data.get("country") is not None:
        if not isinstance(data["country"], str) or len(data["country"]) != 2:
            raise ValueError("Country must be a two-letter code or null")
    attempts = data.get("attempts")
    if isinstance(attempts, bool) or not isinstance(attempts, int) \
            or not 0 <= attempts <= 1000:
        # bool is an int subclass: True would otherwise pass as one attempt.
        raise ValueError("Attempts must be a whole number up to 1000")
    if not isinstance(data.get("attempt_claimed"), bool):
        # A truthy string here would be treated as "a worker owns this attempt".
        raise ValueError("attempt_claimed must be true or false")
    for key, limit in (("last_attempt", 40), ("updated", 40), ("attempt_token", 64)):
        value = data.get(key)
        if value is not None and (not isinstance(value, str) or len(value) > limit):
            raise ValueError(f"{key} must be a timestamp or null")
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
    migrated = validate(migrate(data))
    if isinstance(data, dict) and migrated["schema"] != data.get("schema"):
        # Write the migrated record back, best effort. The whole point of
        # dropping `hotspot_password` is that the credential stops living in
        # this file; leaving it there until something else happens to write
        # would keep it on disk for an unbounded time. The attempt is repeated
        # rather than given up on - the filesystem may only be read-only for a
        # while - but the warning is logged once per path, because this is on
        # the status path and a poll must not repeat it every fifteen seconds.
        try:
            migrated = write(path, migrated)
            _WRITE_BACK_FAILED.discard(str(path))
        except (OSError, ValueError):
            if str(path) not in _WRITE_BACK_FAILED:
                _WRITE_BACK_FAILED.add(str(path))
                LOGGER.warning("The migrated setup state could not be written back; "
                               "the retired key stays on disk until it can be")
    return migrated


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

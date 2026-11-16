"""The onboarding state, persisted so a reboot does not restart the journey.

One small JSON file is the whole record: which phase the device is in, what it
last tried, and what it last failed with. It deliberately never holds the
household Wi-Fi passphrase — NetworkManager owns that keyfile, and a copy here
would be a second place to leak it from.

The setup network's own password is a different credential and is kept here. It
is generated, not derived: a password computed from the device name is computable
by anyone who can see the name broadcast, which is everyone in range. It is also
written to the boot-partition note, which is how the owner learns it.

Every write bumps a `revision`. The setup page uses it to order answers: an
answer is only news if it is newer than the screen it would replace. Schema 1
records are migrated on read; that migration is the one path that accepts a
record the current validator would refuse.
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

# Schema 2 added `attempt_claimed`, `hotspot_password` and `revision`. Schema 1
# records are migrated on read rather than refused: a device that already ran the
# earlier prototype must not be left with a state file that stops the service.
# The migration fills every field that record never wrote, because the prototype
# revisions did not all carry the same keys: filling only the three added at
# schema 2 left three of the five records this repository wrote missing
# `attempt_token`, `baseline_error` or `last_attempt`, and the validator refused
# them before the service could even report why.
SCHEMA = 2


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
        # The setup network's generated password. Written to the boot-partition
        # note so the owner can join; not derivable from anything public.
        "hotspot_password": None,
        "baseline": None,
        # Why the last baseline attempt failed, in words a person can read. It
        # is separate from last_error, which is about joining: a device can be
        # online and still have no baseline.
        "baseline_error": None,
        # A counter that increases with every write. The setup page uses it to
        # tell a status answer that is genuinely newer than its own submission
        # from one that merely started after it. `updated` has one-second
        # resolution, which is not enough to order two writes in the same
        # second - and a retry after a lost reply is exactly that.
        "revision": 0,
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
    for key, limit in (("last_attempt", 40), ("updated", 40), ("attempt_token", 64),
                       ("hotspot_password", 63)):
        value = data.get(key)
        if value is not None and (not isinstance(value, str) or len(value) > limit):
            raise ValueError(f"{key} must be a timestamp or null")
    password = data.get("hotspot_password")
    if password is not None and (not isinstance(password, str)
                                 or not 8 <= len(password) <= 63):
        raise ValueError("Hotspot password must be 8-63 characters or null")
    if password is not None:
        # A generated WPA passphrase is printable and has no whitespace. A
        # newline or a space here is not a credential any phone can type, and
        # it would be written verbatim into the boot-partition note.
        if any(not 33 <= ord(char) <= 126 for char in password):
            raise ValueError("Hotspot password must be printable characters without spaces")
    revision = data.get("revision")
    if isinstance(revision, bool) or not isinstance(revision, int) or revision < 0:
        raise ValueError("Revision must be a whole number from zero")
    hotspot = data.get("hotspot")
    if hotspot is not None:
        if not isinstance(hotspot, dict) or set(hotspot) != {"ssid", "interface"}:
            raise ValueError("Hotspot must be {ssid, interface}")
        for value in hotspot.values():
            if not isinstance(value, str) or not 1 <= len(value) <= 64:
                raise ValueError("Hotspot values must be text of 1-64 characters")
        # A described access point with no credential is one nothing can join.
        # The old record could describe one because the password was not stored
        # at all; now the two always travel together.
        if password is None:
            raise ValueError("A described hotspot needs its password")
    if data.get("phase") == "hotspot" and hotspot is None:
        raise ValueError("The hotspot phase needs a described hotspot")
    if data.get("phase") == "connecting" and data.get("attempt_token") is None:
        # `admit()` writes the token with the phase, under the lock. A record
        # with one and not the other is a state this module did not write.
        raise ValueError("The connecting phase needs an attempt token")
    if data.get("phase") == "online" and hotspot is not None:
        raise ValueError("An online device has no setup hotspot")
    baseline = data.get("baseline")
    if baseline is not None and (not isinstance(baseline, str) or len(baseline) > 200):
        raise ValueError("Baseline must be a path up to 200 characters")
    return data


def _migrate_1(data):
    """Bring a schema-1 record forward without guessing at a credential.

    Every field that record did not write is filled from `blank()`. A missing
    field has no value to lose: the prototype revisions added and removed keys
    between themselves, so a record can lack `attempt_token`, `baseline_error`
    or `last_attempt` and still be a record this repository wrote. Refusing it
    on a missing key stopped the service on a device that had merely upgraded.

    Schema 1 stored no setup-network password. It may still describe a hotspot,
    because the old code raised one and then wrote the note; after an upgrade
    the access point is not running. Keeping that description would leave a
    phase of `hotspot` with no password, which the page cannot use and which
    `validate()` rightly refuses. The description is dropped instead, and the
    next boot raises the access point again with a fresh password.
    """
    migrated = dict(data)
    for key, value in blank().items():
        migrated.setdefault(key, value)
    migrated["schema"] = SCHEMA
    if migrated.get("hotspot") is not None and migrated.get("hotspot_password") is None:
        migrated["hotspot"] = None
        if migrated.get("phase") in ("hotspot", "connecting"):
            migrated["phase"] = "failed"
            migrated["last_error"] = ("The setup network is raised again after the "
                                      "software update")
        migrated["attempt_token"] = None
        migrated["attempt_claimed"] = False
    return migrated


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
    # `True == 1`, so a JSON `true` must not be treated as schema 1.
    if (isinstance(data, dict) and not isinstance(data.get("schema"), bool)
            and data.get("schema") == 1):
        data = _migrate_1(data)
    return validate(data)


def write(path, data):
    """Replace the file atomically, owner-only, without following a symlink."""
    path = Path(path)
    validate(data)
    try:
        previous = json.loads(path.read_text(encoding="utf-8")).get("revision", 0)
    except (OSError, ValueError):
        previous = 0
    if isinstance(previous, bool) or not isinstance(previous, int) or previous < 0:
        previous = 0
    current = data.get("revision", 0)
    if isinstance(current, bool) or not isinstance(current, int) or current < 0:
        current = 0
    data = dict(data, updated=now(), revision=max(previous, current) + 1)
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

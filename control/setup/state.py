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

Every write bumps a `revision`. The setup page uses it to order answers: an
answer is only news if it is newer than the screen it would replace. Older
records are migrated on read; that migration is the one path that accepts a
record the current validator would refuse.
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

# Schema 2 added `attempt_claimed`, `hotspot_password` and `revision`, and kept
# the setup password inside this record. Schema 3 takes that password out: it
# lives in its own owner-only file, so the status API cannot report it and a
# baseline cannot archive it. Older records are migrated on read rather than
# refused - a device that already ran an earlier build must not be left with a
# state file that stops the service and leaves it with no access point.
#
# The migration fills the fields a later revision added (`state.FILLED`), because
# the prototype revisions did not all carry the same keys: filling none of them
# left three of the five records this repository wrote missing `attempt_token`,
# `baseline_error` or `last_attempt`, and the validator refused them before the
# service could even report why. It does not fill the record's shape: a record
# missing a core key is damage, and `MANDATORY_1` refuses it.
SCHEMA = 3

# Keys an earlier schema kept and this one does not. Dropped on read: `validate`
# rejects anything it did not write, so refusing an older record would leave an
# upgraded device with no setup network at all, and the journal would say only
# "ValueError".
DROPPED = ("hotspot_password",)

# Keys a record written by an earlier build could be missing, because the
# prototype revisions added and removed them between themselves. Only these are
# filled from `blank()`: every other key is part of the record's shape, and a
# file without one was not written by this module. Filling those too would turn
# a corrupt file into a fresh device - a record with no `phase` came back as
# `unconfigured` and was written back that way - which `read` promises never to
# do. `updated` is deliberately *not* here: the first prototype wrote it, so a
# record without it is damage like a record without `phase` (`MANDATORY_1`).
FILLED = ("last_attempt", "attempt_token", "attempt_claimed", "baseline_error",
          "revision")

# Paths whose migrated record could not be written back. `read` is on the status
# path, so a read-only state directory would otherwise log the same warning on
# every poll; one line is enough for anyone to notice the filesystem.
_WRITE_BACK_FAILED = set()

# The fields every schema-1 revision wrote, and therefore the floor below which a
# record is not a record this software wrote. The keys the revisions added later
# are deliberately not here: their absence is an ordinary upgrade and is filled.
# `updated` is here because the first prototype revision already wrote it, so its
# absence is damage rather than an upgrade even though `FILLED` covers the rest.
# `phase` matters most: every revision required it, and filling it produced an
# `unconfigured` device from a file that described nothing, which then raised a
# new access point as though the device had never been set up.
MANDATORY_1 = ("phase", "hostname", "country", "ssid", "address", "last_error",
               "attempts", "hotspot", "baseline", "updated")


def now():
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def sync_directory(path):
    """Make a completed rename in `path` durable. Never raises.

    Replacing a file and fsyncing it is not enough: the directory entry itself
    is a write, and a power cut straight after the rename can lose it and leave
    the old file. `nm` and the baseline code already sync their directories; the
    state and the chosen mode have the same requirement, and a lost mode write
    changes which protection the next boot uses.
    """
    try:
        fd = os.open(str(path), os.O_RDONLY | getattr(os, "O_DIRECTORY", 0))
    except OSError:
        return
    try:
        os.fsync(fd)
    except OSError:
        pass
    finally:
        os.close(fd)


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
    for key, limit in (("last_attempt", 40), ("updated", 40), ("attempt_token", 64)):
        value = data.get(key)
        if value is not None and (not isinstance(value, str) or len(value) > limit):
            raise ValueError(f"{key} must be a timestamp or null")
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


def migrate(data):
    """Bring an older record up to the current schema, or return it unchanged.

    Only a *lower* schema is touched. A record from a newer one is left alone so
    that `validate` refuses it: a downgraded service must not silently discard a
    field it does not understand. So is a version that never existed - schema 0
    or a negative one is a corrupt file, and filling it from `blank()` would
    silently reset a device that had already been configured, which `read`'s
    docstring promises never to do.

    Every field an *older schema* could lack is filled from `blank()`; see
    `FILLED`. A missing field has no value to lose: the prototype revisions
    added and removed keys between themselves, so a record can lack
    `attempt_token`, `baseline_error` or `last_attempt` and still be a record
    this repository wrote. Refusing it on a missing key stopped the service on a
    device that had merely upgraded. A key outside that set is part of the
    record's shape, and a file without one is refused rather than filled: a
    record with no `phase` is a corrupt file, not a fresh device.

    That floor has a name for schema 1. `MANDATORY_1` is the set every prototype
    revision wrote, so a record missing any of it was never a record this
    software wrote: an object as small as `{"schema": 1}` is damage, and filling
    it would raise a fresh setup access point on a device that had already been
    set up. Damage is an error with its own message, not a factory reset.

    A record can also carry a combination the current rules refuse even after
    the missing keys are filled: `connecting` with no attempt token, `hotspot`
    with no access point described, or `online` with one. Those are resolved the
    way the next boot resolves them, because refusing the file would stop the
    service before it could raise an access point - which is the failure this
    migration exists to prevent.

    Schema 1 stored no setup-network password, and may describe a hotspot that
    is not running after the upgrade. That description is dropped and the phase
    becomes `failed` with a reason, because a described access point with no
    credential is one nothing can join. Schema 2 held the password itself; it is
    dropped here (the secret moves to its own file), and the description is kept
    because the next raise generates the password and rewrites the card note.
    """
    if not isinstance(data, dict):
        return data
    schema = data.get("schema")
    if isinstance(schema, bool) or not isinstance(schema, int):
        return data
    if not 1 <= schema < SCHEMA:
        return data
    migrated = {key: value for key, value in data.items() if key not in DROPPED}
    if schema == 1:
        # The floor main's review asked for, in this migration's own terms: the
        # keys an older record may lack are `FILLED`, and every other key is the
        # record's shape. Naming the schema-1 subset gives the damage its own
        # message instead of reaching `validate`'s key list.
        missing = [key for key in MANDATORY_1 if key not in migrated]
        if missing:
            raise ValueError("That state file is not a setup record this software "
                             "wrote: " + ", ".join(missing) + " missing")
    defaults = blank()
    for key in FILLED:
        migrated.setdefault(key, defaults[key])
    migrated["schema"] = SCHEMA
    if schema == 1 and migrated.get("hotspot") is not None:
        migrated["hotspot"] = None
        if migrated.get("phase") in ("hotspot", "connecting"):
            migrated["phase"] = "failed"
            migrated["last_error"] = ("The setup network is raised again after the "
                                      "software update")
        migrated["attempt_token"] = None
        migrated["attempt_claimed"] = False
    # Three combinations an earlier build could leave cannot pass the current
    # rules, and refusing them would stop the service before any access point is
    # raised - the outcome this migration exists to prevent. Each is a state the
    # next boot would have resolved anyway, so it is resolved here instead.
    if migrated.get("phase") == "connecting" and not migrated.get("attempt_token"):
        # The attempt belonged to a worker in a process that is gone.
        migrated["phase"] = "failed"
        migrated["last_error"] = "The last attempt did not finish"
        migrated["attempt_claimed"] = False
    if migrated.get("phase") == "hotspot" and migrated.get("hotspot") is None:
        migrated["phase"] = "failed"
        migrated["last_error"] = ("The setup network is raised again after the "
                                  "software update")
    if migrated.get("phase") == "online" and migrated.get("hotspot") is not None:
        # An online device has no setup network: nothing is running to keep.
        migrated["hotspot"] = None
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
    migrated = validate(migrate(data))
    if isinstance(data, dict) and migrated["schema"] != data.get("schema"):
        # Write the migrated record back. The whole point of dropping
        # `hotspot_password` is that the credential stops living in this file;
        # leaving it there until something else happens to write would keep it
        # on disk for an unbounded time. The attempt is repeated rather than
        # given up on - the filesystem may only be read-only for a while - but
        # the warning is logged once per path, because this is on the status
        # path and a poll must not repeat it every fifteen seconds.
        #
        # Only if the file is still the one that was read: `read` is not under
        # the same lock as every writer, so a record saved in between must not
        # be replaced by this older one. The compare and the replace cannot be
        # made one operation here, so this narrows the window rather than
        # closing it.
        try:
            current = path.read_text(encoding="utf-8")
        except OSError:
            # Unreadable now, where it was readable a moment ago. Nothing else
            # will mention that the retired key is still on disk, so say it once.
            current = None
            if str(path) not in _WRITE_BACK_FAILED:
                _WRITE_BACK_FAILED.add(str(path))
                LOGGER.warning("The setup state could not be re-read; the retired "
                               "key stays on disk until it can be")
        if current == raw:
            try:
                migrated = write(path, migrated)
                _WRITE_BACK_FAILED.discard(str(path))
            except (OSError, ValueError):
                if str(path) not in _WRITE_BACK_FAILED:
                    _WRITE_BACK_FAILED.add(str(path))
                    LOGGER.warning("The migrated setup state could not be written "
                                   "back; the retired key stays on disk until it can be")
    return migrated


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
    sync_directory(path.parent)
    return data

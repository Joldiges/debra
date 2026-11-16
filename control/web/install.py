"""Install only the Debra web prototype for the current Linux audio-session user.

No packages, sudo, audio writes, service starts, or existing component changes.
Run on the device, not on the development host. See README.md for recovery.
"""

import argparse
from datetime import datetime, timezone
import hashlib
import ipaddress
import json
import os
from pathlib import Path
import stat
import sys
import tempfile

from server import (Backend, init_state, load_devices, valid_hosts, validate_device,
                    validate_listening_port)


PAYLOAD = ("server.py", "discovery.py", "assets/index.html", "assets/style.css", "assets/app.js")
MARKER = "# Managed by Debra web prototype\n"


def quoted(value):
    # systemd argument quoting, not shell quoting; % expands even inside quotes.
    value = str(value)
    if any(ord(char) < 32 or ord(char) == 127 for char in value):
        raise ValueError("Control characters are not allowed in service arguments")
    return '"' + value.replace("\\", "\\\\").replace('"', '\\"').replace("%", "%%").replace("$", "$$") + '"'


def create_private(path, data):
    """Create a new file that is owner-only from the instant it exists.

    `open("xb")` creates with the process umask, so a 0644 file exists between
    creation and the later `chmod`. An interruption in that window leaves it
    readable. The containing directory is 0700, so this was never a leak in
    practice, but the README says the staging files themselves are private and
    they now are.
    """
    fd = os.open(path, os.O_WRONLY | os.O_CREAT | os.O_EXCL, 0o600)
    with os.fdopen(fd, "wb") as stream:
        stream.write(data)
        stream.flush()
        os.fsync(stream.fileno())


def payload_digest(payload):
    """The content address a release is named by."""
    digest = hashlib.sha256()
    for name, data in sorted(payload.items()):
        digest.update(name.encode() + b"\0" + data + b"\0")
    return digest.hexdigest()


def release_digest(release):
    """The digest of a release directory as it is on disk."""
    return payload_digest({name: (release / name).read_bytes() for name in PAYLOAD})


def damaged_releases(releases):
    """Retained releases whose contents no longer match the name they carry.

    A release is named by the digest of its payload, so a corrupted file is
    detectable without a manifest. This matters for rollback: the previous unit
    runs a retained release, and restoring one whose bytes changed starts a
    service that fails immediately. Nothing is deleted here; the caller reports
    it.
    """
    damaged = []
    if not releases.is_dir():
        return damaged
    for path in sorted(releases.iterdir()):
        if path.is_symlink() or not path.is_dir():
            continue
        try:
            if release_digest(path) != path.name:
                damaged.append(path.name)
        except OSError:
            damaged.append(path.name)
    return damaged


def directory(path, private=False):
    """Reject symlink ancestors rather than writing through an unrelated path."""
    for ancestor in (path, *path.parents):
        if ancestor.is_symlink():
            raise ValueError("Refusing a symlinked install path")
    path.mkdir(parents=True, exist_ok=True, mode=0o700)
    info = path.stat()
    if info.st_uid != os.getuid() or (private and info.st_mode & 0o077):
        raise ValueError("Install directory must be owned by this user; private paths need 0700")


def store_devices(state, devices):
    data = json.dumps(devices, indent=1).encode() + b"\n"
    stored = state / ("devices-" + hashlib.sha256(data).hexdigest() + ".json")
    if not stored.exists() and not stored.is_symlink():
        # No replacement: an old unit may still depend on this exact content.
        fd, staged = tempfile.mkstemp(prefix=".devices.staged-", dir=state)
        with os.fdopen(fd, "wb") as stream:
            stream.write(data)
        try:
            os.link(staged, stored)
        except FileExistsError:
            pass
    fd = os.open(stored, os.O_RDONLY | os.O_NOFOLLOW | os.O_NONBLOCK)
    with os.fdopen(fd, "rb") as stream:
        info = os.fstat(stream.fileno())
        if (not stat.S_ISREG(info.st_mode) or info.st_uid != os.getuid() or
                info.st_size != len(data) or stream.read() != data):
            raise ValueError("Existing device list differs or is not an owned regular file")
        os.fchmod(stream.fileno(), 0o600)
    return stored


def install(home, source, sink, bind, port, hosts, python, auth="key", devices=None):
    if auth not in ("key", "none"):
        raise ValueError("auth must be 'key' or 'none'")
    validate_listening_port(port)
    if not valid_hosts(hosts):
        raise ValueError("Use explicit hostname:port authorities and an unprivileged port")
    if any(int(host.rsplit(":", 1)[1]) != port for host in hosts):
        raise ValueError("Every allowed Host must use the listening port")
    ipaddress.IPv4Address(bind)
    for arg in (home, python, *hosts):
        quoted(arg)  # Reject service-file injection before any writes.
    Backend(sink, {})  # Validate selection before writing files; does not probe.
    # `main()` validated the file it read; a programmatic caller did not, and
    # the server would then refuse the list it was handed at the next start.
    if devices:
        if len(devices) > 50:
            raise ValueError("Device list allows at most 50 entries")
        devices = [validate_device(item) for item in devices]
    payload = {name: (source / name).read_bytes() for name in PAYLOAD}
    release_id = payload_digest(payload)
    base = home / ".local/share/debra/web"
    state = home / ".config/debra/web"
    unit = home / ".config/systemd/user/debra-web.service"
    for path in (base, state, unit.parent):
        for ancestor in (path, *path.parents):
            if ancestor.is_symlink():
                raise ValueError("Refusing a symlinked install directory")
    if unit.is_symlink() or (unit.exists() and not unit.read_text().startswith(MARKER)):
        raise ValueError("Existing service is not managed by this installer; left unchanged")
    init_state(state)
    directory(base, private=True)
    releases = base / "releases"
    directory(releases, private=True)
    release = releases / release_id
    if release.exists():
        if (release.is_symlink() or (release / "assets").is_symlink() or
                any((release / name).is_symlink() or (release / name).read_bytes() != data
                    for name, data in payload.items())):
            raise ValueError("Release directory differs from expected payload; preserved without overwrite")
    else:
        # An interrupted copy leaves a private staging directory, not a poisoned
        # content-addressed release. Retry can publish a fresh complete copy.
        staging = Path(tempfile.mkdtemp(prefix=".pending-", dir=releases))
        for name, data in payload.items():
            target = staging / name
            target.parent.mkdir(mode=0o700, exist_ok=True)
            create_private(target, data)
        staging.rename(release)
    args = [python, "-B", str(release / "server.py"), "serve", "--state-dir", str(state),
            "--bind", bind, "--port", str(port), "--sink", sink, "--auth", auth]
    if devices:
        # Validated at startup too; copying it into the private state directory
        # keeps the unit independent of wherever the operator kept the file.
        stored = store_devices(state, devices)
        args.extend(["--devices", str(stored)])
    for host in hosts:
        args.extend(["--host", host])
    text = MARKER + (
        "[Unit]\nDescription=Debra local browser controls (prototype)\n"
        "After=pipewire-pulse.service\n"
        # Without a start limit a unit that cannot start restarts every three
        # seconds for ever, and the only trace is a journal line. Four attempts
        # in five minutes then "start request repeated too quickly".
        "StartLimitIntervalSec=300\nStartLimitBurst=4\n\n"
        "[Service]\nType=simple\n"
        "ExecStart=" + " ".join(quoted(arg) for arg in args) + "\n"
        "Environment=PULSE_SERVER=unix:%t/pulse/native\n"
        "UMask=0077\nNoNewPrivileges=yes\n"
        "Restart=on-failure\nRestartSec=3\nTimeoutStopSec=5\n\n"
        "[Install]\nWantedBy=default.target\n"
    )
    directory(unit.parent)
    backup = None
    damaged = damaged_releases(releases)
    if unit.exists() and unit.read_text() == text:
        return {"release": release_id, "unit": str(unit), "previous_unit": None,
                "changed": False, "damaged_releases": damaged}
    if unit.exists():
        snapshots = base / "previous-units"
        directory(snapshots, private=True)
        stamp = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%S%fZ")
        backup = snapshots / (stamp + ".service")
        create_private(backup, unit.read_bytes())
    # The previous unit (if any) is preserved before the atomic replacement.
    fd, name = tempfile.mkstemp(prefix="debra-web.service.", suffix=".pending", dir=unit.parent)
    candidate = Path(name)
    try:
        with os.fdopen(fd, "w") as stream:
            stream.write(text)
        candidate.chmod(0o600)
        os.replace(candidate, unit)
    except BaseException:
        # A failed rename leaves a complete candidate named `.pending` in the
        # unit's own directory. It is not loadable, but it is litter in a
        # system-managed folder and nothing ever removes it.
        try:
            candidate.unlink()
        except OSError:
            pass
        raise
    return {"release": release_id, "unit": str(unit),
            "previous_unit": str(backup) if backup else None, "changed": True,
            "damaged_releases": damaged}


def restore_unit(home, source):
    """Replace the service unit with a preserved one, atomically.

    A copy truncates the destination before writing, so an interruption partway
    through leaves a file that is neither the old unit nor the new one, with no
    ExecStart line and no way to start. Writing a complete file and renaming it
    over the unit means the unit is always one of the two versions.
    """
    home = Path(home)
    unit = home / ".config" / "systemd" / "user" / "debra-web.service"
    source = Path(source)
    text = source.read_bytes()
    command = executable_line(text)
    if command is None:
        raise ValueError("That file is not a service unit: it has no ExecStart line")
    gone = missing_release(text)
    if gone is not None:
        # A unit whose release was removed starts and immediately fails, which
        # looks like a rollback that worked. Refuse instead of producing it.
        raise ValueError(f"That unit runs {gone}, which is not installed; "
                         "install instead of restoring it")
    changed = changed_release(text)
    if changed is not None:
        raise ValueError(f"That unit runs {changed}, whose files no longer match "
                         "the content it is named by; install instead of restoring it")
    directory(unit.parent)
    fd, name = tempfile.mkstemp(prefix="debra-web.service.", suffix=".restore",
                                dir=unit.parent)
    candidate = Path(name)
    try:
        with os.fdopen(fd, "wb") as stream:
            stream.write(text)
            stream.flush()
            os.fsync(stream.fileno())
        candidate.chmod(0o600)
        os.replace(candidate, unit)
    except BaseException:
        try:
            candidate.unlink()
        except OSError:
            pass
        raise
    return unit


def executable_line(text):
    """The unit's real ExecStart value, or None.

    A comment mentioning `ExecStart=` is not a command, and a unit whose only
    ExecStart is commented out cannot start. Testing for the bytes alone
    accepted it.
    """
    for raw in text.decode("utf-8", "replace").splitlines():
        line = raw.strip()
        if line.startswith("ExecStart="):
            value = line[len("ExecStart="):].strip()
            return value or None
    return None


def missing_release(text):
    """The release path a unit runs, when it is not on disk. None otherwise.

    Restoring a unit whose code is gone produces a service that cannot start,
    which is the failure a rollback is meant to avoid. Only a recognisable
    release path is checked; a unit that runs something else is left alone.
    """
    command = executable_line(text)
    if not command:
        return None
    for token in command.split():
        token = token.strip('"')
        if token.endswith("/server.py") and "/releases/" in token:
            return None if Path(token).is_file() else token
    return None


def changed_release(text):
    """The release a unit runs when its bytes no longer match its name.

    `missing_release` only proves the file exists. A retained release whose
    files were truncated, replaced or half-copied still exists and still
    starts, then fails. The directory name is the digest of the payload, so
    the mismatch is checkable before the unit is restored.
    """
    command = executable_line(text)
    if not command:
        return None
    for token in command.split():
        token = token.strip('"')
        if not (token.endswith("/server.py") and "/releases/" in token):
            continue
        release = Path(token).parent
        try:
            if release_digest(release) == release.name:
                return None
            return token
        except OSError:
            return None
    return None


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--sink",
                        help="audio sink name the server should use")
    parser.add_argument("--bind", default="127.0.0.1", help="Explicit IPv4 address; LAN: 0.0.0.0")
    parser.add_argument("--port", type=int, default=8787)
    parser.add_argument("--host", action="append",
                        help="Allowed hostname:port; repeatable, required when installing. "
                             "Not needed with --restore")
    parser.add_argument("--auth", choices=["key", "none"], default="key",
                        help="key: require the device access key (default); none: development bypass")
    parser.add_argument("--devices", type=Path,
                        help="JSON list of known devices for the one-stop card")
    parser.add_argument("--restore", type=Path, metavar="PREVIOUS_UNIT",
                        help="atomically restore a unit preserved under "
                             "previous-units/, then stop")
    args = parser.parse_args()
    if os.getuid() == 0:
        parser.error("Run as the device's ordinary audio-session user, not root")
    if args.restore:
        try:
            unit = restore_unit(Path.home(), args.restore)
        except (OSError, ValueError) as exc:
            parser.error(str(exc))
        print(f"unit: {unit}")
        print("Unit restored atomically; nothing was started or stopped.")
        print("Next: systemctl --user daemon-reload")
        return
    if not args.sink:
        parser.error("--sink is required unless --restore is given")
    if not args.host:
        # The guide stops the service and then restores it. Parsing used to
        # refuse that command for a missing install argument before it ever
        # reached the restore, leaving the person with a stopped service.
        parser.error("--host is required when installing (it is not used by --restore)")
    devices = []
    if args.devices:
        try:
            devices = load_devices(args.devices)
        except (OSError, ValueError) as exc:
            parser.error(str(exc))
    try:
        result = install(Path.home(), Path(__file__).resolve().parent, args.sink,
                         args.bind, args.port, args.host, sys.executable,
                         auth=args.auth, devices=devices)
    except (OSError, ValueError) as exc:
        parser.error(str(exc))
    for name, value in result.items():
        print(f"{name}: {value}")
    damaged = result.get("damaged_releases") or []
    if damaged:
        print("WARNING: these retained releases no longer match the content they "
              "are named by, so rolling back to one would start a broken service: "
              + ", ".join(damaged), file=sys.stderr)
    print("Files prepared; no service started and no audio settings changed.")
    print("Next: systemctl --user daemon-reload")
    print("Then: systemctl --user enable --now debra-web.service")


if __name__ == "__main__":
    main()

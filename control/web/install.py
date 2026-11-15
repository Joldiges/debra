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

from server import Backend, init_state, load_devices, valid_hosts


PAYLOAD = ("server.py", "assets/index.html", "assets/style.css", "assets/app.js")
MARKER = "# Managed by Debra web prototype\n"


def quoted(value):
    # systemd argument quoting, not shell quoting; % expands even inside quotes.
    value = str(value)
    if any(ord(char) < 32 or ord(char) == 127 for char in value):
        raise ValueError("Control characters are not allowed in service arguments")
    return '"' + value.replace("\\", "\\\\").replace('"', '\\"').replace("%", "%%").replace("$", "$$") + '"'


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
    if not valid_hosts(hosts) or not 1024 <= port <= 65535:
        raise ValueError("Use explicit hostname:port authorities and an unprivileged port")
    if any(int(host.rsplit(":", 1)[1]) != port for host in hosts):
        raise ValueError("Every allowed Host must use the listening port")
    ipaddress.IPv4Address(bind)
    for arg in (home, python, *hosts):
        quoted(arg)  # Reject service-file injection before any writes.
    Backend(sink, {})  # Validate selection before writing files; does not probe.
    payload = {name: (source / name).read_bytes() for name in PAYLOAD}
    digest = hashlib.sha256()
    for name, data in sorted(payload.items()):
        digest.update(name.encode() + b"\0" + data + b"\0")
    release_id = digest.hexdigest()
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
            with target.open("xb") as stream:
                stream.write(data)
            target.chmod(0o600)
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
        "After=pipewire-pulse.service\n\n"
        "[Service]\nType=simple\n"
        "ExecStart=" + " ".join(quoted(arg) for arg in args) + "\n"
        "Environment=PULSE_SERVER=unix:%t/pulse/native\n"
        "UMask=0077\nNoNewPrivileges=yes\n"
        "Restart=on-failure\nRestartSec=3\nTimeoutStopSec=5\n\n"
        "[Install]\nWantedBy=default.target\n"
    )
    directory(unit.parent)
    backup = None
    if unit.exists() and unit.read_text() == text:
        return {"release": release_id, "unit": str(unit), "previous_unit": None, "changed": False}
    if unit.exists():
        snapshots = base / "previous-units"
        directory(snapshots, private=True)
        stamp = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%S%fZ")
        backup = snapshots / (stamp + ".service")
        with backup.open("xb") as stream:
            stream.write(unit.read_bytes())
        backup.chmod(0o600)
    # The previous unit (if any) is preserved before the atomic replacement.
    fd, name = tempfile.mkstemp(prefix="debra-web.service.", suffix=".pending", dir=unit.parent)
    candidate = Path(name)
    with os.fdopen(fd, "w") as stream:
        stream.write(text)
    candidate.chmod(0o600)
    os.replace(candidate, unit)
    return {"release": release_id, "unit": str(unit),
            "previous_unit": str(backup) if backup else None, "changed": True}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--sink", required=True)
    parser.add_argument("--bind", default="127.0.0.1", help="Explicit IPv4 address; LAN: 0.0.0.0")
    parser.add_argument("--port", type=int, default=8787)
    parser.add_argument("--host", action="append", required=True, help="Allowed hostname:port; repeatable")
    parser.add_argument("--auth", choices=["key", "none"], default="key",
                        help="key: require the device access key (default); none: development bypass")
    parser.add_argument("--devices", type=Path,
                        help="JSON list of known devices for the one-stop card")
    args = parser.parse_args()
    if os.getuid() == 0:
        parser.error("Run as the device's ordinary audio-session user, not root")
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
    print("Files prepared; no service started and no audio settings changed.")
    print("Next: systemctl --user daemon-reload")
    print("Then: systemctl --user enable --now debra-web.service")


if __name__ == "__main__":
    main()

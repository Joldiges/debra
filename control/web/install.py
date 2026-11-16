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
import re
import stat
import sys
import tempfile

from server import (Backend, init_state, load_devices, valid_hosts, validate_device,
                    validate_listening_port)


PAYLOAD = ("server.py", "discovery.py", "assets/index.html", "assets/style.css", "assets/app.js")
MARKER = "# Managed by Debra web prototype\n"
HEADING = re.compile(r"\[([^]]+)\]")
EXEC_START = re.compile(r"ExecStart\s*=\s*(.*)")
UNSUPPORTED_EXEC = ("That unit's ExecStart is not in the form this installer writes "
                    "(every argument double-quoted, only \\\\, \\\", %% and $$ escaped); "
                    "restore only accepts a unit it installed")


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

    This restores the *file*. It starts nothing, so it cannot show that the
    service recovers: a unit that passes every check here still has to be
    loaded and started before anyone knows the rollback worked.
    """
    home = Path(home)
    unit = home / ".config" / "systemd" / "user" / "debra-web.service"
    source = Path(source)
    text = source.read_bytes()
    if not text.startswith(MARKER.encode()):
        # The source is a snapshot this installer wrote. An arbitrary unit may
        # use systemd syntax this decoder does not reproduce, and accepting it
        # on a best effort is how a wrong path gets validated.
        raise ValueError("Restore only accepts a unit this installer wrote")
    commands = service_commands(text)
    if not commands:
        raise ValueError("That file is not a service unit: it has no ExecStart line in [Service]")
    if len(commands) > 1:
        raise ValueError("That unit has more than one start command; Type=simple runs one, "
                         "and this installer writes one")
    problem = release_problem(home, commands)
    if problem is not None:
        raise ValueError(problem + "; install instead of restoring it")
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


def exec_arguments(value):
    """Turn one ExecStart value back into argv, strictly.

    Only the form `quoted()` writes is accepted: every argument in double
    quotes, separated by one space, and the only escapes are a doubled
    backslash, a backslash before a quote, and a doubled percent or dollar.
    Anything else is refused: single quotes, unquoted text, a C escape, a lone
    percent or dollar, a missing closing quote, a glued quote, a trailing
    space.

    This is deliberately not a systemd parser. systemd accepts far more, and a
    decoder that accepts more than it can reproduce has already restored a unit
    whose command line systemd reads as a different path: the r9 review showed
    `he\\x20home` becoming `hex20home`, so restore checked a release that exists
    while the unit started one that does not. Restore exists for the units this
    installer wrote; a hand-written unit is refused rather than half-understood.
    """
    arguments = []
    index, length = 0, len(value)
    while True:
        if index >= length or value[index] != '"':
            raise ValueError(UNSUPPORTED_EXEC)
        index += 1
        current = []
        while True:
            if index >= length:
                # An unterminated quote used to be silently closed, so a
                # truncated unit could pass every check and be published.
                raise ValueError(UNSUPPORTED_EXEC)
            char = value[index]
            if char == '"':
                index += 1
                break
            if char == "\\":
                if index + 1 >= length or value[index + 1] not in ("\\", '"'):
                    raise ValueError(UNSUPPORTED_EXEC)
                current.append(value[index + 1])
                index += 2
                continue
            if char in "%$":
                if index + 1 >= length or value[index + 1] != char:
                    raise ValueError(UNSUPPORTED_EXEC)
                current.append(char)
                index += 2
                continue
            current.append(char)
            index += 1
        arguments.append("".join(current))
        if index == length:
            return arguments
        if value[index] != " " or index + 1 >= length:
            raise ValueError(UNSUPPORTED_EXEC)
        index += 1


def service_commands(text):
    """The argv lists this installer would have written, in file order.

    Only an `ExecStart` inside `[Service]` is a start command: systemd ignores
    one in `[Unit]`, so a unit that has only that has no start command at all,
    and restoring it would report success for a rollback that starts nothing.
    An empty `ExecStart=` resets the list. `ExecStart =` with spaces around `=`
    is the same assignment, and a leading `-` means "ignore failure", not part
    of the executable path. A commented-out line never matches.
    """
    commands, section = [], None
    for raw in text.decode("utf-8", "replace").splitlines():
        line = raw.strip()
        heading = HEADING.fullmatch(line)
        if heading:
            section = heading.group(1)
            continue
        if section != "Service":
            continue
        assignment = EXEC_START.fullmatch(line)
        if not assignment:
            continue
        value = assignment.group(1)
        if not value:
            commands = []
            continue
        if value.startswith("-"):
            value = value[1:]
        commands.append(exec_arguments(value))
    return [argv for argv in commands if argv]


START_OPTIONS = ("--state-dir", "--bind", "--port", "--sink", "--auth", "--devices", "--host")


def start_command_problem(argv):
    """Why this argv is not the start command this installer writes, or None.

    `install()` writes exactly one shape: the interpreter, `-B`, the release's
    own `server.py`, `serve`, then option/value pairs. Restore used to check only
    the arguments that happened to look like paths, which made the command line
    itself unexamined: `python3 not-installed/server.py serve` names a relative
    script systemd would refuse, and `python3 -B -c 'print(1)'` names no release
    at all - and both passed, because the release check found nothing to look at
    and reported success. The entry point *is* the release, so it is required
    here rather than searched for.
    """
    if len(argv) < 4:
        return ("That unit's start command is not the one this installer writes "
                "(interpreter, -B, server.py, serve)")
    if not argv[0].startswith("/"):
        return (f"That unit's start command {argv[0]} is not an absolute path, "
                "which systemd would refuse")
    if argv[1] != "-B":
        return ("That unit's start command does not run Python with -B, which is the "
                "form this installer writes")
    if argv[3] != "serve":
        return ("That unit's start command does not run the server's serve mode, which "
                "is the form this installer writes")
    options = argv[4:]
    if len(options) % 2:
        return "That unit's start command has an option without a value"
    values = {}
    hosts = []
    for index in range(0, len(options), 2):
        name, value = options[index], options[index + 1]
        if name not in START_OPTIONS:
            return (f"That unit's start command passes {name}, which this installer "
                    "does not write")
        if name == "--host":
            hosts.append(value)
        else:
            # argparse keeps the last occurrence, so that is the one that runs.
            values[name] = value
    for name in ("--state-dir", "--devices"):
        if name in values and not values[name].startswith("/"):
            return (f"That unit's start command passes {name} {values[name]}, which is "
                    "not an absolute path and names nothing after boot")
    # The installed server refuses these before it opens a socket, so a rollback
    # that publishes them reports success for a service that cannot start. They
    # are static checks of the same argument parser, not a probe of the device.
    if not values.get("--sink", "").strip():
        return ("That unit's start command names no audio sink, which the installed "
                "server refuses: it never follows a default or a hotplugged device")
    if values.get("--auth") not in (None, "key", "none"):
        return (f"That unit's start command passes --auth {values['--auth']}, which is "
                "not a mode the installed server accepts")
    port = values.get("--port")
    if port is not None:
        if not port.isdigit():
            return f"That unit's start command passes --port {port}, which is not a number"
        try:
            validate_listening_port(int(port))
        except ValueError as exc:
            return f"That unit's start command passes --port {port}: {exc}"
    if hosts and not valid_hosts(hosts):
        return (f"That unit's start command allows {hosts[0]}, which is not a "
                "hostname:port the installed server accepts")
    return None


def release_problem(home, commands):
    """Why the releases these commands name cannot start, or None.

    Restoring a unit whose code is gone produces a service that fails
    immediately, which looks like a rollback that worked. Existing is not proof
    either: an interrupted copy leaves a release holding only part of the
    payload, and the entry point alone does not show that `discovery.py` and the
    assets beside it are there - the import fails before anything listens. The
    directory name is the digest of the payload, so changed content is
    detectable as well.

    The boundary is the tree this installer manages. The start command must be
    the shape `install()` writes, and its entry point must be `server.py` at the
    top of a release; every file inside that release must be one of the five
    payload files, reached without `..`, through real directories and as a real
    file - a link under the release would let the digested files be replaced
    without changing the name the unit is checked against.

    Every ancestor of the release tree is checked for links, not only `web/` and
    `releases/`: renaming `~/.local/share` and pointing the name at a preserved
    copy repoints every release without changing a byte inside one. This is the
    policy `install()` already applies, and the two have to agree about what the
    managed tree is or the check means nothing.
    """
    home = Path(home)
    releases = home / ".local/share/debra/web/releases"
    for ancestor in (releases, *releases.parents):
        if ancestor.is_symlink():
            return f"The managed tree {ancestor} is a link; restore cannot vouch for what it reaches"
    named = {}
    for argv in commands:
        if not argv:
            continue
        problem = start_command_problem(argv)
        if problem is not None:
            return problem
        entry = Path(argv[2])
        try:
            inside = entry.relative_to(releases)
        except ValueError:
            return f"That unit runs {argv[2]}, which is not a release this installer keeps"
        parts = inside.parts
        if ".." in parts:
            return f"That unit runs {argv[2]}, which leaves the release it names"
        if len(parts) != 2 or parts[1] != "server.py":
            return (f"That unit runs {argv[2]}, which is not the server.py of a release "
                    "this installer keeps")
        named.setdefault(parts[0], set()).add(parts[1])
    for release_id in sorted(named):
        release = releases / release_id
        script = release / "server.py"
        if release.is_symlink() or not release.is_dir():
            return f"That unit runs {script}, which is not installed"
        missing = []
        for name in PAYLOAD:
            target = release / name
            for part in (target, *target.parents):
                if part == release:
                    break
                if part.is_symlink():
                    return (f"That unit runs the release in {release}, where {part.name} "
                            "is a link; the content it is named by no longer describes "
                            "what starts")
            if not target.is_file():
                missing.append(name)
        if missing:
            return (f"That unit runs the release in {release}, which is incomplete: "
                    f"{', '.join(missing)} missing, so the service would fail to import")
        try:
            if release_digest(release) == release_id:
                continue
        except OSError:
            return f"That unit runs {script}, which cannot be read"
        return f"That unit runs {script}, whose files no longer match the content it is named by"
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
        print("Unit restored: the file was replaced atomically. Nothing was started or stopped.")
        # "Restored" is about the file. Saying more would claim the service
        # recovered, and only a start that stays up can show that.
        print("This does not prove the service starts: it checks the unit's start "
              "command and that the release it names is complete.")
        print("Next: systemctl --user daemon-reload")
        print("Then: systemctl --user start debra-web.service && "
              "systemctl --user is-active debra-web.service")
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

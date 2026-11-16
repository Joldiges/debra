"""Install the Debra first-boot setup service on a device.

Prepares files only: a content-addressed release under
`/usr/local/lib/debra/setup`, private state paths under `/var/lib/debra/setup`,
and one systemd **system** unit at `/etc/systemd/system/debra-setup.service`.
With `--enable` it also writes the `multi-user.target.wants` link, which decides
that the unit starts at the tree's next boot. It never starts, stops or restarts
a service, never calls sudo, installs no packages and changes no network
setting. Run it on the device, as root.

The same file is the service entry point, because the unit runs
`releases/<id>/install.py --serve`. That keeps the runner on the device
identical to the reviewed installer instead of generating a second program.

Why a system unit and not a user unit is explained in README.md; the short
version is that `nmcli`, `raspi-config`, port 80 and root-only keyfiles are all
system-level, and a user unit would fail at boot rather than work.

See README.md for the install command, the check, and the rollback.
"""

from __future__ import annotations

import argparse
from datetime import datetime, timezone
import hashlib
import logging
import os
from pathlib import Path
import stat
import sys
import tempfile
import threading
import time

try:  # imported as part of the package in the repository
    from . import nm as nm_module
    from . import onboarding
    from . import state as state_module
except ImportError:  # run as a script, as the installer and the unit both do
    import nm as nm_module
    import onboarding
    import state as state_module

LOGGER = logging.getLogger("debra.setup")

MARKER = "# Managed by Debra setup installer\n"
UNIT_NAME = "debra-setup.service"
# The unit is a real file beside this installer, not a string in it, so it can be
# read as a unit. The installer substitutes the five placeholders below.
TEMPLATE = UNIT_NAME
PLACEHOLDERS = ("@PYTHON@", "@RUNNER@", "@STATE@", "@CARD_NOTE@", "@SECURITY@")

# Relative to the install root. Nothing here can leave it: `under()` refuses an
# absolute path, a `..` component, and anything that resolves outside the root.
LIB = Path("usr/local/lib/debra/setup")
VAR = Path("var/lib/debra/setup")
UNIT = Path("etc/systemd/system") / UNIT_NAME
# Where `systemctl enable` puts its link. Written directly only when there is no
# running systemd to ask, which is a card being prepared from a host.
WANTS = Path("etc/systemd/system/multi-user.target.wants")
# Raspberry Pi OS Bookworm mounts the boot partition at /boot/firmware; older
# images use /boot. The note is where a person reads the setup-network password
# before any page can be loaded.
BOOT_NOTES = (Path("boot/firmware/debra-setup.txt"), Path("boot/debra-setup.txt"))

# What a release contains, as release-relative names. install.py is part of the
# payload because it is also the runner; see the module docstring.
PAYLOAD = (
    "install.py",
    "onboarding.py",
    "state.py",
    "nm.py",
    "baseline.py",
    "assets/setup.html",
    "assets/setup.js",
    TEMPLATE,
)

# NetworkManager's default address for a shared-mode access point, and the
# address the setup page has always been documented at. Port 80 so a person
# types `http://10.42.0.1/` and no port; see README.md for the tradeoff.
PORTAL_ADDRESS = "10.42.0.1"
PORTAL_PORT = onboarding.PORTAL_PORT
# A boot gives NetworkManager this long to autoconnect before `resume()` decides
# there is no uplink. Without the wait, a configured device would raise a setup
# access point on every boot while NetworkManager was still connecting.
UPLINK_WAIT_S = 30.0
UPLINK_POLL_S = 2.0
# How often the running portal asks whether the device has gone online.
PORTAL_POLL_S = 2.0
# The page stops accepting as soon as the device is online. The process waits a
# little longer for the baseline, which the join worker captures *after* it
# records the online phase; exiting immediately would kill that capture and
# leave the device with no baseline at all.
BASELINE_GRACE_S = 5.0


def quoted(value):
    """systemd argument quoting, not shell quoting; % expands even inside quotes."""
    value = str(value)
    if any(ord(char) < 32 or ord(char) == 127 for char in value):
        raise ValueError("Control characters are not allowed in service arguments")
    return '"' + value.replace("\\", "\\\\").replace('"', '\\"').replace("%", "%%").replace("$", "$$") + '"'


def under(root, relative):
    """The on-disk path of a declared relative path, or ValueError.

    `root` is the tree this installer may write in. A test passes a temporary
    directory; a device passes `/`. An absolute path, a `..` component, or a
    path that resolves out of the root is refused before anything is written.
    """
    root = Path(root)
    relative = Path(relative)
    if relative.is_absolute() or not relative.parts or ".." in relative.parts:
        raise ValueError(f"Install path must stay inside the install root: {relative}")
    path = root / relative
    resolved = path.resolve()
    if resolved != root and root not in resolved.parents:
        raise ValueError(f"Install path resolves outside the install root: {relative}")
    return path


def refuse_symlinks(root, path):
    """Refuse a symlinked path or ancestor, rather than writing through it."""
    root = Path(root)
    if root.is_symlink():
        raise ValueError(f"Refusing a symlinked install root: {root}")
    for ancestor in (Path(path), *Path(path).parents):
        if ancestor.is_symlink():
            raise ValueError(f"Refusing a symlinked install path: {ancestor}")
        if ancestor == root:
            break


def directory(root, relative, private=True):
    """Create an install directory, refusing a symlinked chain and a loose mode."""
    path = under(root, relative)
    refuse_symlinks(root, path)
    path.mkdir(parents=True, exist_ok=True, mode=0o700 if private else 0o755)
    info = path.stat()
    if info.st_uid != os.geteuid():
        raise ValueError(f"{path} must be owned by the user running this installer")
    if private and info.st_mode & 0o077:
        raise ValueError(f"{path} must be owner-only; found {oct(stat.S_IMODE(info.st_mode))}")
    return path


def target(relative):
    """Where a declared path lands on the device, whatever `--root` prepared."""
    return Path("/") / Path(relative)


def content_address(payload):
    digest = hashlib.sha256()
    for name in sorted(payload):
        digest.update(name.encode() + b"\0" + payload[name] + b"\0")
    return digest.hexdigest()


def boot_note(root):
    """The boot-partition note path, relative to the root being prepared."""
    for candidate in BOOT_NOTES:
        if (Path(root) / candidate).parent.is_dir():
            return candidate
    return BOOT_NOTES[0]


def unit_text(template, python, runner, state, note,
              security=onboarding.DEFAULT_SETUP_SECURITY):
    """Render the reviewed unit template with systemd-quoted values."""
    text = template
    for placeholder, value in zip(PLACEHOLDERS,
                                  (python, runner, state, note, security)):
        text = text.replace(placeholder, quoted(value))
    left = [placeholder for placeholder in PLACEHOLDERS if placeholder in text]
    if left:
        raise ValueError(f"Unit template still contains {', '.join(left)}")
    if not text.startswith(MARKER):
        raise ValueError("Unit template does not start with the managed marker")
    return text


def install(root, source, python=None, *, lib=LIB, var=VAR, unit=UNIT, card_note=None,
            security=onboarding.DEFAULT_SETUP_SECURITY):
    """Prepare the release, the unit and the paths. Returns what was written."""
    if security not in onboarding.SETUP_SECURITY:
        raise ValueError(f"security must be one of {', '.join(onboarding.SETUP_SECURITY)}")
    python = python or sys.executable
    if not Path(python).is_absolute():
        raise ValueError("The interpreter path must be absolute")
    root = Path(root)
    if root.is_symlink():
        raise ValueError(f"Refusing a symlinked install root: {root}")
    root = root.resolve()
    note = Path(card_note) if card_note is not None else boot_note(root)
    for value in (python, target(note)):
        quoted(value)  # Reject service-file injection before any write.

    payload = {name: (Path(source) / name).read_bytes() for name in PAYLOAD}
    release_id = content_address(payload)

    lib_dir = under(root, lib)
    state_dir = under(root, var)
    unit_path = under(root, unit)
    for path in (lib_dir, state_dir, unit_path.parent):
        refuse_symlinks(root, path)

    if unit_path.is_symlink():
        raise ValueError("Refusing a symlinked unit path")
    if unit_path.exists():
        try:
            existing = unit_path.read_text(encoding="utf-8")
        except (OSError, UnicodeDecodeError) as exc:
            raise ValueError("Existing unit cannot be read; left unchanged") from exc
        if not existing.startswith(MARKER):
            raise ValueError("Existing service is not managed by this installer; left unchanged")

    directory(root, lib, private=True)
    releases = directory(root, lib / "releases", private=True)
    release = releases / release_id
    if release.exists():
        if release.is_symlink() or not release.is_dir():
            raise ValueError("Release directory differs from expected payload; preserved without overwrite")
        for name, data in payload.items():
            stored = release / name
            if stored.is_symlink() or not stored.is_file() or stored.read_bytes() != data:
                raise ValueError("Release directory differs from expected payload; preserved without overwrite")
    else:
        # An interrupted copy leaves a private staging directory, not a poisoned
        # content-addressed release. A retry publishes a fresh complete copy.
        staging = Path(tempfile.mkdtemp(prefix=".pending-", dir=releases))
        for name, data in payload.items():
            stored = staging / name
            stored.parent.mkdir(mode=0o700, exist_ok=True)
            with stored.open("xb") as stream:
                stream.write(data)
            stored.chmod(0o600)
        staging.rename(release)

    directory(root, var, private=True)

    text = unit_text(payload[TEMPLATE].decode("utf-8"), target(python),
                     target(lib) / "releases" / release_id / "install.py",
                     target(var), target(note), security)
    directory(root, unit.parent, private=False)
    previous = None
    if unit_path.exists() and unit_path.read_text(encoding="utf-8") == text:
        return {"release": release_id, "release_path": str(release),
                "unit": str(unit_path), "state": str(state_dir),
                "card_note": str(target(note)), "security": security,
                "previous_unit": None, "changed": False}
    if unit_path.exists():
        snapshots = directory(root, lib / "previous-units", private=True)
        stamp = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%S%fZ")
        previous = snapshots / (stamp + ".service")
        with previous.open("xb") as stream:
            stream.write(unit_path.read_bytes())
        previous.chmod(0o600)
    # The previous unit (if any) is preserved before the atomic replacement.
    fd, name = tempfile.mkstemp(prefix=UNIT_NAME + ".", suffix=".pending", dir=unit_path.parent)
    candidate = Path(name)
    try:
        with os.fdopen(fd, "w", encoding="utf-8") as stream:
            stream.write(text)
        candidate.chmod(0o644)
        os.replace(candidate, unit_path)
    except BaseException:
        # A failed install must not leave a candidate beside the real unit: the
        # next run would have to explain an unexplained file there.
        try:
            candidate.unlink()
        except OSError:
            pass
        raise
    return {"release": release_id, "release_path": str(release),
            "unit": str(unit_path), "state": str(state_dir),
            "card_note": str(target(note)), "security": security,
            "previous_unit": str(previous) if previous else None, "changed": True}


def enable(root, *, unit=UNIT, wants=WANTS):
    """Link the installed unit into `multi-user.target.wants`.

    `systemctl enable` is the right command on a running device: it also asks
    the daemon to reload. This exists for the other case, a card prepared from
    a host, where there is no running systemd to ask. It is what makes the
    service start on the very first boot, which is the only way the first-boot
    journey is ever tried before the person has a console.

    It refuses to link a unit that is not there, and refuses to touch anything
    in the wants directory that is not the link it would have made.
    """
    root = Path(root).resolve()
    unit_path = under(root, unit)
    if unit_path.is_symlink() or not unit_path.is_file():
        raise ValueError("Enable needs a unit this installer wrote; nothing was linked")
    try:
        if not unit_path.read_text(encoding="utf-8").startswith(MARKER):
            raise ValueError("Enable needs a unit this installer wrote; nothing was linked")
    except (OSError, UnicodeDecodeError) as exc:
        raise ValueError("The installed unit cannot be read; nothing was linked") from exc
    wants_dir = under(root, wants)
    refuse_symlinks(root, wants_dir)
    link = wants_dir / UNIT_NAME
    if link.is_symlink():
        target = os.readlink(link)
        # `systemctl enable` writes an absolute target for a unit under
        # /etc/systemd/system; the installer writes the relative one. Both name
        # the same file in a prepared tree, so the destination is compared, not
        # the text.
        #
        # The comparison follows symlinks, because the kernel does. `normpath`
        # alone removes `jump/..` without looking at `jump`, so a link spelled
        # `../jump/../debra-setup.service` was accepted while `jump` pointed at
        # another directory and the link actually resolved to a foreign unit.
        if os.path.isabs(target):
            # An absolute target names a path on the device, which this tree is
            # rooted at. A path that already carries the preparing host's mount
            # point is refused: it names this unit only on the host, and nothing
            # at all after boot.
            if os.path.normpath(target) != "/" + os.path.normpath(unit):
                raise ValueError(f"{link} names {target}, which is not this unit on the "
                                 "device; left unchanged")
            destination = os.path.realpath(str(root / target.lstrip("/")))
        else:
            destination = os.path.realpath(os.path.join(str(wants_dir), target))
        if destination == os.path.realpath(str(unit_path)):
            return str(link)
        raise ValueError(f"{link} is a different link; left unchanged")
    if link.exists():
        raise ValueError(f"{link} exists and is not a link; left unchanged")
    directory(root, wants, private=False)
    os.symlink(os.path.join("..", UNIT_NAME), link)
    return str(link)


def restore(root, backup, *, lib=LIB, unit=UNIT):
    """Put a retained unit back, atomically. Prepares files only.

    Rollback is a code path rather than a documented `cp` because a copy
    interrupted partway leaves a truncated unit that cannot start.
    """
    root = Path(root).resolve()
    lib_dir = under(root, lib)
    unit_path = under(root, unit)
    refuse_symlinks(root, unit_path)
    backup = Path(backup)
    if backup.is_symlink() or not backup.is_file():
        raise ValueError("Rollback needs a retained unit file")
    snapshots = (lib_dir / "previous-units").resolve()
    try:
        backup.resolve().relative_to(snapshots)
    except ValueError as exc:
        raise ValueError("Rollback must use a unit retained under previous-units") from exc
    text = backup.read_text(encoding="utf-8")
    if not text.startswith(MARKER):
        raise ValueError("That file is not a unit this installer wrote")
    directory(root, unit.parent, private=False)
    fd, name = tempfile.mkstemp(prefix=UNIT_NAME + ".", suffix=".pending", dir=unit_path.parent)
    candidate = Path(name)
    try:
        with os.fdopen(fd, "w", encoding="utf-8") as stream:
            stream.write(text)
        candidate.chmod(0o644)
        os.replace(candidate, unit_path)
    except BaseException:
        try:
            candidate.unlink()
        except OSError:
            pass
        raise
    return {"unit": str(unit_path), "restored": str(backup.resolve())}


# -- the service ----------------------------------------------------------


def wait_for_uplink(network, timeout=UPLINK_WAIT_S, interval=UPLINK_POLL_S, sleep=time.sleep):
    """Give NetworkManager a bounded chance to autoconnect before deciding.

    A boot starts this unit as soon as NetworkManager is up, which is not the
    same moment as "connected". Asking immediately would find no uplink and
    raise a setup access point on a device that was about to join its own
    network, so the question is asked again for a bounded time.
    """
    deadline = time.monotonic() + timeout
    while True:
        try:
            active = network.active()
        except nm_module.NmError as exc:
            LOGGER.warning("NetworkManager is not answering: %s", exc)
            return None
        if active and active["routable"] and active.get("has_route", True):
            return active
        if time.monotonic() >= deadline:
            return None
        sleep(interval)


def hotspot_address(network, status):
    """The address the access point actually got, or the documented default.

    NetworkManager's shared mode normally assigns 10.42.0.1, but nothing
    guarantees it. Binding the page to a guessed address would fail on a
    different subnet and leave the person with a setup network and no page, so
    the real address is asked for first.
    """
    hotspot = status.get("hotspot") or {}
    try:
        found = network.device_address(hotspot.get("interface"))
    except (AttributeError, nm_module.NmError) as exc:
        LOGGER.warning("Could not read the setup network address: %s", exc)
        found = None
    return found or PORTAL_ADDRESS


def serve(state_dir, card_note=None, network=None, address=None,
          capture_root="/", uplink_wait=UPLINK_WAIT_S, poll=PORTAL_POLL_S,
          grace=BASELINE_GRACE_S, security=onboarding.DEFAULT_SETUP_SECURITY):
    """One boot of the setup service. Returns the process exit code.

    Online: no page and no access point are started. The boot is still not a
    no-op — `resume()` re-applies the device name and checks or captures the
    baseline — and then the process ends. Otherwise the access point is
    raised and the page is served until the device is online, at which point the
    listening socket is closed rather than left open.
    """
    state_dir = Path(state_dir)
    state_dir.mkdir(parents=True, exist_ok=True, mode=0o700)
    state_path = state_dir / "setup.json"
    network = network or nm_module.Nmcli()
    # No keyfile directory is passed: the Wi-Fi profile is written where
    # NetworkManager's keyfile plugin reads it, which is the only place a
    # profile survives a reboot. A Debra-owned staging directory was configured
    # here and never used, and a profile outside the plugin's directories is
    # not one NetworkManager will load again.
    onboarder = onboarding.Onboarder(
        network, state_path, state_dir / "baseline", root=capture_root,
        card_note_path=card_note, security=security)
    if onboarder.security != security:
        # The unit's argument and the mode the device carries disagree. The
        # device wins, and that override is otherwise invisible: the installer's
        # warning is about the flag it wrote, so a device that comes up
        # protected under `--setup-security none` - because the page chose
        # `wpa`, or because an upgrade carried that mode forward - would have
        # exactly one line in the journal saying the opposite.
        LOGGER.warning("setup network mode %s was set on the device, not by "
                       "--setup-security %s", onboarder.security, security)
    if onboarder.security == "none":
        # Deliberately open, and said out loud every boot rather than once at
        # install time: the journal is where an open setup network is noticed.
        # The mode reported is the one the device will use, which after a change
        # on the page is the stored one rather than the unit's argument - so the
        # message names where it came from instead of always blaming the flag.
        # An adopted record is always `wpa`, so it cannot reach this line.
        LOGGER.warning("setup network is OPEN: mode none, from %s",
                       "the setup page" if onboarder.security_source == "page"
                       else "--setup-security")

    wait_for_uplink(network, uplink_wait)
    status = onboarder.resume()
    # The phase and the device name are the only status fields logged. The
    # setup-network password is not a status field at all, so it cannot reach
    # the journal from here.
    #
    # Read with `.get`: `resume` returns the worker-shaped fallback when the
    # access point is up but the state cannot be read, and that dict has no
    # hostname or hotspot. Indexing it turned a missing key into a traceback
    # from the boot path - the one failure the handlers and workers exist to
    # avoid - instead of a sentence and exit code 1.
    phase = status.get("phase")
    LOGGER.info("setup phase %s, device name %s", phase, status.get("hostname"))
    if phase == "online":
        return 0
    if not status.get("hotspot"):
        LOGGER.error("The setup access point is not up: %s",
                     status.get("last_error") or "no reason was given")
        return 1

    if address is None:
        address = (hotspot_address(network, status), PORTAL_PORT)
    try:
        server = onboarding.serve(onboarder, address=address)
    except OSError as exc:
        # The access point is already up. Failing to bind leaves a setup
        # network with no page, which a beginner cannot diagnose or escape, so
        # take the access point back down and record why.
        LOGGER.error("Setup page could not listen on %s: %s",
                     address[0], exc.__class__.__name__)
        try:
            network.stop_hotspot()
        except (AttributeError, nm_module.NmError):
            pass
        try:
            data = state_module.read(state_path)
            data.update(phase="failed", hotspot=None,
                        last_error="The setup page could not start on this device")
            state_module.write(state_path, data)
        except (OSError, ValueError):
            pass
        return 1
    # The note and the status were written from the address the radio reported
    # when the access point came up. This is the address that is actually
    # listening, and it is the one a person must type.
    onboarder.announce_portal(address[0])
    LOGGER.info("setup page listening on http://%s/", server.host)
    stop = threading.Event()

    def watch():
        while not stop.wait(poll):
            try:
                if state_module.read(state_path)["phase"] == "online":
                    break
            except (OSError, ValueError) as exc:
                LOGGER.warning("Setup state could not be read: %s", exc)
        server.shutdown()

    watcher = threading.Thread(target=watch, daemon=True, name="debra-setup-watch")
    watcher.start()
    try:
        server.serve_forever()
    finally:
        stop.set()
        watcher.join(timeout=poll * 2 + 1)
        server.server_close()
    # The socket is closed. Give the join worker the time to finish the first
    # baseline before the process ends.
    try:
        data = state_module.read(state_path)
    except (OSError, ValueError):
        data = None
    if data and data["phase"] == "online" and not data["baseline"]:
        deadline = time.monotonic() + grace
        while time.monotonic() < deadline:
            if state_module.read(state_path)["baseline"]:
                break
            time.sleep(0.2)
        else:
            LOGGER.warning("No baseline was recorded before the service stopped")
    LOGGER.info("setup page stopped")
    return 0


def main(argv=None):
    parser = argparse.ArgumentParser(
        description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--serve", action="store_true",
                        help="run the setup service for one boot (the unit does this)")
    parser.add_argument("--root", type=Path, default=Path("/"),
                        help="tree to prepare; the default is the running system")
    parser.add_argument("--source", type=Path, default=Path(__file__).resolve().parent,
                        help="directory holding the reviewed payload")
    parser.add_argument("--python", default=sys.executable,
                        help="interpreter the unit will run")
    parser.add_argument("--restore", type=Path, metavar="UNIT",
                        help="put a retained previous unit back, atomically")
    parser.add_argument("--enable", action="store_true",
                        help="also link the unit into multi-user.target.wants, for a "
                             "tree prepared from a host that has no running systemd "
                             "(a card); on a device use systemctl enable")
    parser.add_argument("--state-dir", type=Path, default=target(VAR),
                        help="--serve: where the setup state lives")
    parser.add_argument("--card-note", type=Path, default=None,
                        help="--serve: the boot-partition note to write")
    parser.add_argument("--capture-root", type=Path, default=Path("/"),
                        help="--serve: root the baseline reads from")
    parser.add_argument("--setup-security", choices=list(onboarding.SETUP_SECURITY),
                        default=onboarding.DEFAULT_SETUP_SECURITY,
                        help="none: open setup network, no password (the current "
                             "default, a development-phase choice); wpa: a random "
                             "per-device password on the card note")
    args = parser.parse_args(argv)

    if args.serve:
        logging.basicConfig(level=logging.INFO, format="%(levelname)s %(message)s")
        try:
            return serve(args.state_dir, args.card_note, capture_root=args.capture_root,
                         security=args.setup_security)
        except nm_module.NmError as exc:
            # Already classified by the adapter, so it is safe and useful.
            LOGGER.error("The setup service stopped: %s", exc)
            return 1
        except (OSError, ValueError) as exc:
            # The class, not the text: an OSError carries the path it failed on.
            LOGGER.error("The setup service stopped: %s", exc.__class__.__name__)
            return 1

    if args.root.resolve() == Path("/") and os.geteuid() != 0:
        parser.error("Run as root on the device: this writes a system unit, "
                     "/var/lib/debra and the boot-partition note")
    try:
        if args.restore:
            result = restore(args.root, args.restore)
            if args.enable:
                result["enabled"] = enable(args.root)
        else:
            result = install(args.root, args.source, args.python,
                             security=args.setup_security)
            # Enabling comes after the unit exists, and a failure here must not
            # be reported as a failed install of files that are in place.
            if args.enable:
                result["enabled"] = enable(args.root)
    except (OSError, ValueError) as exc:
        parser.error(str(exc))
    for name, value in result.items():
        print(f"{name}: {value}")
    print("Files prepared; no service started and no network setting changed.")
    if result.get("security") == "none":
        print("WARNING: the setup network will be OPEN. Development build only.")
    if args.enable:
        if args.root.resolve() == Path("/"):
            print("Next: systemctl daemon-reload")
            print("The unit is enabled and starts at the next boot; nothing was started now.")
        else:
            print("The unit is enabled in the prepared tree: it starts at that "
                  "tree's next boot. Nothing was started now.")
        return 0
    if args.restore:
        print("Next: systemctl daemon-reload")
        print("Then: systemctl restart debra-setup.service")
        return 0
    print("Next: systemctl daemon-reload")
    print("Then: systemctl enable --now debra-setup.service")
    return 0


if __name__ == "__main__":
    sys.exit(main())

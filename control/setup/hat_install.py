#!/usr/bin/env python3
"""Change the audio HAT in the boot configuration, as root, for one board at a time.

This is the only program in Debra that writes `/boot/firmware/config.txt`, and it
exists because the web page must not have root and a person must not need a shell.
It takes **no arguments**: the request is one JSON object on standard input, and
the answer is one JSON object on standard output.

It is started by a socket, not by `sudo`. The web service runs with
`NoNewPrivileges=yes`, so a setuid `sudo` cannot escalate from it at all — and
removing that line to make `sudo` work would trade a real hardening measure for a
convenience. `debra-hat.socket` listens on a Unix socket that only the web
account's group can open; a connection starts one instance of this program with
the connection as its standard input and output. No setuid binary is involved and
the web service keeps its hardening.

    {"verb": "install", "board": "respeaker-2mic-hat-v1"}
    {"verb": "remove"}
    {"verb": "reboot"}

Three properties are the whole reason it is separate from the server:

* **The board is validated here, not by the caller.** The table in `hats.py` is
  the only list of overlays this program will write, so a compromised server can
  ask for a board it knows about and nothing else. An unknown id is refused, not
  guessed at.
* **Every write is reversible without this program.** `config.txt` is copied
  beside itself before it is touched, and the copy is never overwritten. The
  edit is written to a temporary file and renamed into place, so a power cut
  leaves the old file or the new one, never half of either. After writing, the
  file is read back and checked; a file that does not say what it should is
  restored from the backup before this program reports anything.
* **It never reboots as a side effect.** `install` writes a boot configuration
  that takes effect at the next boot and stops there. Restarting is a separate
  verb, asked for separately, by a person who was told what it does.

Nothing here decides whether a board is a good idea; it decides whether the
write is exactly the write that was asked for.
"""

import importlib.util
import json
import os
from pathlib import Path
import platform
import re
import shutil
import subprocess
import sys
import syslog
import time

# Where the installer puts the shared table. The repository copy is the fallback
# so this file can be read and tested where it lives.
TABLE_PATHS = (Path("/usr/local/lib/debra/hats.py"),
               Path(__file__).resolve().parent.parent / "web" / "hats.py")

CONFIG_CANDIDATES = ("boot/firmware/config.txt", "boot/config.txt")

# A written line does nothing until the next boot. Recording *which* boot it was
# written in is the difference between "restart to apply it" and "it has already
# been restarted and the thing still is not there", and only the second one tells
# a person the board is wrong rather than the restart missing.
STATE_FILE = "var/lib/debra/hat-change.json"
BOOT_ID = "proc/sys/kernel/random/boot_id"

# `dtoverlay=name` or `dtoverlay=name,param=value`; the name is what identifies
# a managed overlay, the rest belongs to the overlay.
OVERLAY_LINE = re.compile(r"^\s*dtoverlay\s*=\s*([A-Za-z0-9_\-]+)")
I2C_PARAM = re.compile(r"^\s*dtparam\s*=\s*i2c_arm\s*=\s*on\b")
I2C_PARAM_COMMENTED = re.compile(r"^\s*#\s*dtparam\s*=\s*i2c_arm\s*=\s*on\b")
SECTION_LINE = re.compile(r"^\s*\[[^\]]+\]\s*$")
# Only these characters may appear in a backup name, so a board id can never
# become a path.
BACKUP_SUFFIX = re.compile(r"^[A-Za-z0-9._-]+$")


class Refused(Exception):
    """A request this program will not carry out, with a reason a person can read."""


def table_file():
    """Where the shared board table is, in the installed copy or the repository."""
    for path in TABLE_PATHS:
        if path.is_file():
            return path
    raise Refused("The board table is missing, so this helper cannot tell which "
                  "overlays it is allowed to write. Reinstall it.")


def load_table():
    """Import the shared board table from wherever this copy of the helper lives."""
    path = table_file()
    spec = importlib.util.spec_from_file_location("debra_hats", path)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def config_path(root=Path("/")):
    """The boot configuration this image actually uses."""
    for relative in CONFIG_CANDIDATES:
        candidate = Path(root) / relative
        if candidate.is_file():
            return candidate
    raise Refused("No boot configuration was found at /boot/firmware/config.txt "
                  "or /boot/config.txt, so there is nothing safe to change.")


def overlay_file(config, name):
    """The compiled overlay this board needs, or None if the image lacks it."""
    return config.parent / "overlays" / (name + ".dtbo")


def module_present(name, root=Path("/"), release=None):
    """Whether a kernel module is on this image, built in or loadable.

    A `.ko` file and a `modules.builtin` entry are both evidence the driver
    exists; neither is evidence it binds. Not finding either is the only case
    that is refused here.
    """
    release = release or platform.release()
    modules = Path(root) / "lib" / "modules" / release
    codecs = modules / "kernel" / "sound" / "soc" / "codecs"
    if codecs.is_dir() and any(codecs.glob(name + ".ko*")):
        return True
    builtin = modules / "modules.builtin"
    try:
        text = builtin.read_text(errors="replace")
    except OSError:
        return False
    return any(line.rstrip().endswith("/" + name + ".ko") for line in text.splitlines())


def _overlay_name(line):
    match = OVERLAY_LINE.match(line)
    return match.group(1) if match else None


def plan(text, overlay, needs_i2c, managed):
    """The new config text, and what changed.

    Every line that is not a managed overlay survives byte for byte, including
    comments, blank lines and overlays this program does not own. That matters:
    config.txt is the file that decides whether the device boots at all.
    """
    lines = text.splitlines(keepends=True)
    kept, dropped = [], []
    for line in lines:
        name = _overlay_name(line)
        if name is not None and name in managed:
            dropped.append(name)
        else:
            kept.append(line)

    # A file whose last line has no newline would otherwise glue the next
    # setting onto it: `dtparam=audio=on` + `dtparam=i2c_arm=on` becomes one
    # nonsense line. Fixed before anything is appended, not after.
    if kept and not kept[-1].endswith("\n"):
        kept[-1] += "\n"

    if needs_i2c:
        # An explicit line is what the measured device used. A commented one is
        # uncommented rather than duplicated, so the file does not grow a second
        # copy of the same setting that a later edit could contradict.
        if not any(I2C_PARAM.match(line) for line in kept):
            for index, line in enumerate(kept):
                if I2C_PARAM_COMMENTED.match(line):
                    kept[index] = "dtparam=i2c_arm=on\n"
                    break
            else:
                kept.append("dtparam=i2c_arm=on\n")

    added = []
    if overlay is not None:
        # The stock file ends with `[all]`, but a hand-edited one may end inside
        # a `[pi4]`-style section, where a bare line would apply to one model
        # only. Saying `[all]` first makes the new line mean what it says.
        if any(SECTION_LINE.match(line) for line in kept):
            last_section = [line for line in kept if SECTION_LINE.match(line)][-1]
            if last_section.strip() != "[all]":
                added.append("[all]\n")
        added.append("dtoverlay=%s\n" % overlay)

    new = "".join(kept + added)
    return new, {"dropped": dropped, "added": added}


def verify(text, overlay, needs_i2c, managed):
    """Whether `text` says exactly what was asked for. Raises Refused if not."""
    present = [_overlay_name(line) for line in text.splitlines()]
    present = [name for name in present if name in managed]
    if overlay is None:
        if present:
            raise Refused("The new configuration still names an audio overlay (%s)."
                          % ", ".join(sorted(set(present))))
        return
    if present != [overlay]:
        raise Refused("The new configuration names %s where %s was asked for."
                      % (", ".join(present) or "no overlay", overlay))
    if needs_i2c and not any(I2C_PARAM.match(line) for line in text.splitlines()):
        raise Refused("The new configuration does not enable I2C, which this board needs.")


def backup_name(config):
    """A name that is not already taken, so no backup is ever overwritten."""
    stamp = time.strftime("%Y%m%d-%H%M%S")
    candidate = "%s.debra-%s" % (config.name, stamp)
    suffix = 1
    while (config.parent / candidate).exists():
        suffix += 1
        candidate = "%s.debra-%s-%d" % (config.name, stamp, suffix)
    return config.parent / candidate


def boot_id(root=Path("/")):
    """This boot's identifier, or None where it cannot be read (a test tree)."""
    try:
        return (Path(root) / BOOT_ID).read_text().strip() or None
    except OSError:
        return None


def remember(root, overlay):
    """Record the overlay this program wrote and the boot it wrote it in.

    Best effort and deliberately quiet: the boot configuration has already been
    written and checked by the time this runs, so a state file that cannot be
    saved must not turn a successful change into a reported failure. The page
    treats a missing record as "cannot say", which is true.
    """
    path = Path(root) / STATE_FILE
    record = {"overlay": overlay, "boot_id": boot_id(root),
              "written": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime())}
    try:
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(json.dumps(record, sort_keys=True) + "\n")
        os.chmod(path, 0o644)
    except OSError:
        return None
    return record


def change(root=Path("/")):
    """The last recorded change, or None when there is no readable record."""
    try:
        record = json.loads((Path(root) / STATE_FILE).read_text())
    except (OSError, ValueError):
        return None
    if not isinstance(record, dict) or "boot_id" not in record:
        return None
    return record


def write_config(config, text):
    """Replace the file atomically, keeping its mode, after backing it up."""
    backup = backup_name(config)
    shutil.copy2(config, backup)
    mode = config.stat().st_mode & 0o777
    temporary = config.parent / (config.name + ".debra-new-%d" % os.getpid())
    try:
        with open(temporary, "w") as handle:
            handle.write(text)
            handle.flush()
            os.fsync(handle.fileno())
        os.chmod(temporary, mode)
        os.replace(temporary, config)
    except OSError:
        if temporary.exists():
            temporary.unlink()
        raise
    return backup


def install(board_id, root=Path("/"), release=None, dry_run=False):
    """Write one board's overlay into the boot configuration. Never reboots."""
    table = load_table()
    entry = table.option(board_id)
    if entry is None:
        raise Refused("%r is not a board this helper knows, so it will not write "
                      "anything for it." % board_id)
    config = config_path(root)
    if not os.access(config, os.R_OK | os.W_OK):
        raise Refused("%s is not writable, so the boot configuration cannot be "
                      "changed." % config)

    overlay = entry["overlay"]
    if overlay is not None:
        compiled = overlay_file(config, overlay)
        if not compiled.is_file():
            raise Refused("This image has no %s overlay, which is what %s needs. "
                          "Nothing was changed." % (overlay, entry["label"]))
        missing = [name for name in entry["modules"]
                   if not module_present(name, root=root, release=release)]
        if missing:
            raise Refused("This image has no %s kernel module, so the overlay "
                          "would load and bind nothing. Nothing was changed."
                          % ", ".join(missing))

    original = config.read_text()
    text, changes = plan(original, overlay, entry["needs_i2c"], table.MANAGED_OVERLAYS)
    verify(text, overlay, entry["needs_i2c"], table.MANAGED_OVERLAYS)
    if text == original:
        return {"ok": True, "changed": False, "config": str(config),
                "note": "The boot configuration already says this; nothing was written."}
    if dry_run:
        return {"ok": True, "changed": True, "config": str(config),
                "note": "Dry run: nothing was written.", "would_write": text}

    backup = write_config(config, text)
    try:
        verify(config.read_text(), overlay, entry["needs_i2c"], table.MANAGED_OVERLAYS)
    except Refused as exc:
        # The file does not say what it should. Put the old one back before
        # saying anything, so a failure never leaves a half-changed boot.
        shutil.copy2(backup, config)
        raise Refused("%s The previous configuration was restored from %s."
                      % (exc, backup.name)) from exc
    remember(root, overlay)
    return {"ok": True, "changed": True, "config": str(config),
            "backup": str(backup), "overlay": overlay,
            "dropped": changes["dropped"],
            "note": "Written. It applies after the next restart; the running "
                    "system is unchanged."}


def remove(root=Path("/")):
    """Take every managed audio-HAT overlay out of the boot configuration."""
    table = load_table()
    config = config_path(root)
    if not os.access(config, os.R_OK | os.W_OK):
        raise Refused("%s is not writable, so the boot configuration cannot be "
                      "changed." % config)
    original = config.read_text()
    text, changes = plan(original, None, False, table.MANAGED_OVERLAYS)
    verify(text, None, False, table.MANAGED_OVERLAYS)
    if text == original:
        return {"ok": True, "changed": False, "config": str(config),
                "note": "No audio-HAT overlay this page manages was configured."}
    backup = write_config(config, text)
    try:
        verify(config.read_text(), None, False, table.MANAGED_OVERLAYS)
    except Refused as exc:
        shutil.copy2(backup, config)
        raise Refused("%s The previous configuration was restored from %s."
                      % (exc, backup.name)) from exc
    remember(root, None)
    return {"ok": True, "changed": True, "config": str(config), "backup": str(backup),
            "dropped": changes["dropped"],
            "note": "Removed. It applies after the next restart; the running "
                    "system is unchanged."}


def reboot(launch=None, delay=2):
    """Restart the device after a short delay, so this answer gets out first."""
    launch = launch or _launch_reboot
    launch(delay)
    return {"ok": True, "rebooting": True,
            "note": "The device is restarting. The page will come back on its own."}


def _launch_reboot(delay):
    """Start the reboot in a transient unit, so it survives this process exiting."""
    command = ["systemd-run", "--quiet", "--collect", "--unit=debra-reboot",
               "--on-active=%d" % delay, "systemctl", "reboot"]
    if shutil.which("systemd-run"):
        result = subprocess.run(command, capture_output=True, timeout=10, check=False)
        if result.returncode == 0:
            return
    # No systemd-run: detach and let the child outlive us. Still delayed, so the
    # JSON answer reaches the page before the network goes away.
    subprocess.Popen(["sh", "-c", "sleep %d; systemctl reboot" % delay],
                     stdin=subprocess.DEVNULL, stdout=subprocess.DEVNULL,
                     stderr=subprocess.DEVNULL, start_new_session=True)


VERBS = {"install", "remove", "reboot"}

# Where enrollment puts things. Fixed paths, because the socket unit names one
# exact program and the helper loads its table from one exact place.
INSTALLED_HELPER = "usr/local/sbin/debra-hat-install"
INSTALLED_TABLE = "usr/local/lib/debra/hats.py"
INSTALLED_SOCKET = "etc/systemd/system/debra-hat.socket"
INSTALLED_SERVICE = "etc/systemd/system/debra-hat@.service"
# The units are real files beside this one, so they can be read as units. The
# installer substitutes the one placeholder.
SOCKET_UNIT = Path(__file__).resolve().parent / "debra-hat.socket"
SERVICE_UNIT = Path(__file__).resolve().parent / "debra-hat@.service"
SOCKET_PATH = "/run/debra-hat/control.sock"
# An earlier, unreleased enrolment used a passwordless sudo rule instead of the
# socket. That rule is not needed by this one, and leaving it would keep a root
# grant on the device for a program the page no longer calls that way. Only a
# file carrying this exact first line is ever removed.
LEGACY_SUDOERS = "etc/sudoers.d/debra-hat"
LEGACY_MARKER = "# Installed by Debra's audio-HAT helper."


def enroll(root=Path("/"), user=None, group=None, source=None, runner=None,
           activate=True):
    """Install this helper and the socket that starts it, as root.

    Run once, by the device's owner, with a password. It writes four files, tells
    systemd about them and starts the socket. It does not touch the boot
    configuration: installing a driver is still a separate, deliberate press.
    """
    user = user or os.environ.get("SUDO_USER") or ""
    if not user or user == "root":
        raise Refused("Run this with sudo as the account that runs the web page, "
                      "not as root directly: the socket is opened for that "
                      "account's group.")
    if not re.fullmatch(r"[A-Za-z_][A-Za-z0-9_.-]*", user):
        raise Refused("%r is not a user name this will open a socket for." % user)
    group = group or user
    if not re.fullmatch(r"[A-Za-z_][A-Za-z0-9_.-]*", group):
        raise Refused("%r is not a group name this will open a socket for." % group)
    runner = runner or subprocess.run
    source = Path(source or __file__).resolve()
    if not source.is_file():
        raise Refused("Cannot find this helper's own file to install.")
    table = table_file()
    for unit in (SOCKET_UNIT, SERVICE_UNIT):
        if not unit.is_file():
            raise Refused("%s is missing, so the socket cannot be installed." % unit.name)

    helper_path = Path(root) / INSTALLED_HELPER
    table_path = Path(root) / INSTALLED_TABLE
    socket_unit = Path(root) / INSTALLED_SOCKET
    service_unit = Path(root) / INSTALLED_SERVICE
    for directory in (helper_path.parent, table_path.parent,
                      socket_unit.parent):
        directory.mkdir(parents=True, exist_ok=True)

    written = []
    contents = (
        (helper_path, source.read_bytes(), 0o755),
        (table_path, table.read_bytes(), 0o644),
        (socket_unit, SOCKET_UNIT.read_text().replace("@GROUP@", group).encode(), 0o644),
        (service_unit, SERVICE_UNIT.read_bytes(), 0o644),
    )
    for target, data, mode in contents:
        if not target.is_file() or target.read_bytes() != data:
            temporary = target.with_name(target.name + ".pending")
            temporary.write_bytes(data)
            os.chmod(temporary, mode)
            os.replace(temporary, target)
            written.append(str(target))
        os.chmod(target, mode)
        if os.geteuid() == 0:
            os.chown(target, 0, 0)

    # The unreleased sudo-based enrolment is retired here rather than left
    # behind. A file that does not carry our own first line is not ours and is
    # not touched.
    legacy = Path(root) / LEGACY_SUDOERS
    retired = []
    if legacy.is_file():
        try:
            first = legacy.read_text(errors="replace").splitlines()[:1]
        except OSError:
            first = []
        if first == [LEGACY_MARKER]:
            legacy.unlink()
            retired.append(str(legacy))

    answer = {"ok": True, "changed": bool(written) or bool(retired), "installed": written,
              "retired": retired,
              "user": user, "group": group,
              "helper": str(helper_path), "table": str(table_path),
              "socket": SOCKET_PATH,
              "socket_unit": str(socket_unit), "service_unit": str(service_unit)}
    if not activate:
        answer["note"] = "Files written; systemd was not told about them."
        return answer
    # Enabling the socket is what makes the page able to ask. `daemon-reload`
    # first, because a new unit is invisible to systemd until it has re-read.
    for argv in (["systemctl", "daemon-reload"],
                 ["systemctl", "enable", "--now", "debra-hat.socket"]):
        result = runner(argv, capture_output=True, text=True, timeout=60, check=False)
        if result.returncode != 0:
            raise Refused("systemd refused %r, so the page cannot ask yet: %s"
                          % (" ".join(argv), (result.stderr or "").strip()[:200]))
    answer["note"] = ("The page may now ask this helper to change the boot "
                      "configuration. Restarting the web service is not needed.")
    return answer


def run(request, root=Path("/"), release=None, launch=None):
    """Carry out one parsed request. Raises Refused rather than guessing."""
    if not isinstance(request, dict):
        raise Refused("The request must be one JSON object.")
    verb = request.get("verb")
    if verb not in VERBS:
        raise Refused("%r is not one of %s." % (verb, ", ".join(sorted(VERBS))))
    unknown = set(request) - {"verb", "board"}
    if unknown:
        raise Refused("Unexpected field(s): %s." % ", ".join(sorted(unknown)))
    if verb == "install":
        board = request.get("board")
        if not isinstance(board, str):
            raise Refused("install needs a board id.")
        return install(board, root=root, release=release)
    if verb == "remove":
        return remove(root=root)
    return reboot(launch=launch)


def main(stdin=None, stdout=None, argv=None):
    stdin = sys.stdin if stdin is None else stdin
    stdout = sys.stdout if stdout is None else stdout
    argv = sys.argv[1:] if argv is None else argv
    if argv == ["--enroll"]:
        # The one argument this program accepts, and it is not the passwordless
        # path: it is run by a person with a password, once, and it is what
        # creates the no-argument rule below.
        try:
            if os.geteuid() != 0:
                raise Refused("Enrolling needs root: run it with sudo.")
            answer = enroll()
        except Refused as exc:
            json.dump({"ok": False, "reason": str(exc)}, stdout)
            stdout.write("\n")
            return 1
        json.dump(answer, stdout, indent=2)
        stdout.write("\n")
        return 0
    if argv:
        # The socket starts this program with no arguments. A call with arguments
        # is not the call that was reviewed, so it is refused outright.
        json.dump({"ok": False, "reason": "This helper takes no arguments."}, stdout)
        stdout.write("\n")
        return 2
    try:
        request = json.load(stdin)
    except (ValueError, OSError):
        json.dump({"ok": False, "reason": "The request was not one JSON object."}, stdout)
        stdout.write("\n")
        return 2
    try:
        if os.geteuid() != 0:
            raise Refused("This helper must run as root; nothing was changed.")
        answer = run(request)
    except Refused as exc:
        syslog.syslog(syslog.LOG_WARNING, "debra-hat-install refused: %s" % exc)
        json.dump({"ok": False, "reason": str(exc)}, stdout)
        stdout.write("\n")
        return 0
    syslog.syslog(syslog.LOG_NOTICE, "debra-hat-install %s: %s"
                  % (request.get("verb"), json.dumps(answer)))
    json.dump(answer, stdout)
    stdout.write("\n")
    return 0


if __name__ == "__main__":
    sys.exit(main())

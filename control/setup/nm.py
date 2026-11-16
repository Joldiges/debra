"""NetworkManager, behind a small interface the onboarding logic can be tested against.

Everything here is a thin, explicit wrapper over `nmcli`. The point is not to
hide NetworkManager but to keep the decisions (is this a success? should the
access point come back?) in one testable place instead of inside shell strings.
"""

from __future__ import annotations

import ipaddress
import logging
import os
import re
import secrets
import subprocess
import tempfile
import uuid
from pathlib import Path


LOGGER = logging.getLogger("debra.setup.nm")

# Where the keyfile plugin keeps profiles it will read again after a reboot.
# A profile anywhere else is not persistent, however successfully it loads.
PROFILES_DIR = "/etc/NetworkManager/system-connections"

# The one connection name the setup access point uses. Fixed rather than
# generated, so a stale setup profile is always found and removed instead of
# piling up under a new name each attempt.
SETUP_CONNECTION = "debra-setup"

# The access point's profile identity. NetworkManager matches a profile by its
# UUID, so a fixed one is what lets `connection reload` update the profile the
# device already has instead of adding a second setup network beside it.
# Derived rather than random so a re-install cannot produce two identities for
# the same access point; it only has to be unique among this device's profiles.
HOTSPOT_UUID = str(uuid.uuid5(uuid.NAMESPACE_DNS, "setup-access-point.debra.invalid"))

# The state `nmcli device show` reports for an activated device.
NM_ACTIVATED = 100

# The loopback alias a Debian install gives the machine's own name. `hostnamectl`
# does not touch it, and nothing rewrites it until the next boot, so a device
# renamed while it is running kept answering `sudo` with "unable to resolve
# host" and `hostname -f` with an error, for the rest of that boot.
HOSTS_PATH = Path("/etc/hosts")
HOSTS_ALIAS = "127.0.1.1"

# The responder that publishes `<name>.local`. It does not follow a live
# hostname change on Raspberry Pi OS: a device renamed this way kept answering
# its previous name until this was restarted.
MDNS_UNIT = "avahi-daemon.service"


class NmError(Exception):
    """A NetworkManager operation failed. The message is safe to show a user."""


# What a failure means, in words a person can act on. Raw external text is
# never stored or shown: it can contain anything at all, and the setup state and
# the page are not places to put it. A test submits a passphrase in stderr and
# asserts it reaches neither.
PUBLIC_FAILURES = (
    ("secrets were required", "The Wi-Fi password was refused by the network"),
    ("no network with ssid", "That network was not found"),
    ("no wifi device", "This device has no usable Wi-Fi interface"),
    ("not authorized", "NetworkManager refused the change"),
    ("activation failed", "The device could not join that network"),
)


def public_failure(detail, code):
    """One bounded, credential-free sentence for a NetworkManager failure."""
    text = " ".join((detail or "").lower().split())
    for needle, message in PUBLIC_FAILURES:
        if needle in text:
            return message
    return f"NetworkManager reported failure {code}"


def _run(argv, timeout=45):
    try:
        result = subprocess.run(argv, capture_output=True, text=True,
                                timeout=timeout, check=False)
    except FileNotFoundError:
        # Name the binary that is actually missing. `raspi-config` and `iw` use
        # this too, and telling someone their NetworkManager is absent when it
        # is `raspi-config` that is absent is a false statement about their
        # device, shown on the setup page. No chain: the traceback of a timeout
        # carries the command line, and the command line is not for a journal.
        raise NmError(f"{argv[0]} is not installed") from None
    except subprocess.TimeoutExpired:
        raise NmError(f"{argv[0]} did not answer in time") from None
    except OSError:
        # A permission or resource failure carries a path and often a filename
        # in its text. None of that belongs on the page, in the state file or
        # in the journal, so only the class of failure leaves here.
        raise NmError(f"{argv[0]} could not be run") from None
    if result.returncode != 0:
        # Only the classification leaves this function; the raw text does not.
        raise NmError(public_failure(result.stderr or result.stdout, result.returncode))
    return result.stdout


def _terse_split(line):
    """Split one nmcli terse-mode line on unescaped colons.

    `-t` escapes a colon inside a value as `\\:` and a backslash as `\\\\`, so a
    network called `a:b` is one field and not two.
    """
    fields, current, escaped = [], [], False
    for char in line:
        if escaped:
            current.append(char)
            escaped = False
        elif char == "\\":
            escaped = True
        elif char == ":":
            fields.append("".join(current))
            current = []
        else:
            current.append(char)
    fields.append("".join(current))
    return fields


def valid_psk(psk):
    """A WPA passphrase: 8-63 printable ASCII characters.

    Control characters are refused rather than escaped. A newline in a keyfile
    value is a second line, which is how `abcdefgh\npsk-flags=1` becomes two
    settings instead of one password.
    """
    return (isinstance(psk, str) and 8 <= len(psk) <= 63
            and all(" " <= char <= "~" for char in psk))


def valid_ssid(ssid):
    """A network name: 1-32 bytes of UTF-8, printable.

    The limit is 32 *octets* on the wire, not 32 characters, so an accented
    name is counted the way the radio counts it.
    """
    if not isinstance(ssid, str) or not ssid.isprintable():
        return False
    try:
        size = len(ssid.encode("utf-8"))
    except UnicodeEncodeError:
        return False
    return 1 <= size <= 32


def valid_country(code):
    return isinstance(code, str) and bool(re.fullmatch(r"[A-Z]{2}", code))


def valid_hostname(name):
    """A single DNS label: what a device name has to be to resolve as .local.

    Dots are refused on purpose. A name with a dot is a domain, not a label, and
    `hostnamectl` accepts one that avahi will not announce as `<name>.local`.
    """
    return isinstance(name, str) and bool(re.fullmatch(r"[A-Za-z0-9]([A-Za-z0-9-]{0,61}[A-Za-z0-9])?", name))


def hosts_naming(text, hostname):
    """Return `/etc/hosts` text that names this device on its loopback alias.

    The alias is the device's own name, and there is one such line. Its content
    is rewritten; every other line keeps its text, including the comment header
    cloud-init writes and the IPv6 block. Line endings are normalised to LF and a
    trailing newline is added, because the file is written back whole.

    The alias carries the name twice, which is the shape Raspberry Pi OS writes
    (`127.0.1.1 debra-lab debra-lab`). The line is rewritten whole, so **every
    other name on it is deleted**, including one a person added: any name there is
    a name this device answers to, and a leftover from a previous device name made
    `sudo` resolve the wrong one. For the same reason a second `127.0.1.1` line is
    removed rather than left behind.

    If the text has no `localhost` entry the result gains one, so a file that was
    truncated or left empty cannot come back without a resolvable localhost. The
    name is looked for among the line's aliases, not merely by the address: a
    partially written `127.0.0.1 local` has the address and not the name, and
    treating that as present left the file unable to resolve localhost.
    """
    alias = f"{HOSTS_ALIAS} {hostname} {hostname}"
    lines = []
    placed = False
    has_localhost = False
    for existing in text.splitlines():
        # A `#` starts a comment wherever it appears in the line, including
        # attached to the alias before it: `127.0.0.1 router# localhost` names
        # only `router`. Splitting the whole line first counted the comment's
        # words as names, so this repair left a file with no localhost entry.
        fields = existing.partition("#")[0].split()
        if fields[:1] == [HOSTS_ALIAS]:
            if not placed:
                lines.append(alias)
                placed = True
            continue
        if fields[:1] == ["127.0.0.1"]:
            if "localhost" in fields[1:]:
                has_localhost = True
        lines.append(existing)
    if not has_localhost:
        lines.append("127.0.0.1 localhost")
    if not placed:
        # Beside the localhost entry, where a person reading the file expects it.
        for index, existing in enumerate(lines):
            if existing.partition("#")[0].split()[:1] == ["127.0.0.1"]:
                lines.insert(index + 1, alias)
                break
        else:
            lines.append(alias)
    return "\n".join(lines) + "\n"


def _replace_text(path, text):
    """Replace a file's contents atomically, keeping its mode and owner.

    The same shape as the keyfile writer below, for the same reason: an
    interrupted in-place write of `/etc/hosts` leaves a device that cannot
    resolve `localhost`, and `O_TRUNC` has exactly that window. `path` is already
    resolved by the caller, so replacing it keeps a symlinked `/etc/hosts`
    working.

    Owner and mode are copied. ACLs, extended attributes and a security label are
    not, and a `/etc/hosts` that is a bind mount cannot be replaced this way at
    all (`os.replace` fails with `EBUSY`). Neither applies to a stock Raspberry Pi
    OS image; both would matter on a container or an image that mounts the file.
    """
    original = path.stat()
    fd, staged = tempfile.mkstemp(prefix=f".{path.name}-", suffix=".part",
                                  dir=str(path.parent))
    try:
        with os.fdopen(fd, "w", encoding="utf-8", errors="surrogateescape") as stream:
            stream.write(text)
            stream.flush()
            os.fsync(stream.fileno())
        try:
            os.chown(staged, original.st_uid, original.st_gid)
        except (OSError, AttributeError):
            pass
        # Mode after owner: a chown can clear the set-user-ID and set-group-ID
        # bits, and chmod is what puts the original mode back exactly.
        os.chmod(staged, original.st_mode & 0o7777)
        os.replace(staged, path)
        _fsync_directory(path.parent)
    except BaseException:
        try:
            os.unlink(staged)
        except OSError:
            pass
        raise


def _keyfile_value(text):
    """Escape one value for a NetworkManager keyfile, exactly once.

    A keyfile is a GLib key file. A value is one line; `#` only starts a
    comment at the beginning of a line; a leading or trailing space is
    stripped. So the escapes that matter are the line break, the backslash and
    the spaces at either end. `;` and `#` *inside* a value are literal, and
    escaping them makes GLib reject the file - the previous version did that
    and a real parser refused `Caf; #1`.
    """
    first = len(text) - len(text.lstrip(" "))
    last = len(text.rstrip(" ")) - 1
    out = []
    for index, char in enumerate(text):
        if char == "\\":
            out.append("\\\\")
        elif char == "\n":
            out.append("\\n")
        elif char == "\r":
            out.append("\\r")
        elif char == "\t":
            out.append("\\t")
        elif char == " " and (index < first or index > last):
            out.append("\\s")
        else:
            out.append(char)
    return "".join(out)


def _keyfile_ssid(ssid):
    """Write the SSID as NetworkManager's explicit byte list, not as text.

    `ssid` is not an ordinary string property. NetworkManager's keyfile reader
    keeps the historical semicolon-separated integer form: a submitted
    `65;66;` becomes the two bytes `AB`, and after GLib unescapes `A\\;B` the
    reader applies its own SSID parser, which loses the backslash. Both were
    checked against the installed libnm parser, not argued from the source.

    The byte list has no such ambiguity: every octet is stated, so no character
    a network name can contain is special. It is also what NetworkManager
    itself writes when the text form would be ambiguous.
    """
    if not valid_ssid(ssid):
        raise NmError("Network name must be 1-32 printable bytes")
    return ";".join(str(octet) for octet in ssid.encode("utf-8")) + ";"


def _fsync_directory(directory):
    """Make a rename in `directory` durable. Best effort, never raises."""
    try:
        handle = os.open(directory, os.O_RDONLY)
    except OSError:
        return
    try:
        os.fsync(handle)
    except OSError:
        pass
    finally:
        os.close(handle)


def _write_profile(directory, name, lines):
    """Write one keyfile atomically, owner-only, and return its final path.

    Shared by the household join and the access point, because both have the
    same requirement: the profile has to be on disk, complete, before anything
    reads it. The file is written under a staged name and renamed into place,
    so a crash mid-write cannot leave a profile that looks real but is empty or
    truncated, and no reader ever sees half a file.

    Some NetworkManager builds watch this directory and some do not, and the
    manual tells an administrator to reload after editing a file by hand, so
    the callers run `connection load`/`connection reload` explicitly either
    way. Writing the profile is never what makes NetworkManager notice it.
    """
    directory = Path(directory or PROFILES_DIR)
    try:
        directory.mkdir(parents=True, exist_ok=True)
        fd, staged = tempfile.mkstemp(prefix=f".{name}-", suffix=".part",
                                      dir=directory)
    except OSError:
        # A path and a filename are not a sentence for the setup page.
        raise NmError("The Wi-Fi profile could not be saved on this device") from None
    final = directory / f"{name}.nmconnection"
    try:
        with os.fdopen(fd, "w", encoding="utf-8") as stream:
            stream.write("\n".join(lines))
            stream.flush()
            os.fsync(stream.fileno())
        os.chmod(staged, 0o600)
        os.replace(staged, final)
        _fsync_directory(directory)
    except OSError:
        try:
            os.unlink(staged)
        except OSError:
            pass
        raise NmError("The Wi-Fi profile could not be saved on this device") from None
    return final


def write_keyfile(directory, ssid, psk, connection_id, autoconnect=False,
                  interface=None):
    """Write one Wi-Fi profile where NetworkManager will keep it.

    The password goes here rather than into an `nmcli` argument because argv is
    world-readable in /proc while the command runs. The file is 0600 and stays
    where it is: `nmcli connection load` loads a profile *from a location the
    keyfile plugin reads*, it does not copy an arbitrary file into storage. A
    profile in a temporary directory is not one NetworkManager will find again,
    so the previous version's file was both rejected and deleted, and the
    device had no household network after a reboot.

    `autoconnect` stays off until the join has been verified, so a trial that
    fails never competes with the real network. `interface` pins the profile to
    one radio, so a device with two Wi-Fi interfaces cannot bring the household
    network up on the wrong one.
    """
    connection = ["[connection]",
                  f"id={_keyfile_value(connection_id)}",
                  "type=wifi",
                  "autoconnect=" + ("true" if autoconnect else "false")]
    if interface:
        connection.append(f"interface-name={_keyfile_value(interface)}")
    lines = connection + ["",
                          "[wifi]",
                          "mode=infrastructure",
                          f"ssid={_keyfile_ssid(ssid)}",
                          ""]
    if psk:
        lines += ["[wifi-security]", "key-mgmt=wpa-psk", f"psk={_keyfile_value(psk)}", ""]
    lines += ["[ipv4]", "method=auto", "", "[ipv6]", "method=auto", ""]
    return _write_profile(directory, connection_id, lines)


def hotspot_profile_path(directory=None):
    """The one file the setup access point's profile is kept in."""
    return Path(directory or PROFILES_DIR) / f"{SETUP_CONNECTION}.nmconnection"


def write_hotspot_keyfile(directory, ssid, interface, password):
    """Write the setup access point's profile, with the security we asked for.

    `nmcli device wifi hotspot` is not usable for this. Its own manual says the
    password is *generated* when none is given, so asking it for an open network
    produced a WPA2 network whose key nobody could read - and the read-back then
    deleted it, leaving a device with no setup network at all. `key-mgmt=none`
    in an explicit profile is the only way to say "open" and mean it, and it
    keeps the password out of argv on the way.

    `ipv4.method=shared` is what gives the access point an address and a DHCP
    server for the phone that joins it. It is also why this profile is rewritten
    in place rather than deleted when the mode changes: NetworkManager gives
    each new shared connection the next subnet (10.42.0.1, then 10.42.1.1), and
    the page is bound to the address the first one handed out.

    `autoconnect=false`: the setup network exists for one boot's job. A profile
    that comes up on its own would compete with the household network later.
    """
    if not valid_ssid(ssid):
        raise NmError("Hotspot name must be 1-32 printable characters")
    if not interface:
        raise NmError("The setup network needs a Wi-Fi interface")
    if password is not None and not valid_psk(password):
        raise NmError("Wi-Fi password must be 8-63 printable characters")
    lines = ["[connection]",
             f"id={_keyfile_value(SETUP_CONNECTION)}",
             f"uuid={HOTSPOT_UUID}",
             "type=wifi",
             "autoconnect=false",
             f"interface-name={_keyfile_value(interface)}",
             "",
             "[wifi]",
             "mode=ap",
             f"ssid={_keyfile_ssid(ssid)}",
             "",
             "[wifi-security]",
             "key-mgmt=" + ("wpa-psk" if password else "none")]
    if password:
        lines.append(f"psk={_keyfile_value(password)}")
    lines += ["", "[ipv4]", "method=shared", "", "[ipv6]", "method=ignore", ""]
    return _write_profile(directory, SETUP_CONNECTION, lines)


class Nmcli:
    """The real adapter. `runner` is injectable so tests never touch a network."""

    def __init__(self, runner=_run, profiles_dir=None, hosts_path=HOSTS_PATH):
        self._run = runner
        # Where the access point's profile has to live to be found again after
        # a reboot. Injectable, so an offline test writes into a scratch
        # directory instead of this machine's real NetworkManager store.
        # `connect` takes its own `keyfile_dir`; it does not read this, so a
        # test that constructs the adapter with a scratch `profiles_dir` and
        # then joins a network still has to pass `keyfile_dir` as well.
        self.profiles_dir = Path(profiles_dir or PROFILES_DIR)
        self._hosts_path = Path(hosts_path)

    def wifi_interface(self):
        out = self._run(["nmcli", "-t", "-f", "DEVICE,TYPE", "device", "status"])
        for line in out.splitlines():
            device, _, kind = line.partition(":")
            if kind.strip() == "wifi":
                return device.strip() or None
        return None

    def country(self):
        # `nmcli general radio wifi` is not a command; it fails, and the failure
        # used to escape before `iw` was ever asked, so a device with a country
        # already set was asked for one again. The real command is `nmcli radio`.
        state = self._run(["nmcli", "radio", "wifi"], timeout=15).strip().lower()
        if state.startswith("disabled"):
            raise NmError("The Wi-Fi radio is switched off")
        try:
            text = self._run(["iw", "reg", "get"], timeout=15)
        except NmError:
            return None
        match = re.search(r"^country ([A-Z]{2}):", text, re.MULTILINE)
        return match.group(1) if match else None

    def set_hostname(self, hostname):
        """Apply the device name to the running system.

        Recording a name is not applying it. Without this the page shows a name
        the device does not answer to, so `<name>.local` never resolves and the
        person has no way to reach it after the setup network is gone.

        Applying it is more than `hostnamectl`. The loopback alias in
        `/etc/hosts` and the running mDNS responder both keep the previous name
        until something tells them, and neither follows a live rename on
        Raspberry Pi OS. A device renamed by an earlier version of this method
        answered `hostname -f` with "Name or service not known", printed
        `sudo: unable to resolve host <new name>` on every privileged command,
        and still advertised `<old name>.local`, all until it was rebooted.
        """
        if not valid_hostname(hostname):
            raise NmError("Device name must be letters, digits and dashes, 1-63 characters")
        self._run(["hostnamectl", "set-hostname", hostname], timeout=30)
        # After the rename, never before: an alias written first would name a
        # hostname the machine does not have if `hostnamectl` then failed.
        self._alias_hosts(hostname)
        self._restart_mdns()

    def _alias_hosts(self, hostname):
        """Point the loopback alias at `hostname`, keeping the rest of the file.

        A failure here is not fatal. The name itself is applied and the device
        works, and the caller already treats a `set_hostname` failure as "recorded
        but not applied", which would be a false statement here: it was applied,
        only incompletely.
        """
        try:
            # Resolved, so a symlinked /etc/hosts keeps working when the target
            # is replaced rather than rewritten in place.
            target = self._hosts_path.resolve()
            text = target.read_text(encoding="utf-8", errors="surrogateescape")
        except OSError:
            LOGGER.warning("Device name applied but %s could not be read", self._hosts_path)
            return
        updated = hosts_naming(text, hostname)
        if updated == text:
            return
        try:
            _replace_text(target, updated)
        except OSError:
            LOGGER.warning("Device name applied but %s could not be updated",
                           self._hosts_path)

    def _restart_mdns(self):
        """Make `<name>.local` follow the name the device now has.

        `restart` would also *start* a responder somebody deliberately stopped,
        and this service does not own mDNS, so it is only restarted when it is
        already running. A device with no avahi at all publishes no `.local`
        name, so there is nothing to correct and nothing to report.

        This is not conditional on the name having changed. Asking the responder
        what it is advertising is the honest test and there is no cheap way to do
        it: `hostnamectl --static` only reports what `/etc/hostname` holds, which
        is already correct when another tool did the rename, and restarting only
        on a change would leave exactly that device stale. An explicit
        `host-name=` in `avahi-daemon.conf` also survives this restart, which is
        why the setup page still offers the address as well as the name.

        A failed query is treated as "nothing to restart". "Not running" and "no
        such unit" cannot be told apart without parsing systemctl's text, which
        this module never does, and a warning on every rename of a device without
        avahi would read as a fault.
        """
        try:
            state = self._run(["systemctl", "is-active", MDNS_UNIT], timeout=15).strip()
        except (NmError, AttributeError):
            return
        if state != "active":
            return
        try:
            self._run(["systemctl", "try-restart", MDNS_UNIT], timeout=30)
        except (NmError, AttributeError):
            LOGGER.warning("Device name applied but %s was not restarted", MDNS_UNIT)

    def set_country(self, code):
        if not valid_country(code):
            raise NmError("Country must be two capital letters")
        # raspi-config owns the regulatory domain on Raspberry Pi OS; using it
        # keeps the setting where the rest of the system expects it.
        self._run(["raspi-config", "nonint", "do_wifi_country", code], timeout=30)

    def active(self):
        """The current uplink, or None. Address is only trusted if routable."""
        out = self._run(["nmcli", "-t", "-f", "DEVICE,TYPE,STATE", "device", "status"])
        interface = None
        for line in out.splitlines():
            device, _, rest = line.partition(":")
            kind, _, state = rest.partition(":")
            if kind.strip() == "wifi" and state.strip() == "connected":
                interface = device.strip()
                break
        if interface is None:
            return None
        detail = self._run(["nmcli", "-t", "-f", "IP4.ADDRESS,IP4.GATEWAY",
                            "device", "show", interface])
        address = gateway = None
        for line in detail.splitlines():
            key, _, value = line.partition(":")
            # nmcli -t writes repeated fields with an index: "IP4.ADDRESS[1]:".
            # Comparing against the bare name silently never matched, which made
            # every successful join look like a network with no address.
            key = re.sub(r"\[\d+\]$", "", key.strip())
            if key == "IP4.ADDRESS" and address is None:
                address = value.split("/")[0].strip() or None
            elif key == "IP4.GATEWAY":
                gateway = value.strip() or None
        return {"interface": interface, "address": address, "gateway": gateway,
                "routable": routable(address), "has_route": bool(gateway)}

    def scan(self, interface, limit=20, timeout=30):
        """Nearby networks, strongest first. Empty on any failure.

        A scan must happen while the radio is free: asking for one with the
        setup access point up can drop the person's phone off it. The caller
        only calls this before raising the AP, and an empty list is a normal
        answer - the page then falls back to typing the name.
        """
        if not interface:
            return []
        try:
            out = self._run(["nmcli", "-t", "-f", "SSID,SIGNAL,SECURITY",
                             "device", "wifi", "list", "--rescan", "yes",
                             "ifname", interface], timeout=timeout)
        except (NmError, AttributeError):
            return []
        seen = {}
        for line in out.splitlines():
            fields = _terse_split(line)
            if len(fields) < 3:
                continue
            # The name is not stripped. A leading or trailing space is part of
            # the SSID on the air, so trimming it here offers the person a
            # network that is not the one the scan found.
            ssid, signal, security = fields[0], fields[1].strip(), fields[2].strip()
            if not ssid:
                # A hidden network has no name to offer; typing it still works.
                continue
            try:
                strength = int(signal)
            except ValueError:
                strength = 0
            if ssid not in seen or strength > seen[ssid]["signal"]:
                seen[ssid] = {"ssid": ssid, "signal": strength,
                              "security": security or "open"}
        ordered = sorted(seen.values(), key=lambda item: (-item["signal"], item["ssid"]))
        return ordered[:limit]

    def active_connection(self, interface):
        """The connection name NetworkManager has active on a device, or None."""
        if not interface:
            return None
        detail = self._run(["nmcli", "-t", "-f", "GENERAL.CONNECTION",
                            "device", "show", interface])
        for line in detail.splitlines():
            key, _, value = line.partition(":")
            if key.strip() == "GENERAL.CONNECTION":
                return value.strip() or None
        return None

    def device_address(self, interface):
        """The IPv4 address a device holds, or None.

        The setup page is bound to the address the access point actually got,
        not to the 10.42.0.1 that shared mode usually assigns. A different
        subnet would otherwise make the bind fail and leave a person with a
        setup network and no page.
        """
        if not interface:
            return None
        detail = self._run(["nmcli", "-t", "-f", "IP4.ADDRESS",
                            "device", "show", interface])
        for line in detail.splitlines():
            key, _, value = line.partition(":")
            if re.sub(r"\[\d+\]$", "", key.strip()) == "IP4.ADDRESS":
                address = value.split("/")[0].strip()
                if address:
                    return address
        return None

    def connect(self, ssid, psk, timeout=60, keyfile_dir=None, interface=None):
        """Join a network and return the resulting uplink, or raise NmError.

        The profile is written to NetworkManager's own profile directory and
        loaded from there, so the password is never in `ps` output and the
        profile survives a reboot. Loading and activating are two steps because
        `nmcli device wifi connect` is the only path that takes a password on
        the command line.

        The profile autoconnects only after the join has been verified. A
        failure deletes it and its file, so a wrong password never leaves a
        profile competing with the household network on the next boot.
        """
        if not valid_ssid(ssid):
            raise NmError("Network name must be 1-32 characters and printable")
        if psk is not None and psk != "" and not valid_psk(psk):
            raise NmError("Wi-Fi password must be 8-63 printable characters")
        connection_id = f"debra-wifi-{secrets.token_hex(4)}"
        path = write_keyfile(keyfile_dir, ssid, psk or None, connection_id,
                             interface=interface)
        try:
            self._run(["nmcli", "connection", "load", str(path)], timeout=30)
            self._run(["nmcli", "connection", "up", "id", connection_id],
                      timeout=timeout)
            active = self.active()
            if active is None:
                raise NmError("Joined the network but NetworkManager reports no uplink")
            # A connected Wi-Fi device is not proof that *this* profile is the
            # one that came up: an older profile can win the race. An unknown
            # profile is not success either - the previous check let None
            # through, so a blank reading counted as a working household join.
            current = self.active_connection(active["interface"])
            if current != connection_id:
                raise NmError("Joined the network, but a different saved network is active")
            if interface and active["interface"] != interface:
                # The profile names its interface, so this means NetworkManager
                # ignored that and brought the network up somewhere else. The
                # household network must be on the radio the page was reached
                # over, not on a second interface nobody looked at.
                raise NmError("Joined the network on a different Wi-Fi interface")
            if not active["routable"]:
                raise NmError("Joined the network but received no usable address")
            if not active["has_route"]:
                raise NmError("Joined the network but received no default route")
        except NmError:
            self._forget(connection_id, path)
            raise
        # Keep the profile: it is the network this device must rejoin on the
        # next boot. Only now is it allowed to connect on its own.
        #
        # This is not optional. A profile left with autoconnect off works until
        # the next reboot and then leaves the device with no network at all, so
        # a promotion that keeps failing is a failed join: the profile goes and
        # the access point comes back while the person is still there to see it.
        for attempt in (1, 2):
            try:
                self._run(["nmcli", "connection", "modify", connection_id,
                           "connection.autoconnect", "yes"], timeout=30)
                return active
            except NmError as exc:
                LOGGER.warning("Could not set the profile to autoconnect (attempt %d): %s",
                               attempt, exc)
        self._forget(connection_id, path)
        raise NmError("Joined the network, but the profile could not be saved for the next boot")

    def _forget(self, connection_id, path):
        """Remove a profile that did not work, and its file."""
        try:
            self._run(["nmcli", "connection", "delete", "id", connection_id], timeout=30)
        except NmError:
            pass
        try:
            Path(path).unlink(missing_ok=True)
        except OSError:
            pass

    def start_hotspot(self, ssid, interface, password=None):
        """Raise the setup access point from a profile we wrote, and verify it.

        Returns `{"key_mgmt": ..., "address": ...}` for what is actually
        running, because what was asked for is not evidence of what came up.

        The profile is rewritten in place and reloaded, then the access point is
        brought down and up. A reload alone does not re-key a running access
        point - NetworkManager keeps the settings a connection was activated
        with - and deleting the connection instead would hand the device a new
        shared subnet, moving the address the setup page is bound to.
        """
        wanted = "wpa-psk" if password else "none"
        if password and not valid_psk(password):
            raise NmError("Wi-Fi password must be 8-63 printable characters")
        path = write_hotspot_keyfile(self.profiles_dir, ssid, interface, password)
        try:
            self._run(["nmcli", "connection", "reload"], timeout=30)
            if self._device_detail(interface)["connection"] == SETUP_CONNECTION:
                self._run(["nmcli", "connection", "down", "id", SETUP_CONNECTION],
                          timeout=60)
            self._run(["nmcli", "connection", "up", "id", SETUP_CONNECTION,
                       "ifname", interface], timeout=60)
            actual = self._hotspot_security()
            detail = self._device_detail(interface)
        except NmError:
            self._forget_hotspot(path)
            raise
        # An open profile is the one case where the value cannot be trusted to
        # be a word: `none` is what a keyfile with `key-mgmt=none` reports, but
        # a build that materialises no security setting at all prints an empty
        # value. Both mean "no key". Demanding the exact word would take down
        # the only setup network the device has, which is the failure this whole
        # mechanism exists to prevent, so both are accepted.
        matched = (actual == wanted) or (wanted == "none" and actual == "")
        if not matched:
            self._forget_hotspot(path)
            raise NmError("The setup network could not be secured as asked")
        if detail["state"] != NM_ACTIVATED or detail["connection"] != SETUP_CONNECTION:
            # The profile loaded but the radio did not come up on it: another
            # profile won, or the driver refused AP mode. A setup network that
            # is not activated has no address and no page.
            self._forget_hotspot(path)
            raise NmError("The setup network did not come up on this device")
        return {"key_mgmt": actual, "address": detail["address"]}

    def _device_detail(self, interface):
        """Activation state, active connection and first IPv4 address of a device.

        One call rather than three: `nmcli -t` prints repeated fields with an
        index (`IP4.ADDRESS[1]:`), which is stripped here the same way `active()`
        does it, so an address is never silently missed.
        """
        if not interface:
            return {"state": None, "connection": None, "address": None}
        detail = self._run(["nmcli", "-t", "-f",
                            "GENERAL.STATE,GENERAL.CONNECTION,IP4.ADDRESS",
                            "device", "show", interface], timeout=30)
        state = connection = address = None
        for line in detail.splitlines():
            key, _, value = line.partition(":")
            key = re.sub(r"\[\d+\]$", "", key.strip())
            value = value.strip()
            if key == "GENERAL.STATE":
                match = re.match(r"(\d+)", value)
                state = int(match.group(1)) if match else None
            elif key == "GENERAL.CONNECTION":
                connection = value or None
            elif key == "IP4.ADDRESS" and address is None:
                address = value.split("/")[0].strip() or None
        return {"state": state, "connection": connection, "address": address}

    def _hotspot_security(self):
        """The key management setting of the profile the setup access point uses.

        `-g` and not `-t`: terse output keeps the property name in front of the
        value (`802-11-wireless-security.key-mgmt:wpa-psk`), so comparing the
        stripped line to `wpa-psk` never matched and every access point was torn
        down as if it had come up wrong. `-g` is the `--get-values` form, which
        prints the value alone. That was checked against a real nmcli (1.58.1),
        not inferred: the same command with `-t` printed the labelled line.

        This reads the profile, not the beacon; `start_hotspot` checks the
        activated device separately. What a real NetworkManager prints for an
        open profile here is unverified - `none` is documented, and an empty
        value is accepted as open too, in `start_hotspot`.
        """
        output = self._run(["nmcli", "-g",
                            "802-11-wireless-security.key-mgmt",
                            "connection", "show", "id", SETUP_CONNECTION],
                           timeout=30)
        return output.strip()

    def _remove_hotspot(self):
        try:
            self.stop_hotspot()
        except NmError as exc:
            # Nothing left to try: the caller is about to fail for a reason the
            # page can show, and a second failure here would replace it.
            LOGGER.warning("Setup access point could not be removed: %s", exc)

    def _forget_hotspot(self, path):
        """Remove an access point that did not come up as asked, and its file."""
        self._remove_hotspot()
        try:
            Path(path).unlink(missing_ok=True)
        except OSError:
            pass

    def stop_hotspot(self):
        # Deleting the profile as well as deactivating it keeps a stale
        # "debra-setup" connection from competing with the real network later.
        # The file goes too: a reload would otherwise raise the access point
        # again from a profile that was meant to be gone.
        try:
            self._run(["nmcli", "connection", "delete", SETUP_CONNECTION], timeout=30)
        finally:
            try:
                hotspot_profile_path(self.profiles_dir).unlink(missing_ok=True)
            except OSError:
                pass


def routable(address):
    """A usable unicast address for a device.

    Multicast and broadcast are not device addresses, and 224.0.0.1 and
    255.255.255.255 used to pass because only link-local, loopback and
    unspecified were rejected.
    """
    if not address:
        return False
    try:
        parsed = ipaddress.IPv4Address(address)
    except ipaddress.AddressValueError:
        return False
    return not (parsed.is_link_local or parsed.is_loopback or parsed.is_unspecified
                or parsed.is_multicast or parsed.is_reserved)

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
from pathlib import Path


LOGGER = logging.getLogger("debra.setup.nm")

# Where the keyfile plugin keeps profiles it will read again after a reboot.
# A profile anywhere else is not persistent, however successfully it loads.
PROFILES_DIR = "/etc/NetworkManager/system-connections"


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

    The profile is written under a name the keyfile plugin does not read and
    renamed into place. Some NetworkManager builds watch this directory and
    some do not, and the manual tells an administrator to reload after editing
    a file by hand, so the caller runs `connection load` explicitly either way.
    The rename still matters: a crash mid-write would otherwise leave a profile
    that looks real but is empty or truncated.

    `autoconnect` stays off until the join has been verified, so a trial that
    fails never competes with the real network. `interface` pins the profile to
    one radio, so a device with two Wi-Fi interfaces cannot bring the household
    network up on the wrong one.
    """
    directory = Path(directory or PROFILES_DIR)
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
    try:
        directory.mkdir(parents=True, exist_ok=True)
        fd, staged = tempfile.mkstemp(prefix=f".{connection_id}-", suffix=".part",
                                      dir=directory)
    except OSError:
        # A path and a filename are not a sentence for the setup page.
        raise NmError("The Wi-Fi profile could not be saved on this device") from None
    final = directory / f"{connection_id}.nmconnection"
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


class Nmcli:
    """The real adapter. `runner` is injectable so tests never touch a network."""

    def __init__(self, runner=_run):
        self._run = runner

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
        """
        if not valid_hostname(hostname):
            raise NmError("Device name must be letters, digits and dashes, 1-63 characters")
        self._run(["hostnamectl", "set-hostname", hostname], timeout=30)

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
        if not valid_ssid(ssid):
            raise NmError("Hotspot name must be 1-32 printable characters")
        argv = ["nmcli", "device", "wifi", "hotspot", "ifname", interface,
                "con-name", "debra-setup", "ssid", ssid]
        if password:
            argv += ["password", password]
        self._run(argv, timeout=60)

    def stop_hotspot(self):
        # Deleting the profile as well as deactivating it keeps a stale
        # "debra-setup" connection from competing with the real network later.
        self._run(["nmcli", "connection", "delete", "debra-setup"], timeout=30)


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

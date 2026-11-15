"""NetworkManager, behind a small interface the onboarding logic can be tested against.

Everything here is a thin, explicit wrapper over `nmcli`. The point is not to
hide NetworkManager but to keep the decisions (is this a success? should the
access point come back?) in one testable place instead of inside shell strings.
"""

from __future__ import annotations

import ipaddress
import os
import re
import secrets
import subprocess
import tempfile
from pathlib import Path


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
    if result.returncode != 0:
        # Only the classification leaves this function; the raw text does not.
        raise NmError(public_failure(result.stderr or result.stdout, result.returncode))
    return result.stdout


def valid_psk(psk):
    return isinstance(psk, str) and 8 <= len(psk) <= 63


def valid_ssid(ssid):
    return isinstance(ssid, str) and 1 <= len(ssid) <= 32 and ssid.isprintable()


def valid_country(code):
    return isinstance(code, str) and bool(re.fullmatch(r"[A-Z]{2}", code))


def valid_hostname(name):
    """A single DNS label: what a device name has to be to resolve as .local.

    Dots are refused on purpose. A name with a dot is a domain, not a label, and
    `hostnamectl` accepts one that avahi will not announce as `<name>.local`.
    """
    return isinstance(name, str) and bool(re.fullmatch(r"[A-Za-z0-9]([A-Za-z0-9-]{0,61}[A-Za-z0-9])?", name))


def _keyfile_value(text):
    """Escape what a NetworkManager keyfile treats as structure.

    A keyfile is an ini file, so a backslash, semicolon or hash inside a network
    name would otherwise change the meaning of the line or start a comment.
    """
    return "".join("\\" + char if char in "\\;#" else char for char in text)


def write_keyfile(directory, ssid, psk, connection_id):
    """Write one Wi-Fi profile to a private file and return its path.

    The password goes here rather than into an `nmcli` argument because argv is
    world-readable in /proc while the command runs. The file is 0600 and is
    deleted by the caller as soon as NetworkManager has read it.
    """
    lines = ["[connection]",
             f"id={_keyfile_value(connection_id)}",
             "type=wifi",
             "autoconnect=true",
             "",
             "[wifi]",
             "mode=infrastructure",
             f"ssid={_keyfile_value(ssid)}",
             ""]
    if psk:
        lines += ["[wifi-security]", "key-mgmt=wpa-psk", f"psk={_keyfile_value(psk)}", ""]
    lines += ["[ipv4]", "method=auto", "", "[ipv6]", "method=auto", ""]
    fd, path = tempfile.mkstemp(prefix="debra-wifi-", suffix=".nmconnection", dir=directory)
    try:
        with os.fdopen(fd, "w", encoding="utf-8") as stream:
            stream.write("\n".join(lines))
            stream.flush()
            os.fsync(stream.fileno())
        os.chmod(path, 0o600)
    except BaseException:
        try:
            os.unlink(path)
        except OSError:
            pass
        raise
    return Path(path)


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
        out = self._run(["nmcli", "general", "radio", "wifi"], timeout=15)
        del out  # the radio state is read for its error, not its text
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

    def connect(self, ssid, psk, timeout=60, keyfile_dir=None):
        """Join a network and return the resulting uplink, or raise NmError.

        The profile is loaded from a private keyfile rather than built from
        command-line arguments, so the password is never in `ps` output. Loading
        the profile and activating it are two steps because `nmcli device wifi
        connect` is the only path that takes a password on the command line.

        A profile that fails is deleted: a leftover autoconnecting profile
        competing with the household network is worse than no profile at all.
        """
        if not valid_ssid(ssid):
            raise NmError("Network name must be 1-32 printable characters")
        if psk is not None and psk != "" and not valid_psk(psk):
            raise NmError("Wi-Fi password must be 8-63 characters")
        connection_id = f"debra-wifi-{secrets.token_hex(4)}"
        path = write_keyfile(keyfile_dir, ssid, psk or None, connection_id)
        try:
            self._run(["nmcli", "connection", "load", str(path)], timeout=30)
        except NmError:
            path.unlink(missing_ok=True)
            raise
        path.unlink(missing_ok=True)
        try:
            self._run(["nmcli", "connection", "up", "id", connection_id],
                      timeout=timeout)
        except NmError:
            try:
                self._run(["nmcli", "connection", "delete", "id", connection_id],
                          timeout=30)
            except NmError:
                pass
            raise
        active = self.active()
        if active is None:
            raise NmError("Joined the network but NetworkManager reports no uplink")
        # A connected Wi-Fi device is not proof that *this* profile is the one
        # that came up: an older profile could have won the race. Success means
        # the profile that was just loaded is the active connection.
        current = self.active_connection(active["interface"])
        if current is not None and current != connection_id:
            raise NmError("Joined the network, but a different saved network is active")
        if not active["routable"]:
            raise NmError("Joined the network but received no usable address")
        if not active["has_route"]:
            raise NmError("Joined the network but received no default route")
        return active

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

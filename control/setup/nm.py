"""NetworkManager, behind a small interface the onboarding logic can be tested against.

Everything here is a thin, explicit wrapper over `nmcli`. The point is not to
hide NetworkManager but to keep the decisions (is this a success? should the
access point come back?) in one testable place instead of inside shell strings.
"""

from __future__ import annotations

import ipaddress
import re
import subprocess


class NmError(Exception):
    """A NetworkManager operation failed. The message is safe to show a user."""


def _run(argv, timeout=45):
    try:
        result = subprocess.run(argv, capture_output=True, text=True,
                                timeout=timeout, check=False)
    except FileNotFoundError as exc:
        raise NmError("nmcli is not installed") from exc
    except subprocess.TimeoutExpired as exc:
        raise NmError(f"nmcli {argv[1]} timed out") from exc
    if result.returncode != 0:
        # nmcli writes the reason to stderr; the browser never sees raw output,
        # so only a short, single-line form is kept.
        detail = " ".join(result.stderr.strip().split())[:200]
        raise NmError(detail or f"nmcli {argv[1]} exited {result.returncode}")
    return result.stdout


def valid_psk(psk):
    return isinstance(psk, str) and 8 <= len(psk) <= 63


def valid_ssid(ssid):
    return isinstance(ssid, str) and 1 <= len(ssid) <= 32 and ssid.isprintable()


def valid_country(code):
    return isinstance(code, str) and bool(re.fullmatch(r"[A-Z]{2}", code))


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
            if key.strip() == "IP4.ADDRESS" and address is None:
                address = value.split("/")[0].strip() or None
            elif key.strip() == "IP4.GATEWAY":
                gateway = value.strip() or None
        return {"interface": interface, "address": address, "gateway": gateway,
                "routable": routable(address), "has_route": bool(gateway)}

    def connect(self, ssid, psk, timeout=60):
        """Join a network and return the resulting uplink, or raise NmError.

        `nmcli device wifi connect` both creates and activates the profile, which
        is what we want: the profile is the thing that survives a reboot.
        """
        if not valid_ssid(ssid):
            raise NmError("Network name must be 1-32 printable characters")
        if psk is not None and not valid_psk(psk):
            raise NmError("Wi-Fi password must be 8-63 characters")
        argv = ["nmcli", "device", "wifi", "connect", ssid]
        if psk:
            argv += ["password", psk]
        self._run(argv, timeout=timeout)
        active = self.active()
        if active is None:
            raise NmError("Joined the network but NetworkManager reports no uplink")
        if not active["routable"]:
            raise NmError("Joined the network but received no usable address")
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
    """A usable address, not link-local, loopback or unspecified."""
    if not address:
        return False
    try:
        parsed = ipaddress.IPv4Address(address)
    except ipaddress.AddressValueError:
        return False
    return not (parsed.is_link_local or parsed.is_loopback or parsed.is_unspecified)

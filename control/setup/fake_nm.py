"""A fake NetworkManager, for the dev server and for tests.

This file never runs on a device. It exists so the whole onboarding journey can
be clicked through — and asserted on — without a Pi, a radio, or root.
"""

from __future__ import annotations


class FakeNetwork:
    """Records what was asked and answers like NetworkManager would.

    `behaviour` selects the outcome of a join:
      "ok"        join succeeds and reports a routable address
      "bad-psk"   nmcli refuses the password
      "no-address" it associates but never gets a usable address
      "no-uplink"  it reports no uplink at all

    It does not model `nmcli` itself: the access point is recorded, not raised.
    The adapter's own profile write, reload, activation and read-back are
    exercised by the nmcli double in tests/test_onboarding.py, which has to
    answer like NetworkManager or the check is proving nothing.
    """

    def __init__(self, interface="wlan0", country=None, behaviour="ok"):
        self.interface = interface
        self.country_code = country
        self.behaviour = behaviour
        self.calls = []
        self.hotspot = None
        self.joined = None
        self.hostname = None
        # What the access point hands out in shared mode. A test that wants to
        # see a page left on a stale address moves this between two raises.
        self.address = "10.42.0.1"

    # -- identity -----------------------------------------------------------

    # -- radio --------------------------------------------------------------

    def wifi_interface(self):
        self.calls.append(("wifi_interface",))
        return self.interface

    def country(self):
        """The regulatory domain already set, as a real device would report it."""
        self.calls.append(("country",))
        return self.country_code

    def set_hostname(self, hostname):
        self.calls.append(("set_hostname", hostname))
        if getattr(self, "fail_hostname", False):
            try:
                from . import nm as nm_module
            except ImportError:
                import nm as nm_module
            raise nm_module.NmError("hostnamectl did not answer in time")
        self.hostname_applied = hostname

    def set_country(self, code):
        self.calls.append(("set_country", code))
        self.country_code = code

    def scan(self, interface, limit=20, timeout=30):
        self.calls.append(("scan", interface))
        if self.behaviour == "scan-fails":
            try:
                from . import nm as nm_module
            except ImportError:
                import nm as nm_module
            raise nm_module.NmError("nmcli did not answer in time")
        return [{"ssid": "HomeWiFi", "signal": 82, "security": "WPA2"},
                {"ssid": "Neighbour", "signal": 40, "security": "WPA2"},
                {"ssid": "Cafe", "signal": 71, "security": "open"}]

    def active(self):
        self.calls.append(("active",))
        if self.hotspot:
            return None
        if self.joined:
            return {"interface": self.interface, "address": "192.0.2.40",
                    "gateway": "192.0.2.1", "routable": True, "has_route": True}
        return None

    def device_address(self, interface):
        """The address the access point holds, as `nmcli device show` reports it."""
        self.calls.append(("device_address", interface))
        return self.address if interface else None

    # -- transitions --------------------------------------------------------

    def start_hotspot(self, ssid, interface, password=None):
        # The call record keeps a flag rather than the password, so a test log
        # is not a place for a credential. The attribute below does hold the
        # value, because the profile writer is what a test inspects; nothing
        # prints it. The return value is what the real adapter reports after
        # verifying: the key management that is running and the address the
        # access point got.
        self.calls.append(("start_hotspot", ssid, interface, bool(password)))
        self.hotspot = {"ssid": ssid, "interface": interface,
                        "password": password}
        return {"key_mgmt": "wpa-psk" if password else "none",
                "address": self.address}

    def stop_hotspot(self):
        self.calls.append(("stop_hotspot",))
        self.hotspot = None

    def connect(self, ssid, psk, timeout=60, keyfile_dir=None, interface=None):
        try:
            from . import nm as nm_module
        except ImportError:
            import nm as nm_module
        self.calls.append(("connect", ssid, bool(psk)))
        if self.behaviour == "bad-psk":
            # The same sentence the real adapter produces: nmcli's raw text is
            # classified at the boundary and never reaches the page or state.
            raise nm_module.NmError(nm_module.public_failure(
                "Secrets were required, but not provided.", 4))
        if self.behaviour == "no-uplink":
            raise nm_module.NmError("Joined the network but NetworkManager reports no uplink")
        if self.behaviour == "no-address":
            raise nm_module.NmError("Joined the network but received no usable address")
        self.joined = ssid
        return {"interface": self.interface, "address": "192.0.2.40",
                "gateway": "192.0.2.1", "routable": True, "has_route": True}

    def phases(self):
        """Just the verb of each call, which is what most assertions need."""
        return [call[0] for call in self.calls]

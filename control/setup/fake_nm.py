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
    """

    def __init__(self, interface="wlan0", country=None, behaviour="ok"):
        self.interface = interface
        self.country = country
        self.behaviour = behaviour
        self.calls = []
        self.hotspot = None
        self.joined = None
        self.hostname = None

    # -- identity -----------------------------------------------------------

    def set_hostname(self, hostname):
        self.calls.append(("set_hostname", hostname))
        self.hostname = hostname

    # -- radio --------------------------------------------------------------

    def wifi_interface(self):
        self.calls.append(("wifi_interface",))
        return self.interface

    def set_country(self, code):
        self.calls.append(("set_country", code))
        self.country = code

    def active(self):
        self.calls.append(("active",))
        if self.hotspot:
            return None
        if self.joined:
            return {"interface": self.interface, "address": "192.0.2.40",
                    "gateway": "192.0.2.1", "routable": True, "has_route": True}
        return None

    # -- transitions --------------------------------------------------------

    def start_hotspot(self, ssid, interface, password=None):
        self.calls.append(("start_hotspot", ssid, interface))
        self.hotspot = {"ssid": ssid, "interface": interface}

    def stop_hotspot(self):
        self.calls.append(("stop_hotspot",))
        self.hotspot = None

    def connect(self, ssid, psk, timeout=60):
        try:
            from . import nm as nm_module
        except ImportError:
            import nm as nm_module
        self.calls.append(("connect", ssid, bool(psk)))
        if self.behaviour == "bad-psk":
            raise nm_module.NmError("Secrets were required, but not provided.")
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

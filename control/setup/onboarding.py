"""First-boot onboarding: identity, then Wi-Fi, then a baseline.

The flow this implements, in the order it actually happens on a fresh card:

1. The device has no usable uplink. It sets a repeatable, hardware-derived
   hostname and raises a setup access point.
2. A phone joins that access point and opens the setup page. The page asks for a
   country (only when the radio needs one) and the household Wi-Fi.
3. On submit the page answers **before** the access point stops, because on a
   single-radio board the connection carrying that page is the one about to go
   away. The page says so in advance.
4. The access point stops, the device associates, and success is checked
   properly: an activated profile, a routable IPv4 address and a default route.
   Association alone is not success.
5. On failure the access point comes back with the reason, so the user can
   correct the password without a console.
6. On success the device stays on the network, records the address, and takes a
   configuration baseline.

Two things are deliberately not here: no reboot is ever used to "apply" Wi-Fi,
and no passphrase is stored in the setup state.
"""

from __future__ import annotations

import hashlib
import json
import logging
import os
import re
import socket
import threading
import time
from datetime import datetime, timezone
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path

try:  # imported as part of the package on a device
    from . import baseline as baseline_module
    from . import nm as nm_module
    from . import state as state_module
except ImportError:  # run as a flat directory, as the installer copies it
    import baseline as baseline_module
    import nm as nm_module
    import state as state_module

LOGGER = logging.getLogger(__name__)

HOTSPOT_PREFIX = "Debra-Setup"
PORTAL_PORT = 80
SUBMIT_INTERVAL_S = 5
MAX_ATTEMPTS = 10
# After the last allowed attempt the page waits this long instead of refusing
# for ever. A permanent refusal whose advice is "power-cycle" is a lockout: the
# counter lives in the state file, so a power cycle cannot clear it.
LOCKOUT_COOLDOWN_S = 600
SERIAL_PATHS = ("/sys/firmware/devicetree/base/serial-number",
                "/proc/device-tree/serial-number")
ASSETS = Path(__file__).resolve().parent / "assets"


def hostname_from_serial(serial):
    """`debra-` plus six hex characters of the board serial.

    Stable across re-flashes of the same board and different between boards,
    which is the point: a hostname that survives an SD card rewrite means the
    user does not have to find the device again. The serial is not a secret and
    is not a credential — it is printed on the board.
    """
    if not serial:
        return None
    cleaned = re.sub(r"[^0-9a-zA-Z]", "", str(serial))
    if len(cleaned) < 6:
        return None
    return "debra-" + cleaned[-6:].lower()


def read_serial(paths=SERIAL_PATHS):
    for path in paths:
        try:
            value = Path(path).read_bytes().decode("ascii", "ignore").strip("\x00 \n")
        except OSError:
            continue
        if value:
            return value
    return None


def _public_text(exc, limit=200):
    """One bounded line from an internal exception, safe to show a person."""
    text = " ".join(str(exc).split())
    return text[:limit] or exc.__class__.__name__


def hotspot_name(hostname):
    suffix = (hostname or "debra").split("-")[-1][:6]
    return f"{HOTSPOT_PREFIX}-{suffix}"


def hotspot_password(hostname):
    """The setup network's password, derived rather than stored.

    A WPA2 access point without a password is a network anyone in range can
    read, and `nmcli` silently generates a password nobody is ever shown, so
    the setup network cannot actually be joined. Deriving it from the device
    name means it can be printed on the card and read again without keeping a
    secret in the setup state. It protects the setup window, not the household:
    anyone holding the card during first boot can read it anyway.
    """
    seed = (hostname or "debra").encode("utf-8")
    return "debra-" + hashlib.sha256(seed).hexdigest()[:8]


class Onboarder:
    """Owns the phase transitions. All decisions live here, not in the portal."""

    def __init__(self, network, state_path, baseline_dir, hostname=None,
                 clock=time.monotonic, serial_paths=SERIAL_PATHS, root="/",
                 card_note_path=None, keyfile_dir=None):
        self.network = network
        self.hostname = hostname
        self.state_path = Path(state_path)
        self.baseline_dir = Path(baseline_dir)
        # Where the baseline reads from. A device uses "/"; anything that is not
        # a device must pass a fake root, or it copies real keyfiles.
        self.root = root
        self.clock = clock
        self.serial_paths = serial_paths
        # The boot-partition note a person can read before joining anything.
        self.card_note_path = Path(card_note_path) if card_note_path else None
        # Where a Wi-Fi profile is staged before NetworkManager loads it.
        self.keyfile_dir = Path(keyfile_dir) if keyfile_dir else None
        self._last_submit = 0.0
        self._lock = threading.Lock()

    # -- identity -----------------------------------------------------------

    def ensure_identity(self):
        """Set the hostname once, and keep it if it is already ours."""
        data = state_module.read(self.state_path)
        if data["hostname"]:
            return data["hostname"]
        hostname = (hostname_from_serial(read_serial(self.serial_paths))
                    or self.hostname
                    or hostname_from_serial(socket.gethostname()) or "debra")
        data["hostname"] = hostname
        state_module.write(self.state_path, data)
        try:
            self.network.set_hostname(hostname)
        except (AttributeError, nm_module.NmError):
            # A hostname that could not be applied is still recorded, so the
            # page shows the intended name rather than an empty field.
            LOGGER.warning("Hostname %s recorded but not applied", hostname)
        return hostname

    # -- phase transitions --------------------------------------------------

    def status(self):
        data = state_module.read(self.state_path)
        hotspot = data.get("hotspot")
        return {
            "phase": data["phase"],
            "hostname": data["hostname"],
            "country": data["country"],
            "ssid": data["ssid"],
            "address": data["address"],
            "last_error": data["last_error"],
            "attempts": data["attempts"],
            "baseline": data["baseline"],
            "baseline_error": data.get("baseline_error"),
            "hotspot": ({**hotspot,
                         "password": hotspot_password(data["hostname"])}
                        if hotspot else None),
            # The name, not the interface: an interface name there produced
            # http://wlan0/, which no browser can follow.
            "portal": (f"http://{data['hostname']}.local/" if data["hostname"] else None),
            "updated": data["updated"],
        }

    def start_hotspot(self, reason=None, phase="hotspot"):
        """Raise the setup access point and record it. Idempotent.

        `phase` is "failed" when this follows a failed attempt, so the page can
        show the reason and a retry instead of a blank form.
        """
        data = state_module.read(self.state_path)
        if not data["hostname"]:
            # Assign it into the record that is about to be written. Reading the
            # name from a separate call left this dict stale, and the write below
            # then wiped the hostname it had just set.
            data["hostname"] = self.ensure_identity()
        hostname = data["hostname"]
        try:
            interface = self.network.wifi_interface()
        except nm_module.NmError as exc:
            # A missing or broken nmcli used to escape this function and kill the
            # boot unit with a traceback. It is a failure the page can explain.
            data.update(phase="failed", last_error=str(exc))
            state_module.write(self.state_path, data)
            return self.status()
        if not interface:
            data.update(phase="failed", last_error="No Wi-Fi interface was found")
            state_module.write(self.state_path, data)
            return self.status()
        if not data["country"]:
            # A country is already set on most devices; asking for it again is
            # a question the user should not have to answer twice.
            try:
                detected = self.network.country()
            except (AttributeError, nm_module.NmError):
                detected = None
            if detected:
                data["country"] = detected
        name = hotspot_name(hostname)
        password = hotspot_password(hostname)
        try:
            self.network.start_hotspot(name, interface, password)
        except nm_module.NmError as exc:
            data.update(phase="failed", last_error=str(exc))
            state_module.write(self.state_path, data)
            return self.status()
        data.update(phase=phase, hotspot={"ssid": name, "interface": interface},
                    last_error=reason)
        state_module.write(self.state_path, data)
        self._write_card_note(name, password, hostname)
        return self.status()

    def _write_card_note(self, ssid, password, hostname):
        """Write the three things needed before any page can be loaded.

        Without the password the setup network cannot be joined at all, and a
        person with no console has no other way to learn it.
        """
        if self.card_note_path is None:
            return
        text = ("Debra setup\n\n"
                f"Wi-Fi network: {ssid}\n"
                f"Password:      {password}\n"
                f"Then open:     http://{hostname}.local/\n")
        try:
            self.card_note_path.parent.mkdir(parents=True, exist_ok=True)
            self.card_note_path.write_text(text, encoding="utf-8")
        except OSError as exc:
            LOGGER.warning("Setup note not written: %s", exc)

    def admit(self, ssid, psk, country=None):
        """Reserve the one in-flight attempt, or say why not.

        Two requests arriving together used to pass the same snapshot check and
        start two associations. Reserving under the lock closes that gap: the
        phase becomes `connecting` before the page is answered, so a second
        request sees a device that is already busy.
        """
        with self._lock:
            data = state_module.read(self.state_path)
            if self._locked_out(data):
                return False, "locked"
            if data["phase"] not in ("hotspot", "failed"):
                return False, "busy"
            if not data["hotspot"]:
                # A failed phase with no access point is a device that could not
                # raise one at all. There is nothing to hand over to, and the old
                # handler then crashed on `hotspot["ssid"]`.
                return False, "no-hotspot"
            if self.clock() - self._last_submit < SUBMIT_INTERVAL_S:
                return False, "throttle"
            if country and not data["country"]:
                try:
                    self.network.set_country(country)
                    data["country"] = country
                except nm_module.NmError as exc:
                    data.update(phase="failed", last_error=str(exc))
                    state_module.write(self.state_path, data)
                    return False, "country"
            # The page has already answered; from here the AP is expendable.
            # A capped counter starts again after the cooldown, so the retry
            # the page offers is always a retry that can work.
            self._last_submit = self.clock()
            data.update(phase="connecting", ssid=ssid, last_error=None,
                        attempts=min(data["attempts"], MAX_ATTEMPTS - 1) + 1,
                        last_attempt=state_module.now())
            state_module.write(self.state_path, data)
            return True, None

    def join(self, ssid, psk, country=None):
        """Admit and join in one call. The portal does the two steps separately."""
        accepted, _ = self.admit(ssid, psk, country)
        if not accepted:
            return self.status()
        return self.join_reserved(ssid, psk)

    def join_reserved(self, ssid, psk):
        """Do the slow part of a join that `admit()` already reserved."""
        data = state_module.read(self.state_path)
        if data["phase"] != "connecting" or data["ssid"] != ssid:
            # Something else moved the state on while this worker waited; the
            # reservation is no longer this worker's to use.
            LOGGER.warning("Join for %s abandoned: the device is no longer connecting", ssid)
            return self.status()

        try:
            self.network.stop_hotspot()
        except nm_module.NmError:
            # Losing the AP cleanup is not a reason to abandon the join.
            LOGGER.warning("Setup access point did not stop cleanly")

        try:
            active = self.network.connect(ssid, psk)
        except nm_module.NmError as exc:
            return self.start_hotspot(reason=str(exc), phase="failed")

        data = state_module.read(self.state_path)
        data.update(phase="online", ssid=ssid, address=active["address"],
                    hotspot=None, last_error=None, attempts=0, last_attempt=None)
        state_module.write(self.state_path, data)
        self._capture_baseline()
        return self.status()

    def _locked_out(self, data):
        """True while the capped attempt counter is cooling down."""
        if data["attempts"] < MAX_ATTEMPTS:
            return False
        try:
            when = datetime.strptime(data.get("last_attempt") or "",
                                     "%Y-%m-%dT%H:%M:%SZ").replace(tzinfo=timezone.utc)
        except ValueError:
            return False
        age = (datetime.now(timezone.utc) - when).total_seconds()
        return age < LOCKOUT_COOLDOWN_S

    def _capture_baseline(self):
        """One baseline, once. Called after a join and on every online boot.

        The record is re-read after the capture rather than written back from
        before it: a capture takes time, and the phase or the address may have
        changed while it ran.
        """
        if state_module.read(self.state_path)["baseline"]:
            return
        try:
            manifest = baseline_module.capture(self.baseline_dir, root=self.root)
        except (baseline_module.BaselineError, OSError) as exc:
            # A missing baseline must not undo a working network, but it must be
            # visible: "not captured yet" with no reason reads as progress that
            # is not happening.
            LOGGER.warning("Baseline not captured: %s", exc)
            try:
                data = state_module.read(self.state_path)
                data["baseline_error"] = _public_text(exc)
                state_module.write(self.state_path, data)
            except (OSError, ValueError):
                LOGGER.warning("Baseline error could not be recorded")
            return
        data = state_module.read(self.state_path)
        data["baseline"] = str(self.baseline_dir / manifest["archive"])
        data["baseline_error"] = None
        state_module.write(self.state_path, data)

    def resume(self):
        """Decide what a boot looks like, from the recorded state."""
        data = state_module.read(self.state_path)
        if not data["hostname"]:
            self.ensure_identity()
            data = state_module.read(self.state_path)
        active = self.network.active()
        if active and active["routable"] and active.get("has_route", True):
            data = state_module.read(self.state_path)
            if data["phase"] != "online" or data["address"] != active["address"]:
                data.update(phase="online", address=active["address"], hotspot=None)
                state_module.write(self.state_path, data)
            # A device can be online without ever having taken its baseline: it
            # was already connected at boot, or the capture died with the power.
            # The baseline is a milestone, not a side effect of joining, so a
            # boot retries it instead of leaving the gap for ever.
            self._capture_baseline()
            return self.status()
        if data["phase"] == "online":
            # Was online and is not now: say so, and offer the setup point again
            # rather than waiting for a console.
            return self.start_hotspot(reason="The previous network is not reachable", phase="failed")
        if data["phase"] == "connecting":
            return self.start_hotspot(reason="The last attempt did not finish", phase="failed")
        return self.start_hotspot()


class Portal(ThreadingHTTPServer):
    """The setup page, reachable only on the access point's own address."""

    daemon_threads = True
    request_queue_size = 8
    allow_reuse_address = True

    def __init__(self, address, onboarder, page):
        self.onboarder = onboarder
        self.page = page
        self.host = f"{address[0]}:{address[1]}" if address[1] != 80 else address[0]
        super().__init__(address, PortalHandler)


class PortalHandler(BaseHTTPRequestHandler):
    server_version = "DebraSetup/1"
    sys_version = ""

    def log_message(self, fmt, *args):
        LOGGER.info("portal %s", fmt % args)

    def _reply(self, code, body, content_type="application/json"):
        payload = body if isinstance(body, bytes) else json.dumps(body).encode()
        self.send_response(code)
        self.send_header("Content-Type", content_type)
        self.send_header("Content-Length", str(len(payload)))
        self.send_header("Cache-Control", "no-store")
        self.send_header("X-Content-Type-Options", "nosniff")
        self.end_headers()
        self.wfile.write(payload)

    def _same_origin(self):
        """Refuse a Host that is not this portal, so a rebinding attack fails."""
        host = (self.headers.get("Host") or "").strip().lower()
        if host not in (self.server.host.lower(), self.server.host.split(":")[0].lower()):
            return False
        return self.headers.get("Sec-Fetch-Site") != "cross-site"

    def do_GET(self):
        if self.path == "/api/status":
            if not self._same_origin():
                self._reply(403, {"error": "Unrecognized host"})
                return
            self._reply(200, self.server.onboarder.status())
            return
        if self.path == "/setup.js":
            if not self._same_origin():
                self._reply(403, {"error": "Unrecognized host"})
                return
            try:
                script = (self.server.page.parent / "setup.js").read_bytes()
            except OSError:
                self._reply(404, {"error": "Not found"})
                return
            self._reply(200, script, "text/javascript; charset=utf-8")
            return
        if self.path not in ("/", "/index.html"):
            self._reply(404, {"error": "Not found"})
            return
        if not self._same_origin():
            self._reply(403, {"error": "Unrecognized host"})
            return
        try:
            page = self.server.page.read_bytes()
        except OSError:
            self._reply(500, {"error": "Setup page is missing"})
            return
        self._reply(200, page, "text/html; charset=utf-8")

    def do_POST(self):
        if self.path != "/api/join":
            self._reply(404, {"error": "Not found"})
            return
        if not self._same_origin():
            self._reply(403, {"error": "Unrecognized host"})
            return
        lengths = self.headers.get_all("Content-Length", [])
        if (len(lengths) != 1 or self.headers.get_all("Transfer-Encoding") is not None
                or not re.fullmatch(r"[0-9]+", lengths[0] or "")):
            self._reply(400, {"error": "One Content-Length is required"})
            return
        length = int(lengths[0])
        if not 0 < length <= 1024:
            self._reply(413, {"error": "Request must be 1-1024 bytes"})
            return
        try:
            body = json.loads(self.rfile.read(length))
        except (ValueError, OSError):
            self._reply(400, {"error": "Expected a JSON object"})
            return
        if not isinstance(body, dict) or set(body) - {"ssid", "psk", "country"}:
            self._reply(400, {"error": "Expected ssid, psk and country only"})
            return
        ssid, psk, country = body.get("ssid"), body.get("psk"), body.get("country")
        if not nm_module.valid_ssid(ssid):
            self._reply(400, {"error": "Network name must be 1-32 printable characters"})
            return
        if psk is not None and psk != "" and not nm_module.valid_psk(psk):
            self._reply(400, {"error": "Wi-Fi password must be 8-63 characters"})
            return
        if country is not None and not nm_module.valid_country(country):
            self._reply(400, {"error": "Country must be two capital letters"})
            return
        # Reserve the attempt *before* answering. Two requests arriving together
        # used to pass the same snapshot check and start two associations; the
        # reservation makes the second one see a device that is already busy.
        accepted, reason = self.server.onboarder.admit(ssid, psk or None, country)
        if not accepted:
            if reason == "locked":
                # The counter is in the state file, so a power cycle cannot clear
                # it. The advice has to be the wait that actually works.
                self._reply(429, {"error": "Too many attempts. Wait ten minutes, "
                                           "then try again."})
            elif reason == "throttle":
                self._reply(429, {"error": "One attempt every few seconds. "
                                           "Try again shortly."})
            elif reason in ("busy", "no-hotspot"):
                self._reply(409, {"error": "The device is not waiting for setup right now"})
            else:
                self._reply(400, {"error": "The country could not be set"})
            return
        status = self.server.onboarder.status()
        # Answer before the network goes away: this reply is the last thing the
        # browser can receive over the setup access point.
        self._reply(202, {"status": "connecting", "ssid": ssid,
                          "hotspot": (status.get("hotspot") or {}).get("ssid")})
        worker = threading.Thread(target=self.server.onboarder.join_reserved,
                                  args=(ssid, psk or None), daemon=True,
                                  name="debra-onboarding")
        worker.start()


def serve(onboarder, page=None, address=("10.42.0.1", PORTAL_PORT)):
    page = page or ASSETS / "setup.html"
    return Portal(address, onboarder, page)

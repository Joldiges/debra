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
and no household passphrase is stored in the setup state. The setup network's
own password is a separate owner-only file, because the note on the boot
partition has to keep working across retries and the status API must not
become a second place to read it from.

How that network is protected, open or password, is a choice the person can
change from the page itself without a reinstall. The choice is kept in a second
owner-only file beside the password and read at every start; the status API
reports the mode, never the password, and the one place the password is served
is the reply to the request that turned the password on.
"""

from __future__ import annotations

import errno
import json
import logging
import os
import re
import secrets
import socket
import tempfile
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
# What NetworkManager's shared mode usually assigns, and the fallback when the
# access point's own address cannot be read.
DEFAULT_PORTAL_ADDRESS = "10.42.0.1"
# How the setup access point is protected:
#   "wpa"   a random per-device password, delivered on the boot-partition note
#   "none"  deliberately open, for a development build
# "none" is a mode a person chooses, never something a device falls into because
# a value was missing: an unknown mode is refused, and this default is written
# into the unit and reported by the page.
SETUP_SECURITY = ("wpa", "none")

# Where Debra is today, not where it ships. During development the setup network
# comes up open, so nothing has to be read off a card before a page can be
# reached; the protected mode stays implemented and tested and is one flag away
# (`--setup-security wpa`, or the button on the setup page). Changing this line
# to "wpa" is the release decision, and every test that names the default reads
# it from here rather than repeating the word.
DEFAULT_SETUP_SECURITY = "none"
# Unambiguous when read off a card and typed into a phone: no 0/O, 1/l/I.
SECRET_ALPHABET = "abcdefghjkmnpqrstuvwxyz23456789"
SECRET_CHARS = 12
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


def _baseline_reason(exc):
    """One fixed sentence about why a baseline was not captured.

    The exception's own text is not used: an OSError carries the path it failed
    on, and a person reading the setup page has no use for the device's layout.
    The journal keeps the detail.
    """
    if isinstance(exc, baseline_module.BaselineError):
        return "The device state is larger than one baseline can hold"
    if isinstance(exc, PermissionError):
        return "Some device files could not be read"
    if getattr(exc, "errno", None) == errno.ENOSPC:
        return "The device is out of disk space"
    return "The device state could not be saved"


def hotspot_name(hostname):
    suffix = (hostname or "debra").split("-")[-1][:6]
    return f"{HOTSPOT_PREFIX}-{suffix}"


def setup_secret(secret_path):
    """The setup network's password: random, kept on the device, stable.

    It used to be derived from the device name, which made `Debra-Setup-345678`
    hand anyone in range the password - a hash of public information is not a
    secret, it is the same information in different letters. This one is drawn
    from the system random source and reaches the person only through the note
    on the boot partition.

    It is kept so that the note stays true: the access point is raised again
    after a failed join, and a fresh password each time would strand a person
    holding a note that had already been read.
    """
    path = Path(secret_path)
    try:
        saved = path.read_text(encoding="utf-8").strip()
    except FileNotFoundError:
        saved = ""
    except OSError as exc:
        # Readable is not required for a good password, only for the same one
        # twice. Say so in the journal and carry on with a fresh one.
        LOGGER.warning("Setup secret could not be read: %s", exc)
        saved = ""
    if saved:
        return saved
    secret = "".join(secrets.choice(SECRET_ALPHABET) for _ in range(SECRET_CHARS))
    try:
        path.parent.mkdir(parents=True, exist_ok=True, mode=0o700)
        fd = os.open(path, os.O_WRONLY | os.O_CREAT | os.O_EXCL, 0o600)
        with os.fdopen(fd, "w", encoding="utf-8") as stream:
            stream.write(secret + "\n")
            stream.flush()
            os.fsync(stream.fileno())
    except FileExistsError:
        # Another process wrote one first: that is the one the note will carry.
        try:
            return path.read_text(encoding="utf-8").strip() or secret
        except OSError:
            return secret
    except OSError as exc:
        LOGGER.warning("Setup secret could not be kept: %s", exc)
    return secret


class Onboarder:
    """Owns the phase transitions. All decisions live here, not in the portal."""

    def __init__(self, network, state_path, baseline_dir, hostname=None,
                 clock=time.monotonic, serial_paths=SERIAL_PATHS, root="/",
                 card_note_path=None, keyfile_dir=None,
                 security=DEFAULT_SETUP_SECURITY,
                 secret_path=None, security_path=None):
        if security not in SETUP_SECURITY:
            # A typo in an install argument must not quietly become an open
            # network: say no at the boundary instead of choosing for someone.
            raise ValueError(f"security must be one of {', '.join(SETUP_SECURITY)}")
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
        # The setup network's password. Next to the state, owner-only, and
        # never in the state itself: that file is reported by the API.
        self.secret_path = (Path(secret_path) if secret_path
                            else self.state_path.with_name("setup-secret"))
        # Where the person's choice of mode is kept. Next to the password and
        # deliberately not inside setup.json: that record is closed and
        # validated, so a new key there would make every existing state file
        # unreadable on the next boot.
        self.security_path = (Path(security_path) if security_path
                              else self.state_path.with_name("setup-security"))
        # The installed mode is the default a device comes up with, not an
        # override of what somebody chose on the page: the stored mode wins
        # because it is the later decision, and it is what the card note, the
        # running access point and this field all have to agree about.
        self.security = self._stored_security() or security
        self._last_submit = 0.0
        self._lock = threading.Lock()
        # Read from the owner-only file once, so the reply that turns the
        # password on and the access point it is turned on with cannot disagree.
        self._password = None
        # Nearby networks, scanned while the radio is free. Kept in memory: it
        # is a convenience for the form, not state the device should remember.
        self._networks = []
        # The address the setup page is served on, read from the access point
        # once it is up. None until then, so the fallback is explicit.
        self._portal_address = None

    # -- identity -----------------------------------------------------------

    def ensure_identity(self):
        """Choose the device name once, and apply it every time.

        The name is chosen once. Applying it is idempotent and is retried on
        every boot: a name that `hostnamectl` failed to take on the first boot
        used to be remembered as done, so the page advertised a name the device
        never answered to and no later boot repaired it.
        """
        data = state_module.read(self.state_path)
        if data["hostname"]:
            try:
                self.network.set_hostname(data["hostname"])
            except (AttributeError, nm_module.NmError) as exc:
                LOGGER.warning("Device name recorded but not applied: %s", exc)
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
            # No password here. It used to be, because it was derived from the
            # device name and so was already public; a real secret is read off
            # the card, and this response is served to anyone who has joined.
            "hotspot": hotspot,
            # So the page can say so plainly when the setup network is open.
            "security": self.security,
            # The address the page is actually served on. A `.local` name here
            # was rejected by the portal's own same-origin check.
            "portal": (f"http://{self._portal_address or DEFAULT_PORTAL_ADDRESS}/"
                       if hotspot else None),
            # Names the device could see before it raised its own network, so
            # the form can offer them instead of making a beginner type one.
            # Empty is normal and means "type it".
            "networks": list(self._networks),
            "updated": data["updated"],
        }

    def start_hotspot(self, reason=None, phase="hotspot", rescan=True):
        """Raise the setup access point and record it. Idempotent.

        `phase` is "failed" when this follows a failed attempt, so the page can
        show the reason and a retry instead of a blank form.

        `rescan` is False on that failure path. The access point is about to be
        raised again, and a scan can take tens of seconds, so scanning there
        would leave the person disconnected with no page for that long. The list
        from the first boot is still in memory and still useful.
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
        if rescan and not data["hotspot"]:
            # The radio is still free here, which is the only safe moment to
            # scan: asking for a scan with the access point up can drop the
            # person's phone off it.
            self.refresh_networks(interface)
        name = hotspot_name(hostname)
        password = setup_secret(self.secret_path) if self.security == "wpa" else None
        raised = None
        try:
            raised = self.network.start_hotspot(name, interface, password)
        except nm_module.NmError as exc:
            data.update(phase="failed", last_error=str(exc))
            state_module.write(self.state_path, data)
            return self.status()
        # The adapter reads the address back from the access point it just
        # verified, which is the real one rather than a guess. An adapter that
        # only says it raised the network gets asked separately.
        address = raised.get("address") if isinstance(raised, dict) else None
        self._portal_address = address or self._device_address(interface)
        data.update(phase=phase, hotspot={"ssid": name, "interface": interface},
                    last_error=reason)
        state_module.write(self.state_path, data)
        self._write_card_note(name, password, hostname)
        return self.status()

    def refresh_networks(self, interface=None):
        """Look for nearby networks while the radio is free. Never raises.

        The result is a convenience for the form, not state: an empty list is a
        normal answer, and the page then falls back to typing the name.
        """
        scan = getattr(self.network, "scan", None)
        try:
            found = scan(interface) if callable(scan) else []
        except nm_module.NmError:
            found = []
        self._networks = list(found or [])
        return self._networks

    def announce_portal(self, address):
        """Record the address the page is actually bound to, and reprint the note.

        The note and the status are written when the access point comes up, so
        they carry the address the radio reported then. If the page ends up
        listening somewhere else, that is the address a person has to type:
        a URL the portal's own same-origin check rejects is a dead end at the
        first step of setup.
        """
        if not address:
            return
        self._portal_address = address
        try:
            data = state_module.read(self.state_path)
        except (OSError, ValueError):
            return
        hotspot = data.get("hotspot")
        if not hotspot:
            return
        self._write_card_note(hotspot.get("ssid") or hotspot_name(data["hostname"]),
                              self._hotspot_password(), data["hostname"])

    def _hotspot_password(self):
        """The setup network's password, or None for a deliberately open build.

        One decision, used both when the access point is raised and when the
        note is reprinted with the address the page really bound to. Two copies
        of it could disagree, and a note describing the previous access point
        is worse than no note.

        Read once per process. `setup_secret` draws a new password when the file
        cannot be written, and the reply that turns the password on serves the
        one it read: two reads in the same breath would then hand the person a
        password the access point is not using.
        """
        if self.security != "wpa":
            return None
        if self._password is None:
            self._password = setup_secret(self.secret_path)
        return self._password

    def _write_card_note(self, ssid, password, hostname):
        """Write the three things needed before any page can be loaded.

        Without the password the setup network cannot be joined at all, and a
        person with no console has no other way to learn it. A development
        build has no password to give, and says so rather than leaving the line
        out, which would read as an incomplete note.

        The address is the one the page is served on, not `<hostname>.local`.
        The portal's same-origin check admits only the address it was given, so
        the printed `.local` name returned 403 to the person following it.
        """
        if self.card_note_path is None:
            return
        address = self._portal_address or DEFAULT_PORTAL_ADDRESS
        # A note written onto the root filesystem is not on the card: the person
        # holding it in a reader would see nothing. The write below succeeds
        # either way, so this is the only place the difference can be seen.
        try:
            if not os.path.ismount(self.card_note_path.parent):
                LOGGER.warning("The setup note is not on a mounted boot partition")
        except OSError:
            pass
        if password:
            password_line = f"Password:      {password}\n"
        else:
            password_line = "Password:      none (development build)\n"
        text = ("Debra setup\n\n"
                f"Wi-Fi network: {ssid}\n"
                f"{password_line}"
                f"Then open:     http://{address}/\n")
        try:
            self.card_note_path.parent.mkdir(parents=True, exist_ok=True)
            self.card_note_path.write_text(text, encoding="utf-8")
        except OSError as exc:
            # The class only: an OSError carries the path it failed on, and the
            # note names a credential.
            LOGGER.warning("Setup note not written: %s", exc.__class__.__name__)

    def _device_address(self, interface):
        """The address the access point holds, or None. Never raises.

        One place, because the note, the status and the address comparison after
        a re-raise have to agree about where the page is. An adapter that cannot
        answer is not a failure here: the documented default is what the note
        falls back to, and that is a guess, not an error.
        """
        try:
            return self.network.device_address(interface)
        except (AttributeError, nm_module.NmError):
            return None

    # -- how the setup network is protected ---------------------------------

    def _stored_security(self):
        """The mode the person chose on the page, if there is one.

        A file in a state directory can hold anything, so an unknown value is
        not a mode: it is read as "no choice" and the installed default applies.
        The value is not repeated into the journal - it is not a credential, but
        a hand-edited file is not text for a log either.
        """
        try:
            stored = self.security_path.read_text(encoding="utf-8").strip()
        except FileNotFoundError:
            return None
        except OSError as exc:
            LOGGER.warning("The stored setup network mode could not be read: %s", exc)
            return None
        if stored in SETUP_SECURITY:
            return stored
        LOGGER.warning("The stored setup network mode is not one of %s; "
                       "using the installed default", ", ".join(SETUP_SECURITY))
        return None

    def _write_security(self, mode):
        """Replace the stored mode, owner-only, in one rename.

        Atomic for the same reason the state file is: a mode lost half-written
        reads back as neither, and the person is then told the setup network is
        one thing while the device does another.
        """
        path = self.security_path
        path.parent.mkdir(parents=True, exist_ok=True, mode=0o700)
        fd, staged = tempfile.mkstemp(prefix=".setup-security-", dir=path.parent)
        try:
            with os.fdopen(fd, "w", encoding="utf-8") as stream:
                stream.write(mode + "\n")
                stream.flush()
                os.fsync(stream.fileno())
            os.chmod(staged, 0o600)
            os.replace(staged, path)
        except BaseException:
            try:
                os.unlink(staged)
            except OSError:
                pass
            raise

    def set_security(self, mode):
        """Choose how the setup network is protected, and keep the choice.

        The argument is the mode, never a password: the password is drawn on the
        device and reused, and the mode is the part the next boot needs. Nothing
        here touches the radio - the page is answered first, and `rearm_hotspot`
        is the half that runs afterwards, exactly as `admit` and
        `join_reserved` split a join.
        """
        if mode not in SETUP_SECURITY:
            raise ValueError(f"security must be one of {', '.join(SETUP_SECURITY)}")
        with self._lock:
            self._write_security(mode)
            self.security = mode
        return mode

    def hotspot_running(self):
        """True while there is an access point to take down and raise again."""
        data = state_module.read(self.state_path)
        return data["phase"] in ("hotspot", "failed") and bool(data["hotspot"])

    def rearm_hotspot(self):
        """Raise the access point again, in whichever mode is current now.

        This is the half that runs after the page has been answered, so the only
        browser that asked for it is already gone. Every failure is recorded
        rather than raised: a traceback in a worker thread leaves the device in
        a mode nobody has been told about.

        The access point is not taken down here first. The adapter rewrites the
        profile it already has and cycles that same connection, because a
        deleted and recreated shared connection is handed the next subnet and
        the page is bound to the address the first one gave. What has to be
        checked is whether the address moved anyway, not assumed either way.
        """
        data = state_module.read(self.state_path)
        if not (data["phase"] in ("hotspot", "failed") and data["hotspot"]):
            # Something moved the device on while the reply was being written:
            # a join is in flight, and raising an access point over it would
            # take the radio away from the association it is making.
            LOGGER.warning("The setup network was not raised again: "
                           "the device is no longer waiting for setup")
            return self.status()
        interface = data["hotspot"].get("interface")
        before = self._device_address(interface)
        self.start_hotspot(rescan=False)
        after = self._portal_address
        if before and after and before != after:
            # The page is still bound to the address it was opened on, so it is
            # now unreachable from the network it serves. Only a restart of the
            # service moves the socket; until someone does that, the state has
            # to say so instead of reading as a normal change.
            message = (f"The setup network moved from {before} to {after}, and the "
                       "page is still listening on the old address")
            LOGGER.warning("%s; restart the setup service to move it", message)
            try:
                data = state_module.read(self.state_path)
                data["last_error"] = message
                state_module.write(self.state_path, data)
            except (OSError, ValueError):
                LOGGER.warning("The moved setup network address could not be recorded")
        return self.status()

    def admit(self, ssid):
        """Reserve the one in-flight attempt, or say why not.

        Two requests arriving together used to pass the same snapshot check and
        start two associations. Reserving under the lock closes that gap: the
        phase becomes `connecting` before the page is answered, so a second
        request sees a device that is already busy.

        Returns `(True, token)` or `(False, reason)`. The token identifies this
        particular attempt, so a worker whose reservation was superseded can
        tell - the SSID alone cannot, because the same network can be tried
        again with a corrected password.

        Nothing here touches the radio. The country used to be set inside this
        lock, before the reply was written, which could delay or disrupt the
        only channel the person has.
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
            # A capped counter starts again after the cooldown, so the retry the
            # page offers is always a retry that can work.
            self._last_submit = self.clock()
            # The token is random, not the timestamp: `last_attempt` has
            # one-second resolution and a retry can land in the same second as
            # the attempt it replaces.
            token = secrets.token_hex(8)
            data.update(phase="connecting", ssid=ssid, last_error=None,
                        attempts=min(data["attempts"], MAX_ATTEMPTS - 1) + 1,
                        last_attempt=state_module.now(), attempt_token=token)
            state_module.write(self.state_path, data)
            return True, token

    def release(self, token):
        """Undo a reservation whose reply never reached the browser.

        Without this, a client that disconnects between the reservation and the
        reply leaves the device `connecting` for ever in this process, and every
        later submission is refused as busy.
        """
        with self._lock:
            data = state_module.read(self.state_path)
            if data["phase"] != "connecting" or data["attempt_token"] != token:
                return
            if data["attempt_claimed"]:
                # A worker has already taken this reservation and stopped the
                # access point. Cancelling it here would leave the device with
                # no radio state and no worker to fix it.
                LOGGER.warning("Reservation was already claimed; not released")
                return
            data.update(phase="hotspot" if data["hotspot"] else "failed",
                        ssid=None, last_attempt=None, attempt_token=None,
                        attempts=max(0, data["attempts"] - 1))
            state_module.write(self.state_path, data)

    def join(self, ssid, psk, country=None):
        """Admit and join in one call. The portal does the two steps separately."""
        accepted, token = self.admit(ssid)
        if not accepted:
            return self.status()
        return self.join_reserved(ssid, psk, country, token=token)

    def _claim(self, ssid, token):
        """Take exclusive ownership of a reservation, or return None.

        Checking a token and then acting on it is not ownership: two workers
        holding the same valid token both passed the check and both joined. The
        claim is set under the lock that `admit()` uses, before any radio call,
        and a second worker with the same token finds it already claimed.
        """
        with self._lock:
            data = state_module.read(self.state_path)
            if (not token or data["phase"] != "connecting" or data["ssid"] != ssid
                    or data["attempt_token"] != token or data["attempt_claimed"]):
                return None
            data["attempt_claimed"] = True
            state_module.write(self.state_path, data)
            return data

    def _settle(self, token, **fields):
        """Write a transition only while this worker still owns the attempt."""
        with self._lock:
            data = state_module.read(self.state_path)
            if not token or data["attempt_token"] != token:
                return None
            data.update(attempt_claimed=False, attempt_token=None, **fields)
            state_module.write(self.state_path, data)
            return data

    def join_reserved(self, ssid, psk, country=None, token=None):
        """Do the slow part of a join that `admit()` already reserved.

        `token` is required. Without it a caller could skip the ownership check
        entirely, which is how a superseded worker used to join and then clear a
        newer reservation's state.
        """
        data = self._claim(ssid, token)
        if data is None:
            # Something else moved the state on while this worker waited; the
            # reservation is no longer this worker's to use. Checking the token
            # as well as the SSID matters: the same network can be retried with
            # a corrected password, and the old worker must not win that race.
            LOGGER.warning("Join for %s abandoned: the reservation is no longer current", ssid)
            return self.status()

        try:
            self.network.stop_hotspot()
        except nm_module.NmError:
            # Losing the AP cleanup is not a reason to abandon the join.
            LOGGER.warning("Setup access point did not stop cleanly")

        # The country is a radio change, so it happens after the page has been
        # answered and the access point is already down. A failure here is a
        # normal failure with a reason, not a broken reply.
        if country and not data["country"]:
            try:
                self.network.set_country(country)
                data = state_module.read(self.state_path)
                data["country"] = country
                state_module.write(self.state_path, data)
            except nm_module.NmError as exc:
                return self._fail(token, str(exc))

        try:
            active = self.network.connect(
                ssid, psk, keyfile_dir=self.keyfile_dir,
                interface=(data.get("hotspot") or {}).get("interface"))
        except nm_module.NmError as exc:
            return self._fail(token, str(exc))

        # Settlement rechecks ownership under the same lock the claim used. A
        # worker that was superseded while it was associating - the person
        # retried after a slow attempt - must not report its result as the
        # current attempt's, and must not clear the newer reservation's token.
        settled = self._settle(token, phase="online", ssid=ssid,
                               address=active["address"], hotspot=None,
                               last_error=None, attempts=0, last_attempt=None)
        if settled is None:
            LOGGER.warning("Join for %s finished but the attempt was no longer current", ssid)
            return self.status()
        self._capture_baseline()
        return self.status()

    def _fail(self, token, reason):
        """Record a failed attempt that this worker still owns, then retry the AP."""
        # `last_attempt` is kept: it is the time the capped counter last
        # started, and the cooldown is measured from it. Clearing it here made
        # the cap never apply, because the record no longer said when.
        settled = self._settle(token, phase="failed", last_error=reason, ssid=None)
        if settled is None:
            return self.status()
        return self.start_hotspot(reason=reason, phase="failed", rescan=False)

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
        data = state_module.read(self.state_path)
        pointer = data["baseline"]
        if pointer:
            # A saved pointer is only a baseline if its archive still hashes to
            # what its manifest says. Existence is not verification: an empty or
            # truncated file at the recorded path made the page report a
            # known-good point that `latest()` already knew was unusable, and
            # nothing ever retried.
            if baseline_module.verified(self.baseline_dir, pointer):
                return
            LOGGER.warning("The recorded baseline does not verify; looking for a whole one")
            try:
                data["baseline"] = None
                data["baseline_error"] = "The saved baseline is damaged, so it is not a recovery point"
                state_module.write(self.state_path, data)
            except (OSError, ValueError):
                pass
        # A capture whose pointer could not be written leaves a complete
        # baseline on disk with nothing pointing at it. Adopt it rather than
        # capturing another, especially when the disk is why the write failed.
        existing = baseline_module.latest(self.baseline_dir)
        if existing:
            try:
                data = state_module.read(self.state_path)
                data["baseline"] = str(self.baseline_dir / existing["archive"])
                data["baseline_error"] = None
                state_module.write(self.state_path, data)
                LOGGER.warning("Adopted an existing baseline that had no recorded pointer")
                return
            except (OSError, ValueError):
                # Recording it failed again; carry on and capture as before so
                # the failure is visible instead of silent.
                LOGGER.warning("An existing baseline could not be recorded")
        try:
            manifest = baseline_module.capture(self.baseline_dir, root=self.root)
        except (baseline_module.BaselineError, OSError) as exc:
            # A missing baseline must not undo a working network, but it must be
            # visible: "not captured yet" with no reason reads as progress that
            # is not happening.
            # The fixed sentence, not the exception. `str(exc)` is the thing the
            # review showed carrying a path, and a path here can name a
            # credential-bearing file.
            LOGGER.warning("Baseline not captured: %s", _baseline_reason(exc))
            try:
                data = state_module.read(self.state_path)
                data["baseline_error"] = _baseline_reason(exc)
                state_module.write(self.state_path, data)
            except (OSError, ValueError):
                LOGGER.warning("Baseline error could not be recorded")
            return
        # The capture succeeded; recording that must not be the step that
        # throws. A full disk here used to escape the handler, leave the error
        # field empty and look like nothing had happened.
        try:
            data = state_module.read(self.state_path)
            data["baseline"] = str(self.baseline_dir / manifest["archive"])
            data["baseline_error"] = None
            state_module.write(self.state_path, data)
        except (OSError, ValueError) as exc:
            reason = _baseline_reason(exc)
            LOGGER.warning("Baseline captured but not recorded: %s", reason)
            # The page must not say "captured" when nothing points at it. The
            # write may fail again - a full disk is the likely cause - but a
            # silent gap is what the review found, so it is attempted.
            try:
                data = state_module.read(self.state_path)
                data["baseline_error"] = reason
                state_module.write(self.state_path, data)
            except (OSError, ValueError):
                LOGGER.warning("The baseline failure could not be recorded")

    def resume(self):
        """Decide what a boot looks like, from the recorded state."""
        # Applied on every boot, not only when the name is missing. The name is
        # saved before it is applied, so a `hostnamectl` failure left a non-empty
        # name and every later boot skipped the retry: the page advertised a name
        # the device never answered to, and fixing the tool did not fix the
        # device. Reconciling is idempotent and never changes the chosen name.
        self.ensure_identity()
        data = state_module.read(self.state_path)
        active = self.network.active()
        if active and active["routable"] and active.get("has_route", True):
            data = state_module.read(self.state_path)
            previous = data["phase"]
            if previous != "online" or data["address"] != active["address"]:
                # Adopting an already-connected network is not the same event as
                # completing a join: there is no attempt in flight, no error and
                # no reservation. Leaving those fields behind made a later worker
                # look current, and made the online label claim a join that this
                # boot never performed.
                data.update(phase="online", address=active["address"], hotspot=None,
                            last_error=None, attempts=0, last_attempt=None,
                            attempt_token=None, attempt_claimed=False)
                if previous != "online":
                    # The network name is only known from a join this device
                    # performed. Guessing one here would be a claim.
                    data["ssid"] = None
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


# The addresses phones and laptops probe to decide whether they are behind a
# captive portal. Answering with a redirect is what makes the operating system
# offer to open this page; without it a person has to read an address off the
# card and type it, which is the step most likely to lose them.
#
# Whether the probe ever arrives is a separate question, and an open one: the
# setup network's DNS has to resolve these names to the access point. Network
# Manager's shared mode does not promise that, so this is a best-effort
# improvement, not a captive portal that has been demonstrated on a phone.
CAPTIVE_PROBES = frozenset({
    "/generate_204",       # Android
    "/gen_204",            # Android, older
    "/hotspot-detect.html",  # Apple
    "/library/test/success.html",  # Apple, older
    "/connecttest.txt",    # Windows
    "/ncsi.txt",           # Windows
    "/redirect",           # Windows
    "/canonical.html",     # Firefox
    "/success.txt",        # Firefox
})


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

    def _portal_url(self):
        """The address this page is served on, built from the bind, not the Host.

        The Host header is attacker-controlled: reflecting it would make this an
        open redirect, and a phone would then be sent somewhere else entirely.
        """
        return f"http://{self.server.host}/"

    def _redirect_to_page(self, body=True):
        payload = (f'<!doctype html><meta http-equiv="refresh" '
                   f'content="0;url={self._portal_url()}">'
                   f'<a href="{self._portal_url()}">Set up this device</a>\n').encode()
        self.send_response(302)
        self.send_header("Location", self._portal_url())
        self.send_header("Content-Type", "text/html; charset=utf-8")
        self.send_header("Content-Length", str(len(payload)))
        self.send_header("Cache-Control", "no-store")
        self.end_headers()
        if body:
            self.wfile.write(payload)

    def do_HEAD(self):
        if self.path.split("?")[0] in CAPTIVE_PROBES:
            self._redirect_to_page(body=False)
            return
        self.send_response(404)
        self.send_header("Content-Length", "0")
        self.end_headers()

    def do_GET(self):
        if self.path.split("?")[0] in CAPTIVE_PROBES:
            # Deliberately before the same-origin check: the operating system
            # asks for these paths with its own host name, not ours.
            self._redirect_to_page()
            return
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

    def _json_body(self):
        """The one JSON object this POST carries, or None after replying itself.

        Both POST paths take a small object and neither can do anything useful
        without it, so the framing rules live here once rather than in two
        copies that could drift apart.
        """
        lengths = self.headers.get_all("Content-Length", [])
        if (len(lengths) != 1 or self.headers.get_all("Transfer-Encoding") is not None
                or not re.fullmatch(r"[0-9]+", lengths[0] or "")):
            self._reply(400, {"error": "One Content-Length is required"})
            return None
        length = int(lengths[0])
        if not 0 < length <= 1024:
            self._reply(413, {"error": "Request must be 1-1024 bytes"})
            return None
        try:
            return json.loads(self.rfile.read(length))
        except (ValueError, OSError):
            self._reply(400, {"error": "Expected a JSON object"})
            return None

    def do_POST(self):
        path = self.path.split("?")[0]
        if path not in ("/api/join", "/api/security"):
            self._reply(404, {"error": "Not found"})
            return
        if not self._same_origin():
            self._reply(403, {"error": "Unrecognized host"})
            return
        body = self._json_body()
        if body is None:
            return
        if path == "/api/security":
            self._security(body)
            return
        self._join(body)

    def _join(self, body):
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
        accepted, token = self.server.onboarder.admit(ssid)
        if not accepted:
            if token == "locked":
                # The counter is in the state file, so a power cycle cannot clear
                # it. The advice has to be the wait that actually works.
                self._reply(429, {"error": "Too many attempts. Wait ten minutes, "
                                           "then try again."})
            elif token == "throttle":
                self._reply(429, {"error": "One attempt every few seconds. "
                                           "Try again shortly."})
            else:
                self._reply(409, {"error": "The device is not waiting for setup right now"})
            return
        status = self.server.onboarder.status()
        # Answer before the network goes away: this reply is the last thing the
        # browser can receive over the setup access point.
        try:
            self._reply(202, {"status": "connecting", "ssid": ssid,
                              "hotspot": (status.get("hotspot") or {}).get("ssid")})
        except OSError:
            # The phone dropped between the reservation and the reply. Nothing
            # was started, so the reservation must be released or every later
            # submission is refused as busy until the process restarts.
            LOGGER.warning("Join reply could not be delivered; the reservation is released")
            self.server.onboarder.release(token)
            return
        # Not a daemon: the process must not exit while the baseline is being
        # captured, because that is the only copy of the device's first state.
        worker = threading.Thread(target=self.server.onboarder.join_reserved,
                                  args=(ssid, psk or None, country, token),
                                  daemon=False, name="debra-onboarding")
        worker.start()

    def _security(self, body):
        """Change how the setup network is protected, without a reinstall.

        The reply is the one place the setup password is ever served. It is not
        in the status, not in the state and not in the journal, and it is only
        sent to a client that has already joined the access point - which is
        the same client that is about to lose it, so it has to carry the new
        password with it.
        """
        if not isinstance(body, dict) or set(body) != {"mode"}:
            self._reply(400, {"error": "Expected a mode"})
            return
        mode = body["mode"]
        if mode not in SETUP_SECURITY:
            self._reply(400, {"error": "Mode must be wpa or none"})
            return
        onboarder = self.server.onboarder
        if not onboarder.hotspot_running():
            # Joining, or already online: there is no access point to take down
            # and raise again, and re-raising one would take the radio away from
            # whatever is using it.
            self._reply(409, {"error": "The setup network is not running, so there is "
                                       "nothing to change"})
            return
        previous = onboarder.security
        try:
            onboarder.set_security(mode)
        except ValueError:
            self._reply(400, {"error": "Mode must be wpa or none"})
            return
        except OSError:
            self._reply(500, {"error": "The device could not save that setting"})
            return
        password = onboarder._hotspot_password() if mode == "wpa" else None
        payload = {"status": "changing", "mode": mode,
                   "ssid": (onboarder.status().get("hotspot") or {}).get("ssid")}
        if password:
            payload["password"] = password
        # Answer before the radio changes, for the same reason a join does: this
        # reply is the last thing the setup network can carry.
        try:
            self._reply(202, payload)
        except OSError:
            # The browser never heard the answer. Turning the password on and
            # raising a network that asks for one nobody was told is worse than
            # not changing it, so the device goes back to the mode it is
            # actually running in.
            LOGGER.warning("The change of the setup network was not delivered; "
                           "keeping the previous mode")
            try:
                onboarder.set_security(previous)
            except (ValueError, OSError):
                LOGGER.warning("The previous setup network mode could not be restored")
            return
        # Not a daemon: the access point is between two states, and exiting in
        # the middle of that leaves the setup network down with no page.
        worker = threading.Thread(target=onboarder.rearm_hotspot, daemon=False,
                                  name="debra-setup-security")
        worker.start()


def serve(onboarder, page=None, address=("10.42.0.1", PORTAL_PORT)):
    page = page or ASSETS / "setup.html"
    return Portal(address, onboarder, page)

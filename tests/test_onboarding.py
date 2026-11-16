"""Onboarding: identity, the phase machine, the portal, and the baseline.

Every test here runs offline. The NetworkManager is a recorded double, so a pass
proves the decisions and the HTTP contract, not that a radio works.
"""

import json
import secrets
import hashlib
import io
import logging
import os
import socket
import stat
import sys
import tempfile
import threading
import time
import unittest
import urllib.error
import urllib.request
from contextlib import redirect_stderr
from pathlib import Path
from unittest.mock import patch

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "control" / "setup"))

import baseline as baseline_module  # noqa: E402
import nm as nm_module  # noqa: E402
import onboarding  # noqa: E402
import state as state_module  # noqa: E402
from fake_nm import FakeNetwork  # noqa: E402

# GLib is the parser NetworkManager's keyfile plugin uses. Testing our escaping
# against a string assertion proves nothing; testing it against this proves the
# value comes back the way the person typed it.
try:
    import gi
    gi.require_version("GLib", "2.0")
    from gi.repository import GLib
except (ImportError, ValueError):  # pragma: no cover - depends on the host
    GLib = None


def _glib_parse(text):  # noqa: F401 - kept for the GLib-level assertions
    key_file = GLib.KeyFile()
    key_file.load_from_data(text, len(text.encode("utf-8")), GLib.KeyFileFlags.NONE)
    return {"ssid": key_file.get_string("wifi", "ssid"),
            "psk": key_file.get_string("wifi-security", "psk")}


# libnm is the parser NetworkManager's keyfile plugin itself uses. GLib alone is
# not enough: `ssid` has its own reader on top of the GLib value, which is how a
# submitted `65;66;` became `AB`.
def _nm_library():
    import ctypes
    try:
        nm = ctypes.CDLL("libnm.so.0")
        gio = ctypes.CDLL("libgio-2.0.so.0")
        glib = ctypes.CDLL("libglib-2.0.so.0")
    except OSError:  # pragma: no cover - depends on the host
        return None
    glib.g_key_file_new.restype = ctypes.c_void_p
    load = glib.g_key_file_load_from_data
    load.restype = ctypes.c_int
    load.argtypes = [ctypes.c_void_p, ctypes.c_char_p, ctypes.c_size_t,
                     ctypes.c_int, ctypes.POINTER(ctypes.c_void_p)]
    read = nm.nm_keyfile_read
    read.restype = ctypes.c_void_p
    read.argtypes = [ctypes.c_void_p, ctypes.c_char_p, ctypes.c_int,
                     ctypes.c_void_p, ctypes.c_void_p, ctypes.POINTER(ctypes.c_void_p)]
    for name in ("nm_connection_get_setting_wireless", "nm_setting_wireless_get_ssid",
                 "nm_connection_get_setting_wireless_security",
                 "nm_setting_wireless_security_get_psk"):
        function = getattr(nm, name)
        function.restype = ctypes.c_void_p
        function.argtypes = [ctypes.c_void_p]
    gio.g_bytes_get_size.restype = ctypes.c_size_t
    gio.g_bytes_get_size.argtypes = [ctypes.c_void_p]
    gio.g_bytes_get_data.restype = ctypes.c_void_p
    gio.g_bytes_get_data.argtypes = [ctypes.c_void_p, ctypes.POINTER(ctypes.c_size_t)]
    return ctypes, nm, gio, glib, load, read


NM_LIBRARY = _nm_library()


def _nm_parse(text, base_dir="/tmp/opencode"):
    """What NetworkManager itself would read out of this keyfile."""
    import ctypes
    _, nm, gio, glib, load, read = NM_LIBRARY
    key_file = glib.g_key_file_new()
    error = ctypes.c_void_p()
    payload = text.encode("utf-8")
    if not load(key_file, payload, len(payload), 0, ctypes.byref(error)):
        raise AssertionError("GLib refused the keyfile")
    connection = read(key_file, base_dir.encode(), 0, None, None, ctypes.byref(error))
    if not connection:
        raise AssertionError("libnm refused the keyfile")
    wireless = nm.nm_connection_get_setting_wireless(connection)
    size = ctypes.c_size_t()
    blob = nm.nm_setting_wireless_get_ssid(wireless)
    pointer = gio.g_bytes_get_data(blob, ctypes.byref(size))
    ssid = ctypes.string_at(pointer, gio.g_bytes_get_size(blob)).decode("utf-8")
    security = nm.nm_connection_get_setting_wireless_security(connection)
    psk = None
    if security:
        value = nm.nm_setting_wireless_security_get_psk(security)
        if value:
            psk = ctypes.cast(value, ctypes.c_char_p).value.decode("utf-8")
    return {"ssid": ssid, "psk": psk}


class Temp(unittest.TestCase):
    def setUp(self):
        self._temp = tempfile.TemporaryDirectory(prefix="onboard-", dir="/tmp/opencode")
        self.dir = Path(self._temp.name)
        self.state_path = self.dir / "setup.json"
        self.baseline_dir = self.dir / "baseline"

    def tearDown(self):
        self._temp.cleanup()

    def onboarder(self, network=None, **kwargs):
        # A fixed name, a serial path that cannot exist and an empty fake root
        # keep every test independent of the machine it runs on. Without the
        # root, a join would capture this laptop's real keyfiles.
        kwargs.setdefault("hostname", "debra-demo1")
        kwargs.setdefault("serial_paths", (str(self.dir / "no-serial"),))
        root = self.dir / "fake-root"
        root.mkdir(exist_ok=True)
        kwargs.setdefault("root", str(root))
        return onboarding.Onboarder(network or FakeNetwork(), self.state_path,
                                    self.baseline_dir, **kwargs)


class IdentityTests(Temp):
    def test_hostname_comes_from_the_board_serial_and_is_stable(self):
        self.assertEqual(onboarding.hostname_from_serial("00000000abcdef01"), "debra-cdef01")
        self.assertEqual(onboarding.hostname_from_serial("1000000012345678"), "debra-345678")
        self.assertEqual(onboarding.hostname_from_serial("1000000012345678"),
                         onboarding.hostname_from_serial("1000000012345678"))
        self.assertNotEqual(onboarding.hostname_from_serial("1000000012345678"),
                            onboarding.hostname_from_serial("1000000087654321"))

    def test_a_serial_that_cannot_name_a_device_falls_back(self):
        self.assertIsNone(onboarding.hostname_from_serial(""))
        self.assertIsNone(onboarding.hostname_from_serial("abc"))
        self.assertIsNone(onboarding.hostname_from_serial(None))
        # Punctuation is dropped rather than becoming part of a hostname.
        self.assertEqual(onboarding.hostname_from_serial("0000-00ab-cdef"), "debra-abcdef")

    def test_identity_is_chosen_once_and_applied_every_time(self):
        serial = self.dir / "serial"
        serial.write_text("1000000012345678\n")
        network = FakeNetwork()
        onboarder = self.onboarder(network, serial_paths=(str(serial),))
        self.assertEqual(onboarder.ensure_identity(), "debra-345678")
        self.assertEqual(onboarder.ensure_identity(), "debra-345678")
        # The name is chosen once. Applying it is idempotent and repeated,
        # because a first application that failed used to be remembered as done
        # and no later boot repaired it.
        self.assertEqual(network.phases().count("set_hostname"), 2)
        self.assertEqual(state_module.read(self.state_path)["hostname"], "debra-345678")

    def test_a_failed_application_is_retried_on_the_next_boot(self):
        network = FakeNetwork()
        network.fail_hostname = True
        onboarder = self.onboarder(network)
        with self.assertLogs(onboarding.LOGGER, level="WARNING"):
            onboarder.ensure_identity()
        network.fail_hostname = False
        onboarder.ensure_identity()
        self.assertEqual(network.hostname_applied, "debra-demo1")

    def test_hotspot_name_is_derived_from_the_hostname(self):
        self.assertEqual(onboarding.hotspot_name("debra-345678"), "Debra-Setup-345678")
        self.assertEqual(onboarding.hotspot_name(None), "Debra-Setup-debra")


class StateTests(Temp):
    def test_a_missing_file_is_a_blank_record_not_an_error(self):
        data = state_module.read(self.state_path)
        self.assertEqual(data["phase"], "unconfigured")
        self.assertEqual(data["attempts"], 0)

    def test_written_state_is_owner_only_and_round_trips(self):
        data = state_module.blank("debra-345678")
        data.update(phase="hotspot", hotspot={"ssid": "Debra-Setup-345678",
                                              "interface": "wlan0"},
                    hotspot_password="abcdefghjk2m")
        state_module.write(self.state_path, data)
        self.assertEqual(stat.S_IMODE(self.state_path.stat().st_mode), 0o600)
        self.assertEqual(state_module.read(self.state_path)["hostname"], "debra-345678")

    def test_unknown_keys_bad_phases_and_bad_values_are_refused(self):
        base = state_module.blank("debra-345678")
        for broken in (dict(base, extra=1), dict(base, phase="sleeping"),
                       dict(base, schema=3), dict(base, attempts=-1),
                       dict(base, country="GBR"), dict(base, hotspot={"ssid": "x"})):
            with self.assertRaises(ValueError, msg=str(broken)[:60]):
                state_module.validate(broken)

    def test_a_hotspot_and_its_password_travel_together(self):
        # A described access point with no credential is one nothing can join.
        # The old record could describe one because the password was not stored.
        described = dict(state_module.blank("debra-1"), phase="hotspot",
                         hotspot={"ssid": "Debra-Setup-1", "interface": "wlan0"})
        with self.assertRaisesRegex(ValueError, "needs its password"):
            state_module.validate(described)
        with self.assertRaisesRegex(ValueError, "needs a described hotspot"):
            state_module.validate(dict(state_module.blank("debra-1"), phase="hotspot",
                                       hotspot_password="abcdefghjk2m"))

    def test_a_password_that_cannot_be_typed_is_refused(self):
        # Twelve newlines passed the old length check and would have been
        # written verbatim into the boot-partition note.
        base = dict(state_module.blank("debra-1"), phase="hotspot",
                    hotspot={"ssid": "Debra-Setup-1", "interface": "wlan0"})
        for password in ("\n" * 12, "has a space", "tab\there12", "abcdefg"):
            with self.subTest(password=password):
                with self.assertRaises(ValueError):
                    state_module.validate(dict(base, hotspot_password=password))

    def test_a_schema_one_record_is_migrated_not_refused(self):
        # Schema 2 added `attempt_claimed`, `hotspot_password` and `revision`.
        # A device that ran the earlier prototype must not be left with a state
        # file that stops the service.
        old = state_module.blank("debra-1")
        del old["attempt_claimed"], old["hotspot_password"], old["revision"]
        old.update(schema=1, phase="failed", last_error="A wrong password")
        self.state_path.write_text(json.dumps(old))
        data = state_module.read(self.state_path)
        self.assertEqual(data["schema"], state_module.SCHEMA)
        self.assertFalse(data["attempt_claimed"])
        self.assertIsNone(data["hotspot_password"])
        self.assertEqual(data["last_error"], "A wrong password")

    def test_a_schema_one_record_without_the_later_fields_is_migrated(self):
        # The prototype revisions did not all carry the same keys: three of the
        # five records this repository wrote lacked `attempt_token`,
        # `baseline_error` or `last_attempt` as well as the fields added at
        # schema 2. Filling only those three refused those records and stopped
        # the service on a device that had merely upgraded.
        old = {"schema": 1, "phase": "hotspot", "hostname": "debra-1",
               "country": "GB", "ssid": "HomeWiFi", "address": None,
               "last_error": None, "attempts": 1,
               "hotspot": {"ssid": "Debra-Setup-1", "interface": "wlan0"},
               "baseline": None}
        self.state_path.write_text(json.dumps(old))
        data = state_module.read(self.state_path)
        self.assertEqual(data["schema"], state_module.SCHEMA)
        self.assertEqual(data["country"], "GB")
        self.assertIsNone(data["attempt_token"])
        self.assertIsNone(data["baseline_error"])
        self.assertIsNone(data["last_attempt"])
        self.assertFalse(data["attempt_claimed"])
        # The described hot spot had no stored password, so it is dropped.
        self.assertIsNone(data["hotspot"])
        self.assertEqual(data["phase"], "failed")

    def test_a_schema_one_hotspot_is_dropped_so_it_can_be_raised_again(self):
        # The old schema stored no password, so the described access point
        # cannot be joined. It is dropped and the next boot raises it again,
        # instead of refusing the file and stopping the service.
        old = state_module.blank("debra-1")
        del old["attempt_claimed"], old["hotspot_password"], old["revision"]
        old.update(schema=1, phase="hotspot",
                   hotspot={"ssid": "Debra-Setup-1", "interface": "wlan0"})
        self.state_path.write_text(json.dumps(old))
        data = state_module.read(self.state_path)
        self.assertIsNone(data["hotspot"])
        self.assertEqual(data["phase"], "failed")
        self.assertIn("raised again", data["last_error"])

    def test_every_write_advances_the_revision(self):
        # The page orders answers by this, not by the time its request started.
        data = state_module.write(self.state_path, state_module.blank("debra-1"))
        first = data["revision"]
        second = state_module.write(self.state_path, dict(data, country="GB"))["revision"]
        self.assertGreater(second, first)

    def test_a_record_missing_a_key_is_refused_not_crashed_on(self):
        # A record that validates and then raises KeyError in status() is worse
        # than one refused at the boundary. The review deleted every required
        # key and the old check accepted each one.
        for key in state_module.blank("debra-demo1"):
            broken = dict(state_module.blank("debra-demo1"))
            del broken[key]
            with self.assertRaises(ValueError, msg=key):
                state_module.validate(broken)

    def test_a_bool_is_not_a_schema_version(self):
        # JSON `true` is 1 in Python, so a bare equality check accepted it.
        data = state_module.blank("debra-demo1")
        data["schema"] = True
        with self.assertRaises(ValueError):
            state_module.validate(data)

    def test_a_passphrase_can_never_be_stored(self):
        # The schema is closed, so a keyfile-shaped extra key is rejected rather
        # than quietly persisted next to the state.
        with self.assertRaises(ValueError):
            state_module.validate(dict(state_module.blank("debra-1"), psk="hunter22"))
        self.assertNotIn("psk", json.dumps(state_module.blank("debra-1")))


class HotspotTests(Temp):
    def test_starting_the_hotspot_records_the_name_and_interface(self):
        network = FakeNetwork()
        status = self.onboarder(network).start_hotspot()
        self.assertEqual(status["phase"], "hotspot")
        self.assertEqual(status["hotspot"]["ssid"], "Debra-Setup-demo1")
        self.assertEqual(status["hotspot"]["interface"], "wlan0")
        # A setup network nobody can join is not a setup network: the password
        # has to be somewhere a person can read it.
        self.assertGreaterEqual(len(status["hotspot"]["password"]), 8)
        # The hostname is applied before the access point is named after it, and
        # an already-set country is read rather than asked for again.
        # The scan sits before the access point is raised, which is the only
        # window where the radio is free enough to look around.
        self.assertEqual(network.phases(),
                         ["set_hostname", "wifi_interface", "country", "scan",
                          "start_hotspot"])

    def test_the_device_name_survives_the_first_hotspot(self):
        # The identity is set in the same record the hotspot then writes. When
        # the write used a record read before the name existed, it erased it.
        status = self.onboarder(FakeNetwork()).start_hotspot()
        self.assertEqual(status["hostname"], "debra-demo1")
        self.assertEqual(state_module.read(self.state_path)["hostname"], "debra-demo1")
        # The portal only admits the address it is served on, so the printed
        # name is that address, not `<hostname>.local`.
        self.assertEqual(status["portal"], "http://10.42.0.1/")

    def test_a_boot_with_no_uplink_keeps_the_name_too(self):
        status = self.onboarder(FakeNetwork()).resume()
        self.assertEqual(status["hostname"], "debra-demo1")
        self.assertEqual(state_module.read(self.state_path)["hostname"], "debra-demo1")

    def test_no_wifi_interface_is_reported_not_ignored(self):
        status = self.onboarder(FakeNetwork(interface=None)).start_hotspot()
        self.assertEqual(status["phase"], "failed")
        self.assertIn("No Wi-Fi interface", status["last_error"])

    def test_a_hotspot_failure_is_reported(self):
        network = FakeNetwork()

        def refuse(*args, **kwargs):
            raise nm_module.NmError("AP mode not supported by this driver")

        network.start_hotspot = refuse
        status = self.onboarder(network).start_hotspot()
        self.assertEqual(status["phase"], "failed")
        self.assertIn("AP mode not supported", status["last_error"])


class JoinTests(Temp):
    def test_a_successful_join_stops_the_hotspot_and_records_the_address(self):
        network = FakeNetwork()
        onboarder = self.onboarder(network)
        onboarder.start_hotspot()
        status = onboarder.join("HomeWiFi", "correct horse", "GB")
        self.assertEqual(status["phase"], "online")
        self.assertEqual(status["ssid"], "HomeWiFi")
        self.assertEqual(status["address"], "192.0.2.40")
        self.assertIsNone(status["hotspot"])
        # Order matters: the access point goes before the association, because a
        # single radio cannot do both.
        phases = network.phases()
        self.assertLess(phases.index("stop_hotspot"), phases.index("connect"))
        self.assertEqual(network.country_code, "GB")

    def test_a_wrong_password_brings_the_hotspot_back_with_the_reason(self):
        network = FakeNetwork(behaviour="bad-psk")
        onboarder = self.onboarder(network)
        onboarder.start_hotspot()
        status = onboarder.join("HomeWiFi", "wrong password", None)
        self.assertEqual(status["phase"], "failed")
        self.assertIn("password was refused", status["last_error"])
        # The access point must be back, or the user has no way to try again.
        self.assertEqual(status["hotspot"]["ssid"], "Debra-Setup-demo1")
        self.assertEqual(network.hotspot["ssid"], "Debra-Setup-demo1")

    def test_association_without_an_address_is_a_failure_not_a_success(self):
        network = FakeNetwork(behaviour="no-address")
        onboarder = self.onboarder(network)
        onboarder.start_hotspot()
        status = onboarder.join("HomeWiFi", "correct horse", None)
        self.assertEqual(status["phase"], "failed")
        self.assertIn("no usable address", status["last_error"])

    def test_the_country_is_only_set_once(self):
        network = FakeNetwork(country="GB")
        onboarder = self.onboarder(network)
        state_module.write(self.state_path, dict(state_module.blank("debra-1"), country="GB"))
        onboarder.start_hotspot()
        onboarder.join("HomeWiFi", "correct horse", "US")
        self.assertNotIn("set_country", network.phases())

    def test_attempts_are_counted_and_capped(self):
        network = FakeNetwork(behaviour="bad-psk")
        onboarder = self.onboarder(network)
        onboarder.start_hotspot()
        for _ in range(onboarding.MAX_ATTEMPTS):
            onboarder._last_submit = -1000
            onboarder.join("HomeWiFi", "wrong password", None)
        self.assertEqual(state_module.read(self.state_path)["attempts"],
                         onboarding.MAX_ATTEMPTS)
        onboarder._last_submit = -1000
        before = len(network.calls)
        onboarder.join("HomeWiFi", "wrong password", None)
        self.assertEqual(len(network.calls), before, "the cap did not stop the attempt")

    def test_rapid_resubmission_is_ignored(self):
        network = FakeNetwork()
        clock = [0.0]
        onboarder = self.onboarder(network, clock=lambda: clock[0])
        onboarder.start_hotspot()
        onboarder.join("HomeWiFi", "correct horse", None)
        clock[0] = 1.0
        before = len(network.calls)
        onboarder.join("OtherWiFi", "correct horse", None)
        self.assertEqual(len(network.calls), before)


class ResumeTests(Temp):
    def test_an_offline_boot_raises_the_setup_point(self):
        status = self.onboarder(FakeNetwork()).resume()
        self.assertEqual(status["phase"], "hotspot")

    def test_an_online_boot_records_the_current_address(self):
        network = FakeNetwork()
        network.joined = "HomeWiFi"
        status = self.onboarder(network).resume()
        self.assertEqual(status["phase"], "online")
        self.assertEqual(status["address"], "192.0.2.40")
        self.assertNotIn("start_hotspot", network.phases())

    def test_a_lost_network_comes_back_as_a_setup_point_with_a_reason(self):
        state_module.write(self.state_path, dict(state_module.blank("debra-1"),
                                                phase="online", address="192.0.2.40"))
        status = self.onboarder(FakeNetwork()).resume()
        self.assertEqual(status["phase"], "failed")
        self.assertIn("not reachable", status["last_error"])


class BaselineTests(Temp):
    def test_a_baseline_captures_the_allowlist_and_records_what_was_missing(self):
        root = self.dir / "root"
        (root / "etc" / "NetworkManager" / "system-connections").mkdir(parents=True)
        (root / "etc" / "hostname").write_text("debra-345678\n")
        (root / "etc" / "NetworkManager" / "system-connections" / "home.nmconnection").write_text(
            "[wifi]\nssid=HomeWiFi\n")
        manifest = baseline_module.capture(self.baseline_dir, root=str(root))
        self.assertIn("etc/hostname", manifest["captured"])
        self.assertIn("etc/NetworkManager/system-connections/home.nmconnection",
                      manifest["captured"])
        self.assertIn("var/lib/debra", manifest["missing"])
        archive = self.baseline_dir / manifest["archive"]
        self.assertEqual(stat.S_IMODE(archive.stat().st_mode), 0o600)
        self.assertEqual(stat.S_IMODE((self.baseline_dir / manifest["archive"].replace(
            ".tar.gz", ".json")).stat().st_mode), 0o600)

    def test_a_baseline_is_taken_once_after_the_first_join(self):
        network = FakeNetwork()
        onboarder = self.onboarder(network)
        onboarder.start_hotspot()
        status = onboarder.join("HomeWiFi", "correct horse", None)
        self.assertIsNotNone(status["baseline"])
        self.assertTrue(Path(status["baseline"]).exists())
        first = status["baseline"]
        onboarder._last_submit = -1000
        onboarder.join("HomeWiFi", "correct horse", None)
        self.assertEqual(state_module.read(self.state_path)["baseline"], first)

    def test_an_unreadable_file_is_skipped_and_the_rest_still_runs(self):
        root = self.dir / "root"
        (root / "etc" / "NetworkManager" / "system-connections").mkdir(parents=True)
        (root / "etc" / "hostname").write_text("debra-345678\n")
        secret = root / "etc" / "NetworkManager" / "system-connections" / "home.nmconnection"
        secret.write_text("[wifi]\nssid=HomeWiFi\n")
        import builtins
        real_open = builtins.open

        def fake_open(path, *args, **kwargs):
            if str(path).endswith("home.nmconnection"):
                raise PermissionError(13, "Permission denied")
            return real_open(path, *args, **kwargs)

        with patch("builtins.open", fake_open):
            manifest = baseline_module.capture(self.baseline_dir, root=str(root))
        self.assertIn("etc/hostname", manifest["captured"])
        self.assertEqual(manifest["skipped"][0]["path"], str(secret))
        self.assertEqual(manifest["skipped"][0]["reason"], "PermissionError")
        self.assert_in_archive(manifest, ["etc/hostname"])

    def test_a_read_that_fails_partway_does_not_poison_the_archive(self):
        # tar.add() writes a header and part of a body before a read can fail.
        # Catching that left a truncated member that every later file was
        # unreachable behind, while the manifest still claimed they were saved.
        root = self.dir / "root"
        (root / "etc" / "NetworkManager" / "system-connections").mkdir(parents=True)
        (root / "etc" / "hostname").write_text("debra-345678\n")
        profile = root / "etc" / "NetworkManager" / "system-connections" / "home.nmconnection"
        profile.write_bytes(b"x" * 2048)
        import builtins
        real_open = builtins.open

        class Partial:
            def __init__(self, path):
                self._file = real_open(path, "rb")
                self._served = False

            def fileno(self):
                return self._file.fileno()

            def read(self, size=-1):
                if not self._served:
                    self._served = True
                    return self._file.read(17)
                raise OSError(5, "Input/output error")

            def __enter__(self):
                return self

            def __exit__(self, *args):
                self._file.close()

        def fake_open(path, *args, **kwargs):
            if str(path).endswith("home.nmconnection"):
                return Partial(path)
            return real_open(path, *args, **kwargs)

        with patch("builtins.open", fake_open):
            manifest = baseline_module.capture(self.baseline_dir, root=str(root))
        self.assertIn("etc/hostname", manifest["captured"])
        self.assertNotIn("etc/NetworkManager/system-connections/home.nmconnection",
                         manifest["captured"])
        # The later file must still be readable out of the published archive.
        self.assert_in_archive(manifest, ["etc/hostname"])

    def assert_in_archive(self, manifest, expected):
        import tarfile as tarfile_module
        archive = self.baseline_dir / manifest["archive"]
        with tarfile_module.open(archive) as tar:
            names = tar.getnames()
        for name in expected:
            self.assertIn(name, names, f"{name} missing from the published archive: {names}")
        self.assertEqual(len(names), len(manifest["captured"]),
                         "the archive and the manifest disagree about what was captured")

    def test_a_failed_baseline_does_not_undo_a_working_network(self):
        network = FakeNetwork()
        onboarder = self.onboarder(network)
        onboarder.start_hotspot()
        with patch.object(baseline_module, "capture",
                          side_effect=baseline_module.BaselineError("too large")):
            status = onboarder.join("HomeWiFi", "correct horse", None)
        self.assertEqual(status["phase"], "online")
        self.assertIsNone(status["baseline"])


class PortalTests(Temp):
    def setUp(self):
        super().setUp()
        self.network = FakeNetwork()
        self.onboarder = self.onboarder(self.network)
        self.onboarder.start_hotspot()
        self.server = onboarding.Portal(("127.0.0.1", 0), self.onboarder,
                                        onboarding.ASSETS / "setup.html")
        self.host = "127.0.0.1:%d" % self.server.server_port
        self.server.host = self.host
        self.thread = threading.Thread(target=self.server.serve_forever, daemon=True)
        self.thread.start()

    def tearDown(self):
        self.server.shutdown()
        self.thread.join()
        super().tearDown()

    def request(self, path, body=None, host=None, method=None):
        data = None if body is None else json.dumps(body).encode()
        request = urllib.request.Request(
            "http://" + self.host + path, data=data, method=method or ("POST" if data else "GET"))
        request.add_header("Host", host or self.host)
        if data:
            request.add_header("Content-Type", "application/json")
        try:
            with urllib.request.urlopen(request, timeout=10) as response:
                return response.status, response.read()
        except urllib.error.HTTPError as exc:
            return exc.code, exc.read()

    def test_the_page_and_its_script_are_served(self):
        code, body = self.request("/")
        self.assertEqual(code, 200)
        self.assertIn(b"Set up Wi-Fi", body)
        code, body = self.request("/setup.js")
        self.assertEqual(code, 200)
        self.assertIn(b"/api/join", body)

    def test_status_reports_the_phase_without_the_household_passphrase(self):
        # The setup network's own password *is* in this response, on purpose:
        # that is how the page shows it after a failure. What must never appear
        # is the household passphrase, which this response has no reason to hold.
        code, body = self.request("/api/status")
        self.assertEqual(code, 200)
        data = json.loads(body)
        self.assertEqual(data["phase"], "hotspot")
        self.assertNotIn("psk", data)
        self.assertNotIn(b"correct horse", body)
        self.assertIn("password", data["hotspot"])

    def test_another_host_name_is_refused(self):
        code, _ = self.request("/api/status", host="evil.example")
        self.assertEqual(code, 403)
        code, _ = self.request("/", host="evil.example")
        self.assertEqual(code, 403)

    def test_a_join_is_answered_before_the_access_point_stops(self):
        code, body = self.request("/api/join", {"ssid": "HomeWiFi", "psk": "correct horse",
                                                "country": "GB"})
        self.assertEqual(code, 202)
        self.assertEqual(json.loads(body)["status"], "connecting")
        # The worker finishes in the background; wait for it rather than sleep.
        for _ in range(200):
            if state_module.read(self.state_path)["phase"] in ("online", "failed"):
                break
            threading.Event().wait(0.01)
        self.assertEqual(state_module.read(self.state_path)["phase"], "online")

    def test_the_join_runs_only_after_the_page_has_been_answered(self):
        # The whole handover depends on this ordering: the reply is the last
        # thing that can travel over the setup network. A review mutation that
        # completed the join before writing the 202 passed every other test.
        seen = {}
        real_reply = onboarding.PortalHandler._reply

        def reply(handler, code, body, content_type="application/json"):
            if code == 202:
                seen["replied"] = True
            return real_reply(handler, code, body, content_type)

        real_connect = self.network.connect

        def connect(ssid, psk, timeout=60, keyfile_dir=None, interface=None):
            seen["connect_saw_reply"] = seen.get("replied", False)
            return real_connect(ssid, psk, timeout=timeout,
                                keyfile_dir=keyfile_dir, interface=interface)

        # The patches stay in place until the worker has finished: the worker
        # starts after the reply and would otherwise run unpatched.
        with patch.object(onboarding.PortalHandler, "_reply", reply), \
                patch.object(self.network, "connect", connect):
            code, _ = self.request("/api/join", {"ssid": "HomeWiFi",
                                                 "psk": "correct horse"})
            self.assertEqual(code, 202)
            for _ in range(200):
                if state_module.read(self.state_path)["phase"] in ("online", "failed"):
                    break
                threading.Event().wait(0.01)
        self.assertTrue(seen.get("connect_saw_reply"),
                        "the join ran before the page was answered")

    def test_the_access_point_is_still_up_when_the_page_is_answered(self):
        # Answering first is not enough if the access point has already gone:
        # the reply has to travel over the network being torn down. A review
        # mutation stopped the AP before the 202 and kept the worker after it,
        # and every other test still passed, because they only watched
        # `connect()`.
        seen = {}
        real_reply = onboarding.PortalHandler._reply

        def reply(handler, code, body, content_type="application/json"):
            if code == 202:
                seen["hotspot_at_reply"] = self.network.hotspot
                seen["stops_at_reply"] = len(
                    [call for call in self.network.calls if call[0] == "stop_hotspot"])
            return real_reply(handler, code, body, content_type)

        with patch.object(onboarding.PortalHandler, "_reply", reply):
            code, _ = self.request("/api/join", {"ssid": "HomeWiFi",
                                                 "psk": "correct horse"})
            self.assertEqual(code, 202)
            for _ in range(200):
                if state_module.read(self.state_path)["phase"] in ("online", "failed"):
                    break
                threading.Event().wait(0.01)
        self.assertTrue(seen.get("hotspot_at_reply"),
                        "the access point was already down when the page was answered")
        self.assertEqual(seen.get("stops_at_reply"), 0,
                         "the access point was stopped before the page was answered")
        # And it does go down, eventually: the join is what needs the radio.
        self.assertEqual(len([call for call in self.network.calls
                              if call[0] == "stop_hotspot"]), 1)
        self.assertIsNone(self.network.hotspot)

    def test_a_reply_that_cannot_be_delivered_releases_the_reservation(self):
        real_reply = onboarding.PortalHandler._reply

        def reply(handler, code, body, content_type="application/json"):
            if code == 202:
                raise BrokenPipeError(32, "Broken pipe")
            return real_reply(handler, code, body, content_type)

        with patch.object(onboarding.PortalHandler, "_reply", reply):
            with self.assertRaises(OSError):
                self.request("/api/join", {"ssid": "HomeWiFi", "psk": "correct horse"})
        data = state_module.read(self.state_path)
        self.assertEqual(data["phase"], "hotspot",
                         "a lost reply left the device connecting for ever")
        self.assertIsNone(data["attempt_token"])
        self.assertEqual(data["attempts"], 0)
        self.assertNotIn("connect", self.network.phases(),
                         "a join ran although its reply never arrived")

    def test_bad_input_is_refused_without_touching_the_network(self):
        for body, expected in (
            ({"ssid": ""}, 400),
            ({"ssid": "x" * 33}, 400),
            ({"ssid": "ok", "psk": "short"}, 400),
            ({"ssid": "ok", "country": "gb"}, 400),
            ({"ssid": "ok", "extra": 1}, 400),
        ):
            code, _ = self.request("/api/join", body)
            self.assertEqual(code, expected, body)
        self.assertNotIn("connect", self.network.phases())

    def test_a_join_is_refused_when_the_device_is_not_waiting(self):
        state_module.write(self.state_path, dict(state_module.blank("debra-1"), phase="online"))
        code, _ = self.request("/api/join", {"ssid": "HomeWiFi", "psk": "correct horse"})
        self.assertEqual(code, 409)


if __name__ == "__main__":
    unittest.main()


class SetupPasswordTests(Temp):
    """The setup network has to be joinable by a person with no console.

    It also has to be unguessable. The password used to be derived from the
    device name, which is broadcast in the setup network's own SSID: anyone in
    range could compute it, so it protected nothing.
    """

    def test_the_password_is_generated_and_not_computable_from_the_name(self):
        first = onboarding.new_hotspot_password()
        second = onboarding.new_hotspot_password()
        self.assertNotEqual(first, second, "two passwords were the same")
        name = onboarding.hotspot_name("debra-345678")
        self.assertNotIn(name.split("-")[-1], first,
                         "the password leaks the device name it used to be made from")
        self.assertGreaterEqual(len(first), 8)
        self.assertLessEqual(len(first), 63)
        self.assertTrue(set(first) <= set(onboarding.HOTSPOT_ALPHABET))

    def test_the_adapter_is_given_a_password_rather_than_left_to_invent_one(self):
        # The page can only be joined if the person is told the password, so one
        # must be generated and handed over rather than left to nmcli.
        network = FakeNetwork()
        self.onboarder(network).start_hotspot()
        # The fake records only whether a password was passed, so that a test
        # log never holds a credential; the length is checked on the real one.
        hotspot_calls = [call for call in network.calls if call[0] == "start_hotspot"]
        self.assertTrue(hotspot_calls[0][3], "start_hotspot was called without a password")
        self.assertGreaterEqual(len(onboarding.new_hotspot_password()), 8,
                                "a shorter password is outside what NM CLI accepts")

    def test_the_household_passphrase_is_never_written_into_the_setup_state(self):
        # The old version of this test only raised the access point and never
        # submitted anything, so it could not fail on the passphrase at all.
        onboarder = self.onboarder()
        onboarder.start_hotspot()
        status = onboarder.join("HomeWiFi", "correct horse battery", None)
        self.assertEqual(status["phase"], "online")
        stored = self.state_path.read_text(encoding="utf-8")
        self.assertNotIn("correct horse", stored)
        self.assertNotIn("psk", stored)

    def test_the_setup_password_is_stored_so_the_page_and_the_note_agree(self):
        # It protects the setup window, not the household. Keeping it lets the
        # status report it and the note be reprinted after a rebind.
        onboarder = self.onboarder()
        status = onboarder.start_hotspot()
        stored = state_module.read(self.state_path)["hotspot_password"]
        self.assertEqual(status["hotspot"]["password"], stored)
        self.assertEqual(len(stored), onboarding.HOTSPOT_PASSWORD_LENGTH)

    def test_the_card_note_says_the_three_things_needed_before_any_page_loads(self):
        note = self.dir / "boot" / "debra-setup.txt"
        onboarder = self.onboarder(card_note_path=note)
        status = onboarder.start_hotspot()
        text = note.read_text(encoding="utf-8")
        self.assertIn("Debra-Setup-demo1", text)
        self.assertIn(status["hotspot"]["password"], text)
        self.assertIn("http://", text)

    def test_a_reprinted_note_keeps_the_password_the_access_point_was_raised_with(self):
        note = self.dir / "boot" / "debra-setup.txt"
        network = FakeNetwork()
        onboarder = self.onboarder(network, card_note_path=note)
        first = onboarder.start_hotspot()["hotspot"]["password"]
        onboarder.announce_portal("192.0.2.9")
        text = note.read_text(encoding="utf-8")
        self.assertIn(first, text, "the reprinted note lost the password")
        self.assertIn("192.0.2.9", text)


class CountryTests(Temp):
    def test_a_country_already_on_the_device_is_adopted_not_asked_for_again(self):
        onboarder = self.onboarder(FakeNetwork(country="GB"))
        status = onboarder.start_hotspot()
        self.assertEqual(status["country"], "GB")
        self.assertEqual(state_module.read(self.state_path)["country"], "GB")

    def test_with_no_country_set_the_page_still_asks(self):
        status = self.onboarder(FakeNetwork(country=None)).start_hotspot()
        self.assertIsNone(status["country"])


class LockoutTests(Temp):
    def test_the_cap_is_a_cooldown_and_not_a_permanent_lockout(self):
        network = FakeNetwork(behaviour="bad-psk")
        clock = [0.0]
        onboarder = self.onboarder(network, clock=lambda: clock[0])
        onboarder.start_hotspot()
        for _ in range(onboarding.MAX_ATTEMPTS):
            clock[0] += onboarding.SUBMIT_INTERVAL_S + 1
            onboarder.join("HomeWiFi", "wrong password", None)
        data = state_module.read(self.state_path)
        self.assertEqual(data["attempts"], onboarding.MAX_ATTEMPTS)
        # Immediately after the cap, another attempt is refused...
        clock[0] += onboarding.SUBMIT_INTERVAL_S + 1
        before = len(network.calls)
        onboarder.join("HomeWiFi", "wrong password", None)
        self.assertEqual(len(network.calls), before, "the cooldown did not hold")
        # ...but not for ever, because a power cycle cannot clear this counter.
        pinned = state_module.read(self.state_path)
        pinned["last_attempt"] = "2020-01-01T00:00:00Z"
        state_module.write(self.state_path, pinned)
        clock[0] += onboarding.SUBMIT_INTERVAL_S + 1
        onboarder.join("HomeWiFi", "wrong password", None)
        self.assertGreater(len(network.calls), before,
                           "an expired cooldown must let the retry through")
        # The allowance starts again from one. It used to stay at the cap, so
        # one wrong password after the cooldown re-armed the whole lockout.
        self.assertEqual(state_module.read(self.state_path)["attempts"], 1,
                         "the expired window did not start again from one")

    def test_a_successful_join_clears_the_failure_count(self):
        network = FakeNetwork(behaviour="bad-psk")
        clock = [0.0]
        onboarder = self.onboarder(network, clock=lambda: clock[0])
        onboarder.start_hotspot()
        for _ in range(3):
            clock[0] += onboarding.SUBMIT_INTERVAL_S + 1
            onboarder.join("HomeWiFi", "wrong password", None)
        self.assertEqual(state_module.read(self.state_path)["attempts"], 3)
        network.behaviour = "ok"
        clock[0] += onboarding.SUBMIT_INTERVAL_S + 1
        status = onboarder.join("HomeWiFi", "correct horse", None)
        self.assertEqual(status["phase"], "online")
        data = state_module.read(self.state_path)
        self.assertEqual(data["attempts"], 0)
        self.assertIsNone(data["last_attempt"])


class BaselineRootTests(Temp):
    def test_the_baseline_reads_the_configured_root_and_not_the_real_one(self):
        # On a laptop, root="/" would copy that machine's real NetworkManager
        # keyfiles into the archive. A test run must never do that.
        fake = self.dir / "fake-root"
        (fake / "etc").mkdir(parents=True)
        (fake / "etc" / "hostname").write_text("debra-demo1\n", encoding="utf-8")
        onboarder = self.onboarder(root=str(fake))
        onboarder.start_hotspot()
        status = onboarder.join("HomeWiFi", "correct horse", None)
        manifest = json.loads((Path(status["baseline"].replace(".tar.gz", ".json"))
                               ).read_text())
        self.assertIn("etc/hostname", manifest["captured"])
        self.assertTrue(all(not path.startswith("var/") for path in manifest["captured"]))


class Recorder:
    """A stand-in for `_run` that answers like nmcli and remembers argv.

    It tracks the connection id the adapter generates, because a successful
    join is now defined by NetworkManager naming *that* profile as the active
    connection. A double that answers every query with IP fields is exactly the
    bypass the review found: it made an unknown profile look like success.
    """

    def __init__(self, address="192.0.2.40", gateway="192.0.2.1", up_fails=False,
                 active_profile=None, load_fails=False, modify_fails=False,
                 interface="wlan0", profile_dir=None):
        self.calls, self.contents = [], []
        self.address, self.gateway, self.up_fails = address, gateway, up_fails
        self.active_profile = active_profile
        self.load_fails = load_fails
        self.modify_fails = modify_fails
        self.interface = interface
        # The directory the keyfile plugin reads. `nmcli connection load` is not
        # an arbitrary-file import, so a profile handed over from anywhere else
        # is refused here the way a real NetworkManager would refuse it.
        self.profile_dir = profile_dir
        self.loaded_id = None
        self.deleted = []
        self.modified = []

    def __call__(self, argv, timeout=45):
        self.calls.append(list(argv))
        if argv[1:] == ["-t", "-f", "DEVICE,TYPE,STATE", "device", "status"]:
            return f"{self.interface}:wifi:connected\n"
        if argv[1:3] == ["-t", "-f"] and argv[4:6] == ["device", "show"]:
            if argv[3] == "GENERAL.CONNECTION":
                name = self.active_profile
                if name is None:
                    name = self.loaded_id if not self.up_fails else None
                return f"GENERAL.CONNECTION:{name or ''}\n"
            return (f"IP4.ADDRESS[1]:{self.address}/24\n"
                    f"IP4.GATEWAY:{self.gateway}\n")
        if argv[1:3] == ["connection", "load"]:
            if self.load_fails:
                raise nm_module.NmError("NetworkManager refused the profile")
            path = Path(argv[3])
            if self.profile_dir is not None and path.parent != Path(self.profile_dir):
                raise nm_module.NmError(
                    "Error: Cannot load connection profile: file is not in a profile directory")
            self.contents.append((path.read_text(encoding="utf-8"),
                                  stat.S_IMODE(path.stat().st_mode),
                                  str(path)))
            return ""
        if argv[1:4] == ["connection", "up", "id"]:
            self.loaded_id = argv[4]
            if self.up_fails:
                raise nm_module.NmError("The Wi-Fi password was refused by the network")
            return ""
        if argv[1:4] == ["connection", "delete", "id"]:
            self.deleted.append(argv[4])
            return ""
        if argv[1:3] == ["connection", "modify"]:
            if self.modify_fails:
                raise nm_module.NmError("NetworkManager refused the change")
            self.modified.append(" ".join(argv[4:]))
            return ""
        if argv[1:3] == ["radio", "wifi"]:
            return "enabled\n"
        return ""


class AdapterTests(Temp):
    def test_the_wi_fi_password_never_appears_in_a_command_line(self):
        recorder = Recorder()
        nm_module.Nmcli(runner=recorder).connect("HomeWiFi", "correct horse",
                                                 keyfile_dir=self.dir)
        flattened = " ".join(" ".join(call) for call in recorder.calls)
        self.assertNotIn("correct horse", flattened,
                         "the password is visible in argv to any other process")
        self.assertEqual(len(recorder.contents), 1)
        text, mode, path = recorder.contents[0]
        self.assertIn("psk=correct horse", text)
        self.assertEqual(mode, 0o600, "the profile must be owner-only")
        # The profile stays where NetworkManager will read it on the next boot.
        # Deleting it, as the previous version did, meant the device forgot its
        # household network the moment the setup network went away.
        self.assertTrue(Path(path).exists(), "the working profile was deleted")
        self.assertEqual(Path(path).parent, self.dir)
        # It must not be allowed to compete until the join is verified.
        self.assertIn("autoconnect=false", text)
        self.assertIn(["nmcli", "connection", "modify", recorder.loaded_id,
                       "connection.autoconnect", "yes"], recorder.calls)

    @unittest.skipUnless(GLib, "GLib is not installed on this host")
    @unittest.skipUnless(NM_LIBRARY, "libnm is not installed on this host")
    def test_the_ssid_survives_network_managers_own_parser(self):
        # GLib is not the whole story: `ssid` has a second reader on top of it.
        # Writing it as text meant `65;66;` joined a network called `AB` and a
        # name containing a backslash lost it. Ask libnm, which is what the
        # keyfile plugin runs.
        for ssid in ("HomeWiFi", "Caf; #1", " Home ", "back\\slash", "65;66;",
                     "A\\;B", "x;y;z;", "123", "Café"):
            with self.subTest(ssid=ssid):
                directory = self.dir / ("rt-" + str(abs(hash(ssid))))
                directory.mkdir()
                recorder = Recorder()
                nm_module.Nmcli(runner=recorder).connect(
                    ssid, "correct horse", keyfile_dir=directory)
                text, _, _ = recorder.contents[0]
                self.assertEqual(_nm_parse(text)["ssid"], ssid,
                                 "NetworkManager would join a different network")

    @unittest.skipUnless(NM_LIBRARY, "libnm is not installed on this host")
    def test_the_passphrase_survives_network_managers_own_parser(self):
        for psk in ("pass;word#1", " space pass ", "back\\slash1", "correct horse"):
            with self.subTest(psk=psk):
                directory = self.dir / ("psk-" + str(abs(hash(psk))))
                directory.mkdir()
                recorder = Recorder()
                nm_module.Nmcli(runner=recorder).connect("Home", psk, keyfile_dir=directory)
                text, _, _ = recorder.contents[0]
                self.assertEqual(_nm_parse(text)["psk"], psk)

    def test_glib_accepts_the_file_at_all(self):
        # GLib is the first reader. A value GLib refuses is a file NetworkManager
        # never gets to. This is weaker than the libnm test above and says so.
        recorder = Recorder()
        nm_module.Nmcli(runner=recorder).connect("Caf; #1", "pass;word#1",
                                                 keyfile_dir=self.dir)
        text, _, _ = recorder.contents[0]
        GLib.KeyFile().load_from_data(text, len(text.encode("utf-8")),
                                      GLib.KeyFileFlags.NONE)

    def test_a_newline_in_a_password_is_refused_not_escaped(self):
        recorder = Recorder()
        with self.assertRaises(nm_module.NmError):
            nm_module.Nmcli(runner=recorder).connect("HomeWiFi", "abcdefgh\npsk-flags=1",
                                                     keyfile_dir=self.dir)
        self.assertEqual(recorder.calls, [], "a newline password reached nmcli")

    def test_a_network_name_longer_than_32_octets_is_refused(self):
        recorder = Recorder()
        with self.assertRaises(nm_module.NmError):
            nm_module.Nmcli(runner=recorder).connect("é" * 17, "correct horse",
                                                     keyfile_dir=self.dir)
        self.assertEqual(recorder.calls, [])

    def test_an_address_without_a_default_route_is_not_success(self):
        recorder = Recorder(gateway="")
        with self.assertRaises(nm_module.NmError) as caught:
            nm_module.Nmcli(runner=recorder).connect("HomeWiFi", "correct horse",
                                                     keyfile_dir=self.dir)
        self.assertIn("default route", str(caught.exception))

    def test_a_failed_activation_does_not_leave_a_competing_profile(self):
        recorder = Recorder(up_fails=True)
        with self.assertRaises(nm_module.NmError):
            nm_module.Nmcli(runner=recorder).connect("HomeWiFi", "correct horse",
                                                     keyfile_dir=self.dir)
        self.assertEqual(len(recorder.deleted), 1, "the failed profile was kept")
        self.assertEqual(list(self.dir.glob("*.nmconnection")), [],
                         "the failed profile file was kept")

    def test_a_link_local_address_is_not_a_usable_uplink(self):
        # The review's mutation removed this check and every test still passed,
        # because the doubles only ever raised their own exceptions. This one
        # goes through the adapter's own decision.
        for address in ("169.254.7.7", ""):
            with self.subTest(address=address):
                recorder = Recorder(address=address)
                with self.assertRaises(nm_module.NmError) as caught:
                    nm_module.Nmcli(runner=recorder).connect(
                        "HomeWiFi", "correct horse", keyfile_dir=self.dir)
                self.assertIn("no usable address", str(caught.exception))
                self.assertEqual(len(recorder.deleted), 1,
                                 "the unusable profile was kept for the next boot")

    def test_the_profile_is_pinned_to_the_radio_the_page_was_reached_over(self):
        recorder = Recorder()
        nm_module.Nmcli(runner=recorder).connect("HomeWiFi", "correct horse",
                                                 keyfile_dir=self.dir, interface="wlan0")
        text, _, _ = recorder.contents[0]
        self.assertIn("interface-name=wlan0", text)

    def test_a_join_that_comes_up_on_another_radio_is_refused(self):
        # Two Wi-Fi interfaces would otherwise let the household network come up
        # on the one nobody reached the page over.
        recorder = Recorder()
        with self.assertRaises(nm_module.NmError) as caught:
            nm_module.Nmcli(runner=recorder).connect(
                "HomeWiFi", "correct horse", keyfile_dir=self.dir, interface="wlan1")
        self.assertIn("different Wi-Fi interface", str(caught.exception))

    def test_an_unknown_active_profile_is_not_success(self):
        # A blank GENERAL.CONNECTION used to pass because the check only
        # rejected a *known different* name.
        recorder = Recorder(active_profile="HomeWiFi-old")
        with self.assertRaises(nm_module.NmError) as caught:
            nm_module.Nmcli(runner=recorder).connect("HomeWiFi", "correct horse",
                                                     keyfile_dir=self.dir)
        self.assertIn("different saved network", str(caught.exception))

    def test_a_bad_password_length_is_refused_before_anything_runs(self):
        recorder = Recorder()
        with self.assertRaises(nm_module.NmError):
            nm_module.Nmcli(runner=recorder).connect("HomeWiFi", "short",
                                                     keyfile_dir=self.dir)
        self.assertEqual(recorder.calls, [])


class ProfileStorageTests(Temp):
    """Where the household profile lives, and that it is still there later.

    `nmcli connection load` reads a profile from the keyfile plugin's own
    directories; it does not import an arbitrary file. The r2 acceptance review
    reproduced the old behaviour: the profile went to a process temporary
    directory, NetworkManager refused it, and the file was deleted afterwards
    anyway. A join that only works until the next reboot is not a join.
    """

    def setUp(self):
        super().setUp()
        self.profiles = self.dir / "system-connections"
        self.profiles.mkdir()
        patcher = patch.object(nm_module, "PROFILES_DIR", str(self.profiles))
        patcher.start()
        self.addCleanup(patcher.stop)

    def recorder(self, **kwargs):
        kwargs.setdefault("profile_dir", self.profiles)
        return Recorder(**kwargs)

    def test_the_profile_is_written_where_network_manager_reads_it(self):
        recorder = self.recorder()
        nm_module.Nmcli(runner=recorder).connect("HomeWiFi", "correct horse")
        text, mode, path = recorder.contents[0]
        self.assertEqual(Path(path).parent, self.profiles,
                         "the profile was staged somewhere NetworkManager does not read")
        self.assertTrue(path.endswith(".nmconnection"),
                        "the profile has no name the keyfile plugin will read")
        self.assertEqual(mode, 0o600, "the profile must be owner-only")
        self.assertTrue(Path(path).exists(),
                        "the working profile did not survive the join")
        self.assertIn("autoconnect=false", text,
                      "the trial profile may compete before the join is verified")
        self.assertEqual(recorder.modified, ["connection.autoconnect yes"],
                         "the profile was never promoted to autoconnect")

    def test_only_the_finished_profile_is_left_in_the_directory(self):
        recorder = self.recorder()
        nm_module.Nmcli(runner=recorder).connect("HomeWiFi", "correct horse")
        names = sorted(item.name for item in self.profiles.iterdir())
        self.assertEqual(len(names), 1, f"a staging file was left behind: {names}")
        self.assertTrue(names[0].endswith(".nmconnection"))

    def test_network_manager_never_sees_a_half_written_profile(self):
        # The keyfile plugin watches this directory. A file created under its
        # final name is parsed while it is still empty or half written, and a
        # crash leaves something that looks like a profile but is not one.
        seen = []
        real_fsync = os.fsync

        def watch(handle):
            seen.append(sorted(item.name for item in self.profiles.iterdir()))
            return real_fsync(handle)

        recorder = self.recorder()
        with patch.object(nm_module.os, "fsync", side_effect=watch):
            nm_module.Nmcli(runner=recorder).connect("HomeWiFi", "correct horse")
        self.assertTrue(seen, "the profile was never made durable")
        self.assertEqual([name for name in seen[0] if name.endswith(".nmconnection")], [],
                         f"a partial profile was visible while it was being written: {seen[0]}")

    def test_a_profile_that_does_not_work_leaves_nothing_behind(self):
        recorder = self.recorder(up_fails=True)
        with self.assertRaises(nm_module.NmError):
            nm_module.Nmcli(runner=recorder).connect("HomeWiFi", "correct horse")
        self.assertEqual(list(self.profiles.iterdir()), [],
                         "a profile that never worked is still in the directory")

    def test_another_network_already_saved_is_not_touched(self):
        existing = self.profiles / "home.nmconnection"
        existing.write_text("[connection]\nid=Home\n", encoding="utf-8")
        recorder = self.recorder(up_fails=True)
        with self.assertRaises(nm_module.NmError):
            nm_module.Nmcli(runner=recorder).connect("HomeWiFi", "correct horse")
        self.assertEqual(existing.read_text(encoding="utf-8"), "[connection]\nid=Home\n")
        self.assertEqual([item.name for item in self.profiles.iterdir()],
                         ["home.nmconnection"])

    def test_a_profile_that_cannot_be_saved_for_the_next_boot_is_a_failed_join(self):
        # Autoconnect off works until the reboot and then strands the device
        # with no network at all, so it is not a success with a warning.
        recorder = self.recorder(modify_fails=True)
        with self.assertRaises(nm_module.NmError) as caught:
            nm_module.Nmcli(runner=recorder).connect("HomeWiFi", "correct horse")
        self.assertIn("could not be saved for the next boot", str(caught.exception))
        self.assertEqual(len(recorder.deleted), 1, "the unsaved profile was kept")
        self.assertEqual(list(self.profiles.iterdir()), [],
                         "a profile that will not autoconnect was left behind")

    def test_the_profile_is_pinned_to_the_radio_that_was_used(self):
        recorder = self.recorder()
        nm_module.Nmcli(runner=recorder).connect("HomeWiFi", "correct horse",
                                                 interface="wlan0")
        text, _, _ = recorder.contents[0]
        self.assertIn("interface-name=wlan0", text)

    def test_a_join_that_comes_up_on_another_radio_is_not_success(self):
        recorder = self.recorder(interface="wlan1")
        with self.assertRaises(nm_module.NmError) as caught:
            nm_module.Nmcli(runner=recorder).connect("HomeWiFi", "correct horse",
                                                     interface="wlan0")
        self.assertIn("different Wi-Fi interface", str(caught.exception))
        self.assertEqual(list(self.profiles.iterdir()), [],
                         "the profile that came up on the wrong radio was kept")

    def test_a_directory_that_cannot_be_written_is_a_sentence_not_a_traceback(self):
        recorder = self.recorder()
        with patch.object(nm_module.tempfile, "mkstemp",
                          side_effect=PermissionError(13, "Permission denied")):
            with self.assertRaises(nm_module.NmError) as caught:
                nm_module.Nmcli(runner=recorder).connect("HomeWiFi", "correct horse")
        self.assertEqual(str(caught.exception),
                         "The Wi-Fi profile could not be saved on this device")
        self.assertEqual(recorder.calls, [], "a profile was loaded that was never written")


class MissingToolTests(unittest.TestCase):
    def test_the_error_names_the_tool_that_is_missing(self):
        # `iw` and `raspi-config` go through the same runner. Telling someone
        # their NetworkManager is absent when it is `raspi-config` that is
        # absent is a false statement about their device, shown on the page.
        with self.assertRaises(nm_module.NmError) as caught:
            nm_module._run(["/nonexistent/debra-test-tool", "--version"])
        self.assertIn("debra-test-tool", str(caught.exception))
        self.assertNotIn("nmcli", str(caught.exception))


class DeviceAddressTests(Temp):
    def test_the_access_point_address_is_read_from_the_device(self):
        recorder = Recorder()
        self.assertEqual(nm_module.Nmcli(runner=recorder).device_address("wlan0"),
                         "192.0.2.40")

    def test_a_device_with_no_address_is_none_rather_than_a_guess(self):
        def runner(argv, timeout=45):
            return ""
        self.assertIsNone(nm_module.Nmcli(runner=runner).device_address("wlan0"))
        self.assertIsNone(nm_module.Nmcli(runner=runner).device_address(None))


class HostnameTests(Temp):
    def test_a_valid_name_is_applied_not_only_recorded(self):
        network = FakeNetwork()
        self.onboarder(network).ensure_identity()
        self.assertIn(("set_hostname", "debra-demo1"), network.calls)

    def test_a_name_that_cannot_resolve_is_refused(self):
        recorder = Recorder()
        adapter = nm_module.Nmcli(runner=recorder)
        for bad in ("", "has space", "two.dots", "-leading", "x" * 64):
            with self.subTest(name=bad):
                with self.assertRaises(nm_module.NmError):
                    adapter.set_hostname(bad)
        self.assertEqual(recorder.calls, [], "an invalid name reached hostnamectl")
        adapter.set_hostname("debra-3c6b3f")
        self.assertEqual(recorder.calls, [["hostnamectl", "set-hostname", "debra-3c6b3f"]])

    def test_a_missing_hostnamectl_is_reported_without_losing_the_name(self):
        class Broken(FakeNetwork):
            def set_hostname(self, hostname):
                raise nm_module.NmError("hostnamectl is not installed")
        with self.assertLogs(onboarding.LOGGER, level="WARNING"):
            status = self.onboarder(Broken()).start_hotspot()
        self.assertEqual(status["hostname"], "debra-demo1")


class AdmissionTests(Temp):
    """One attempt in flight, enforced before the page is answered."""

    def test_two_requests_cannot_both_be_admitted(self):
        onboarder = self.onboarder()
        onboarder.start_hotspot()
        results = []
        barrier = threading.Barrier(2)

        def attempt():
            barrier.wait()
            results.append(onboarder.admit("HomeWiFi")[0])

        threads = [threading.Thread(target=attempt) for _ in range(2)]
        for thread in threads:
            thread.start()
        for thread in threads:
            thread.join()
        self.assertEqual(sorted(results), [False, True],
                         "two requests were admitted for one device")

    def test_a_reserved_worker_abandons_if_the_state_moved_on(self):
        network = FakeNetwork()
        onboarder = self.onboarder(network)
        onboarder.start_hotspot()
        self.assertTrue(onboarder.admit("First")[0])
        # A second network is reserved by someone else in the meantime.
        data = state_module.read(self.state_path)
        data["ssid"] = "Second"
        state_module.write(self.state_path, data)
        before = len(network.calls)
        status = onboarder.join_reserved("First", "correct horse")
        self.assertEqual(len(network.calls), before,
                         "the abandoned worker touched the network")
        self.assertEqual(status["phase"], "connecting")

    def test_a_second_admission_is_refused_while_one_is_in_flight(self):
        onboarder = self.onboarder()
        onboarder.start_hotspot()
        self.assertTrue(onboarder.admit("HomeWiFi")[0])
        self.assertEqual(onboarder.admit("HomeWiFi"), (False, "busy"))


class BaselineRetryTests(Temp):
    def test_an_online_boot_still_takes_the_missing_baseline(self):
        network = FakeNetwork()
        network.joined = "HomeWiFi"
        onboarder = self.onboarder(network)
        data = state_module.blank("debra-demo1")
        data.update(phase="online", ssid="HomeWiFi", address="192.0.2.40")
        state_module.write(self.state_path, data)
        status = onboarder.resume()
        self.assertEqual(status["phase"], "online")
        self.assertIsNotNone(status["baseline"],
                             "a device that was already online never took its baseline")

    def test_a_pointer_to_a_missing_baseline_does_not_suppress_a_capture(self):
        network = FakeNetwork()
        network.joined = "HomeWiFi"
        onboarder = self.onboarder(network)
        data = state_module.blank("debra-demo1")
        data.update(phase="online", ssid="HomeWiFi", address="192.0.2.40",
                    baseline=str(self.baseline_dir / "baseline-gone.tar.gz"))
        state_module.write(self.state_path, data)
        status = onboarder.resume()
        self.assertIsNotNone(status["baseline"],
                             "a pointer to a deleted archive suppressed the capture")
        self.assertTrue(Path(status["baseline"]).is_file())

    def test_a_capture_failure_is_recorded_and_shown_not_swallowed(self):
        network = FakeNetwork()
        network.joined = "HomeWiFi"
        onboarder = self.onboarder(network)
        data = state_module.blank("debra-demo1")
        data.update(phase="online", ssid="HomeWiFi", address="192.0.2.40")
        state_module.write(self.state_path, data)
        # A real ENOSPC carries the path it failed on. The page must say what
        # happened without publishing the device's layout.
        failure = OSError(28, "No space left on device",
                          "/var/lib/debra/setup/baseline/.baseline-1.tar.gz.part")
        with patch.object(baseline_module, "capture", side_effect=failure):
            with self.assertLogs(onboarding.LOGGER, level="WARNING"):
                status = onboarder.resume()
        self.assertIsNone(status["baseline"])
        self.assertEqual(status["baseline_error"], "The device is out of disk space")
        self.assertNotIn("/var/lib/debra", status["baseline_error"])
        # The next boot tries again rather than believing it is done.
        status = onboarder.resume()
        self.assertIsNotNone(status["baseline"])
        self.assertIsNone(status["baseline_error"])


class ErrorBoundaryTests(unittest.TestCase):
    """Raw NetworkManager text never reaches the page or the state."""

    def test_a_passphrase_in_nmcli_output_is_not_reported_back(self):
        class Runner:
            def __call__(self, argv, timeout=45):
                if argv[1:3] == ["connection", "load"]:
                    return ""
                raise nm_module.NmError(
                    nm_module.public_failure(
                        "Error: 802-11-wireless-security.psk: 'SYNTHETIC-SECRET-123' is wrong", 4))

        with tempfile.TemporaryDirectory(prefix="nm-", dir="/tmp/opencode") as directory:
            with self.assertRaises(nm_module.NmError) as caught:
                nm_module.Nmcli(runner=Runner()).connect("HomeWiFi", "SYNTHETIC-SECRET-123",
                                                         keyfile_dir=directory)
        self.assertNotIn("SYNTHETIC-SECRET-123", str(caught.exception))

    def test_an_unknown_failure_is_bounded_and_carries_no_external_text(self):
        message = nm_module.public_failure("Error: something odd with 'a secret'", 10)
        self.assertNotIn("secret", message)
        self.assertIn("failure 10", message)

    def test_the_known_failures_become_sentences_a_person_can_act_on(self):
        self.assertEqual(nm_module.public_failure("Secrets were required, but not provided.", 4),
                         "The Wi-Fi password was refused by the network")
        self.assertEqual(nm_module.public_failure("Error: No network with SSID 'X' found.", 10),
                         "That network was not found")

    def test_multicast_and_broadcast_are_not_device_addresses(self):
        for address in ("224.0.0.1", "255.255.255.255", "0.0.0.0", "169.254.1.1", "127.0.0.1"):
            self.assertFalse(nm_module.routable(address), address)
        for address in ("192.168.1.40", "10.42.0.1"):
            self.assertTrue(nm_module.routable(address), address)


class FailedWithoutHotspotTests(Temp):
    def test_a_join_on_a_failed_device_with_no_access_point_is_refused_not_crashed(self):
        onboarder = self.onboarder()
        data = state_module.blank("debra-demo1")
        data.update(phase="failed", last_error="No Wi-Fi interface was found", hotspot=None)
        state_module.write(self.state_path, data)
        server = onboarding.Portal(("127.0.0.1", 0), onboarder, onboarding.ASSETS / "setup.html")
        host = "127.0.0.1:%d" % server.server_port
        server.host = host
        thread = threading.Thread(target=server.serve_forever, daemon=True)
        thread.start()
        try:
            request = urllib.request.Request(
                "http://" + host + "/api/join",
                data=json.dumps({"ssid": "HomeWiFi", "psk": "correct horse"}).encode(),
                method="POST")
            request.add_header("Host", host)
            request.add_header("Content-Type", "application/json")
            try:
                with urllib.request.urlopen(request, timeout=10) as response:
                    code = response.status
            except urllib.error.HTTPError as exc:
                code = exc.code
        finally:
            server.shutdown()
            thread.join()
        # No access point means nothing to hand over to; the page must get a
        # refusal, not a dropped connection from a TypeError in the handler.
        self.assertEqual(code, 409)


class BaselineAtomicityTests(Temp):
    def test_a_full_disk_leaves_no_archive_that_looks_complete(self):
        root = self.dir / "fake-root"
        (root / "etc").mkdir(parents=True)
        (root / "etc" / "hostname").write_text("debra-demo1\n")
        real_open = os.open

        def failing_open(path, flags, mode=0o777):
            if str(path).endswith(".part"):
                raise OSError(28, "No space left on device")
            return real_open(path, flags, mode)

        with patch.object(baseline_module.os, "open", side_effect=failing_open):
            with self.assertRaises(OSError):
                baseline_module.capture(self.baseline_dir, root=root, stamp="T1")
        names = sorted(path.name for path in self.baseline_dir.iterdir())
        self.assertEqual(names, [], f"a failed capture left {names}")
        self.assertIsNone(baseline_module.latest(self.baseline_dir))

    def test_a_complete_capture_is_readable_and_owner_only(self):
        root = self.dir / "fake-root"
        (root / "etc").mkdir(parents=True)
        (root / "etc" / "hostname").write_text("debra-demo1\n")
        manifest = baseline_module.capture(self.baseline_dir, root=root, stamp="T2")
        self.assertEqual(manifest["captured"], ["etc/hostname"])
        archive = self.baseline_dir / manifest["archive"]
        self.assertEqual(stat.S_IMODE(archive.stat().st_mode), 0o600)
        self.assertEqual(baseline_module.latest(self.baseline_dir)["archive"], manifest["archive"])


class ActiveProfileTests(Temp):
    class Runner:
        """Answers nmcli like a device whose saved profile won the race."""

        def __init__(self, active):
            self.active, self.calls = active, []

        def __call__(self, argv, timeout=45):
            self.calls.append(list(argv))
            if argv[1:3] == ["connection", "load"]:
                return ""
            if argv[1:4] == ["connection", "up", "id"]:
                return ""
            if argv[1:] == ["-t", "-f", "DEVICE,TYPE,STATE", "device", "status"]:
                return "wlan0:wifi:connected\n"
            if argv[1:3] == ["-t", "-f"] and argv[4:6] == ["device", "show"]:
                if "GENERAL.CONNECTION" in argv[3]:
                    return f"GENERAL.CONNECTION:{self.active}\n"
                return "IP4.ADDRESS[1]:192.0.2.40/24\nIP4.GATEWAY:192.0.2.1\n"
            return ""

    def test_a_different_active_profile_is_not_success(self):
        runner = self.Runner("HomeWiFi-old")
        with self.assertRaises(nm_module.NmError) as caught:
            nm_module.Nmcli(runner=runner).connect("HomeWiFi", "correct horse",
                                                   keyfile_dir=self.dir)
        self.assertIn("different saved network", str(caught.exception))

    def test_the_profile_that_was_just_loaded_is_success(self):
        runner = self.Runner("placeholder")
        # The loaded profile id is generated per call, so read it from the argv.
        def answer(argv, timeout=45):
            if argv[1:3] == ["connection", "load"]:
                return ""
            if argv[1:4] == ["connection", "up", "id"]:
                runner.active = argv[4]
                return ""
            return runner(argv, timeout)
        result = nm_module.Nmcli(runner=answer).connect("HomeWiFi", "correct horse",
                                                        keyfile_dir=self.dir)
        self.assertEqual(result["address"], "192.0.2.40")


class ScanTests(Temp):
    """Nearby networks are offered, never required."""

    def test_the_scan_result_reaches_the_page(self):
        status = self.onboarder(FakeNetwork()).start_hotspot()
        self.assertEqual([item["ssid"] for item in status["networks"]],
                         ["HomeWiFi", "Neighbour", "Cafe"])
        self.assertEqual(status["networks"][0]["security"], "WPA2")

    def test_a_failed_scan_is_an_empty_list_not_a_failed_hotspot(self):
        network = FakeNetwork()
        network.behaviour = "scan-fails"
        status = self.onboarder(network).start_hotspot()
        self.assertEqual(status["phase"], "hotspot")
        self.assertEqual(status["networks"], [])

    def test_an_adapter_with_no_scan_at_all_still_raises_the_access_point(self):
        class NoScan(FakeNetwork):
            scan = None  # not a callable: the adapter does not have one
        status = self.onboarder(NoScan()).start_hotspot()
        self.assertEqual(status["phase"], "hotspot")
        self.assertEqual(status["networks"], [])

    def test_no_scan_happens_when_the_access_point_is_already_up(self):
        # Scanning with the AP up can drop the person's phone off it, so a
        # re-raise must not scan.
        network = FakeNetwork()
        onboarder = self.onboarder(network)
        onboarder.start_hotspot()
        before = [call for call in network.calls if call[0] == "scan"]
        onboarder.start_hotspot()
        after = [call for call in network.calls if call[0] == "scan"]
        self.assertEqual(len(after), len(before), "a re-raise scanned with the AP up")


class ScanParsingTests(unittest.TestCase):
    class Runner:
        def __init__(self, output):
            self.output, self.calls = output, []

        def __call__(self, argv, timeout=45):
            self.calls.append(list(argv))
            return self.output

    def test_an_escaped_colon_in_a_name_is_one_field(self):
        runner = self.Runner("Home\\:WiFi:82:WPA2\n")
        found = nm_module.Nmcli(runner=runner).scan("wlan0")
        self.assertEqual(found, [{"ssid": "Home:WiFi", "signal": 82, "security": "WPA2"}])

    def test_hidden_networks_are_skipped_and_duplicates_keep_the_strongest(self):
        runner = self.Runner("Home:40:WPA2\n:99:WPA2\nHome:88:WPA3\n")
        found = nm_module.Nmcli(runner=runner).scan("wlan0")
        self.assertEqual(len(found), 1)
        self.assertEqual(found[0]["signal"], 88)
        self.assertEqual(found[0]["security"], "WPA3")

    def test_strongest_first_and_bounded(self):
        lines = "".join(f"Net{n}:{n}:WPA2\n" for n in range(30))
        found = nm_module.Nmcli(runner=self.Runner(lines)).scan("wlan0", limit=5)
        self.assertEqual(len(found), 5)
        self.assertEqual([item["signal"] for item in found], [29, 28, 27, 26, 25])

    def test_a_scan_asks_for_a_rescan_on_the_named_interface(self):
        runner = self.Runner("")
        nm_module.Nmcli(runner=runner).scan("wlan0")
        self.assertIn("--rescan", runner.calls[0])
        self.assertEqual(runner.calls[0][-2:], ["ifname", "wlan0"])

    def test_a_failing_scan_returns_nothing(self):
        class Broken:
            def __call__(self, argv, timeout=45):
                raise nm_module.NmError("nmcli did not answer in time")
        self.assertEqual(nm_module.Nmcli(runner=Broken()).scan("wlan0"), [])
        self.assertEqual(nm_module.Nmcli(runner=Broken()).scan(None), [])


class FailurePathScanTests(Temp):
    def test_a_failed_join_does_not_rescan_before_raising_the_access_point(self):
        # The AP is about to come back. A scan can take tens of seconds, and the
        # person would be disconnected with no page for that long.
        network = FakeNetwork(behaviour="bad-psk")
        onboarder = self.onboarder(network)
        onboarder.start_hotspot()
        scans_before = len([call for call in network.calls if call[0] == "scan"])
        onboarder.join("HomeWiFi", "wrong password")
        scans_after = len([call for call in network.calls if call[0] == "scan"])
        self.assertEqual(scans_after, scans_before,
                         "a failed join scanned before restoring the access point")
        # The first boot's list is still offered.
        self.assertEqual(len(onboarder.status()["networks"]), 3)


class ReservationTests(Temp):
    """One reservation, identified by a token, not by a network name."""

    def test_a_retry_of_the_same_network_supersedes_the_old_worker(self):
        # The same SSID can be tried twice with a corrected password, so the
        # network name cannot identify which attempt a worker belongs to. The
        # token can, and the old worker must lose.
        network = FakeNetwork()
        onboarder = self.onboarder(network)
        onboarder.start_hotspot()
        accepted, old_token = onboarder.admit("Home")
        self.assertTrue(accepted)
        onboarder.release(old_token)
        onboarder._last_submit = 0.0
        accepted, new_token = onboarder.admit("Home")
        self.assertTrue(accepted)
        self.assertNotEqual(old_token, new_token,
                            "two attempts in one second share a token")
        before = len(network.calls)
        with self.assertLogs(onboarding.LOGGER, level="WARNING"):
            status = onboarder.join_reserved("Home", "old password", token=old_token)
        self.assertEqual(len(network.calls), before,
                         "the superseded worker touched the network")
        self.assertEqual(status["phase"], "connecting")
        # The current reservation still works.
        status = onboarder.join_reserved("Home", "correct horse", token=new_token)
        self.assertEqual(status["phase"], "online")

    def test_a_reply_that_cannot_be_delivered_releases_the_reservation(self):
        network = FakeNetwork()
        onboarder = self.onboarder(network)
        onboarder.start_hotspot()
        accepted, token = onboarder.admit("HomeWiFi")
        self.assertTrue(accepted)
        self.assertEqual(state_module.read(self.state_path)["attempts"], 1)
        onboarder.release(token)
        data = state_module.read(self.state_path)
        self.assertEqual(data["phase"], "hotspot")
        self.assertIsNone(data["attempt_token"])
        self.assertEqual(data["attempts"], 0, "a released attempt still counted")
        onboarder._last_submit = 0.0
        self.assertTrue(onboarder.admit("HomeWiFi")[0],
                        "the device stayed busy after a lost reply")

    def test_releasing_a_superseded_reservation_changes_nothing(self):
        network = FakeNetwork()
        onboarder = self.onboarder(network)
        onboarder.start_hotspot()
        _, first = onboarder.admit("Home")
        onboarder.release(first)
        onboarder._last_submit = 0.0
        _, second = onboarder.admit("Home")
        onboarder.release(first)
        self.assertEqual(state_module.read(self.state_path)["attempt_token"], second,
                         "a stale release cancelled the current attempt")


class CountryOrderingTests(Temp):
    """The country is a radio change, so it happens after the page is answered."""

    def test_admitting_never_touches_the_radio(self):
        network = FakeNetwork()
        onboarder = self.onboarder(network)
        onboarder.start_hotspot()
        before = list(network.calls)
        accepted, _ = onboarder.admit("HomeWiFi")
        self.assertTrue(accepted)
        self.assertEqual(network.calls, before,
                         "the radio was touched before the reply was written")
        self.assertIsNone(state_module.read(self.state_path)["country"])

    def test_the_country_is_set_after_the_access_point_is_down(self):
        network = FakeNetwork()
        onboarder = self.onboarder(network)
        onboarder.start_hotspot()
        _, token = onboarder.admit("HomeWiFi")
        network.calls.clear()
        status = onboarder.join_reserved("HomeWiFi", "correct horse", "GB", token)
        self.assertEqual(status["phase"], "online")
        phases = network.phases()
        self.assertLess(phases.index("stop_hotspot"), phases.index("set_country"),
                        "the country was set while the setup network was still up")
        self.assertLess(phases.index("set_country"), phases.index("connect"))
        self.assertEqual(state_module.read(self.state_path)["country"], "GB")

    def test_a_country_that_cannot_be_set_brings_the_setup_network_back(self):
        class NoCountry(FakeNetwork):
            def set_country(self, code):
                self.calls.append(("set_country", code))
                raise nm_module.NmError("The Wi-Fi radio is switched off")
        network = NoCountry()
        onboarder = self.onboarder(network)
        onboarder.start_hotspot()
        _, token = onboarder.admit("HomeWiFi")
        status = onboarder.join_reserved("HomeWiFi", "correct horse", "GB", token)
        self.assertEqual(status["phase"], "failed")
        self.assertEqual(status["last_error"], "The Wi-Fi radio is switched off")
        self.assertNotIn("connect", network.phases())


class RunnerBoundaryTests(unittest.TestCase):
    """`_run` itself, not a double of it: what actually leaves the boundary."""

    class Result:
        def __init__(self, returncode, stdout="", stderr=""):
            self.returncode, self.stdout, self.stderr = returncode, stdout, stderr

    def test_raw_stderr_never_leaves_the_runner(self):
        result = self.Result(4, stderr="Error: psk: 'SYNTHETIC-SECRET-123' is wrong")
        with patch.object(nm_module.subprocess, "run", return_value=result):
            with self.assertRaises(nm_module.NmError) as caught:
                nm_module._run(["nmcli", "connection", "up", "id", "x"])
        self.assertNotIn("SYNTHETIC-SECRET-123", str(caught.exception))
        self.assertEqual(str(caught.exception), "NetworkManager reported failure 4")

    def test_a_missing_binary_names_the_tool_and_no_path(self):
        failure = FileNotFoundError(2, "No such file or directory", "/usr/bin/nmcli")
        with patch.object(nm_module.subprocess, "run", side_effect=failure):
            with self.assertRaises(nm_module.NmError) as caught:
                nm_module._run(["nmcli", "radio", "wifi"])
        self.assertEqual(str(caught.exception), "nmcli is not installed")
        self.assertNotIn("/usr/bin", str(caught.exception))

    def test_a_permission_failure_names_no_path(self):
        failure = PermissionError(
            13, "Permission denied",
            "/etc/NetworkManager/system-connections/home.nmconnection")
        with patch.object(nm_module.subprocess, "run", side_effect=failure):
            with self.assertRaises(nm_module.NmError) as caught:
                nm_module._run(["nmcli", "radio", "wifi"])
        self.assertEqual(str(caught.exception), "nmcli could not be run")
        self.assertNotIn("system-connections", str(caught.exception))

    def test_a_timeout_carries_no_command_line(self):
        with patch.object(nm_module.subprocess, "run",
                          side_effect=nm_module.subprocess.TimeoutExpired(["nmcli", "x"], 45)):
            with self.assertRaises(nm_module.NmError) as caught:
                nm_module._run(["nmcli", "x"])
        self.assertEqual(str(caught.exception), "nmcli did not answer in time")
        self.assertIsNone(caught.exception.__cause__, "a traceback carries the argv")


class BaselinePublishTests(Temp):
    """A baseline is never overwritten, never archives itself, never lies."""

    def root_with(self, name="hostname", text="debra-demo1\n"):
        root = self.dir / "publish-root"
        (root / "etc").mkdir(parents=True, exist_ok=True)
        (root / "etc" / name).write_text(text)
        return root

    def test_two_captures_in_the_same_second_do_not_overwrite_each_other(self):
        root = self.root_with()
        first = baseline_module.capture(self.baseline_dir, root=root, stamp="SAME")
        second = baseline_module.capture(self.baseline_dir, root=root, stamp="SAME")
        self.assertNotEqual(first["archive"], second["archive"])
        for manifest in (first, second):
            self.assertTrue((self.baseline_dir / manifest["archive"]).is_file())
        # The newest one is the one reported, and its hash still matches.
        self.assertEqual(baseline_module.latest(self.baseline_dir)["archive"],
                         second["archive"])

    def test_a_baseline_never_archives_its_own_directory(self):
        # The capture reads var/lib/debra, which is where the baselines live. A
        # capture that included itself would grow on every retry until the size
        # cap failed for ever.
        root = self.dir / "self-root"
        (root / "var" / "lib" / "debra").mkdir(parents=True)
        (root / "var" / "lib" / "debra" / "note.txt").write_text("hello\n")
        destination = root / "var" / "lib" / "debra" / "baseline"
        first = baseline_module.capture(destination, root=root, stamp="A")
        second = baseline_module.capture(destination, root=root, stamp="B")
        self.assertNotIn("var/lib/debra/baseline", " ".join(first["captured"]))
        self.assertIn("var/lib/debra/note.txt", first["captured"])
        self.assertEqual(first["captured"], second["captured"],
                         "the second capture archived the first baseline")

    def test_latest_ignores_a_manifest_whose_archive_is_damaged(self):
        root = self.root_with()
        manifest = baseline_module.capture(self.baseline_dir, root=root, stamp="C1")
        archive = self.baseline_dir / manifest["archive"]
        archive.write_bytes(b"not the archive the manifest describes")
        self.assertIsNone(baseline_module.latest(self.baseline_dir),
                          "a damaged archive was reported as the known-good point")

    def test_latest_ignores_a_manifest_whose_archive_is_gone(self):
        root = self.root_with()
        manifest = baseline_module.capture(self.baseline_dir, root=root, stamp="C2")
        (self.baseline_dir / manifest["archive"]).unlink()
        self.assertIsNone(baseline_module.latest(self.baseline_dir))

    def test_a_newer_damaged_baseline_falls_back_to_the_older_whole_one(self):
        root = self.root_with()
        good = baseline_module.capture(self.baseline_dir, root=root, stamp="D1")
        damaged = baseline_module.capture(self.baseline_dir, root=root, stamp="D2")
        (self.baseline_dir / damaged["archive"]).write_bytes(b"truncated")
        self.assertEqual(baseline_module.latest(self.baseline_dir)["archive"],
                         good["archive"])

    def test_a_manifest_that_cannot_be_published_removes_its_archive(self):
        root = self.root_with()
        real_link = os.link
        calls = {"n": 0}

        def failing_link(src, dst):
            # The archive is published first; the manifest is the second link.
            calls["n"] += 1
            if calls["n"] == 2:
                raise OSError(28, "No space left on device")
            return real_link(src, dst)

        with patch.object(baseline_module.os, "link", side_effect=failing_link):
            with self.assertRaises(OSError):
                baseline_module.capture(self.baseline_dir, root=root, stamp="E1")
        names = sorted(path.name for path in self.baseline_dir.iterdir())
        self.assertEqual(names, [], f"an archive with no manifest was left: {names}")


class CaptivePortalTests(Temp):
    """A phone should offer to open the page instead of being told to type it."""

    def setUp(self):
        super().setUp()
        self.network = FakeNetwork()
        self.onboarder = self.onboarder(self.network)
        self.onboarder.start_hotspot()
        self.server = onboarding.Portal(("127.0.0.1", 0), self.onboarder,
                                        onboarding.ASSETS / "setup.html")
        self.host = "127.0.0.1:%d" % self.server.server_port
        self.server.host = self.host
        self.thread = threading.Thread(target=self.server.serve_forever, daemon=True)
        self.thread.start()

    def tearDown(self):
        self.server.shutdown()
        self.thread.join()
        super().tearDown()

    def probe(self, path, host=None, method="GET"):
        request = urllib.request.Request("http://" + self.host + path, method=method)
        request.add_header("Host", host or self.host)
        opener = urllib.request.build_opener(NoRedirect)
        try:
            with opener.open(request, timeout=10) as response:
                return response.status, response.headers.get("Location"), response.read()
        except urllib.error.HTTPError as exc:
            return exc.code, exc.headers.get("Location"), exc.read()

    def test_every_known_probe_redirects_to_the_page(self):
        for path in sorted(onboarding.CAPTIVE_PROBES):
            with self.subTest(path=path):
                code, location, _ = self.probe(path)
                self.assertEqual(code, 302)
                self.assertEqual(location, f"http://{self.host}/")

    def test_a_probe_with_the_operating_systems_own_host_still_redirects(self):
        # The OS asks for these paths with its own name, so the same-origin
        # check must not apply. It is the page that must stay same-origin.
        code, location, _ = self.probe("/generate_204",
                                       host="connectivitycheck.gstatic.com")
        self.assertEqual(code, 302)
        self.assertEqual(location, f"http://{self.host}/",
                         "the redirect was built from the attacker-controlled Host")

    def test_a_head_probe_gets_the_redirect_and_no_body(self):
        code, location, body = self.probe("/hotspot-detect.html", method="HEAD")
        self.assertEqual(code, 302)
        self.assertEqual(location, f"http://{self.host}/")
        self.assertEqual(body, b"")

    def test_an_unknown_path_is_still_refused(self):
        # Not a probe, so it is not redirected: the redirect is only for the
        # handful of paths an operating system actually asks for.
        code, location, _ = self.probe("/admin", host="connectivitycheck.gstatic.com")
        self.assertEqual((code, location), (404, None))
        code, location, _ = self.probe("/admin")
        self.assertEqual((code, location), (404, None))

    def test_the_page_itself_is_still_same_origin_only(self):
        code, _, _ = self.probe("/", host="evil.example")
        self.assertEqual(code, 403)


class NoRedirect(urllib.request.HTTPRedirectHandler):
    """Ask for the response itself, not the page it points at."""

    def redirect_request(self, *args, **kwargs):
        return None


class BootRepairTests(Temp):
    """What a real boot does, not what a helper does when called twice."""

    def test_a_boot_retries_a_device_name_that_was_never_applied(self):
        # The name is saved before it is applied. The first boot fails to apply
        # it; the second must try again, because the page advertises that name.
        network = FakeNetwork()
        network.fail_hostname = True
        with self.assertLogs(onboarding.LOGGER, level="WARNING"):
            self.onboarder(network).resume()
        self.assertEqual(state_module.read(self.state_path)["hostname"], "debra-demo1")
        self.assertIsNone(getattr(network, "hostname_applied", None))
        network.fail_hostname = False
        # A second boot is a new Onboarder over the same state.
        self.onboarder(network).resume()
        applied = [call for call in network.calls if call[0] == "set_hostname"]
        self.assertEqual(len(applied), 2, "the second boot did not retry the name")
        self.assertEqual(network.hostname_applied, "debra-demo1")

    def test_a_boot_that_is_already_online_also_applies_the_name(self):
        network = FakeNetwork()
        network.joined = "HomeWiFi"
        self.onboarder(network).resume()
        self.assertEqual(network.hostname_applied, "debra-demo1",
                         "an online boot skipped applying the device name")
        self.assertEqual(state_module.read(self.state_path)["phase"], "online")


class DamagedBaselineTests(Temp):
    """A saved pointer that does not verify is not a recovery point."""

    def root_with(self):
        root = self.dir / "capture-root"
        (root / "etc").mkdir(parents=True)
        (root / "etc" / "hostname").write_text("debra-demo1\n")
        return root

    def capture_with(self, root):
        return baseline_module.capture(self.baseline_dir, root=root, stamp="R1")

    def test_a_damaged_archive_does_not_suppress_the_next_capture(self):
        root = self.root_with()
        manifest = self.capture_with(root)
        archive = self.baseline_dir / manifest["archive"]
        archive.write_bytes(b"")
        network = FakeNetwork()
        network.joined = "HomeWiFi"
        onboarder = self.onboarder(network, root=str(root))
        data = state_module.blank("debra-demo1")
        data.update(phase="online", ssid="Home", address="192.0.2.5",
                    baseline=str(archive))
        state_module.write(self.state_path, data)
        status = onboarder.resume()
        self.assertIsNotNone(status["baseline"], "an empty archive was believed")
        self.assertNotEqual(status["baseline"], str(archive))
        self.assertTrue(baseline_module.verified(self.baseline_dir, status["baseline"]))
        self.assertIsNone(status["baseline_error"])

    def test_the_damage_is_reported_while_it_is_still_the_record(self):
        root = self.root_with()
        manifest = self.capture_with(root)
        (self.baseline_dir / manifest["archive"]).write_bytes(b"truncated")
        network = FakeNetwork()
        network.joined = "HomeWiFi"
        onboarder = self.onboarder(network, root=str(root))
        data = state_module.blank("debra-demo1")
        data.update(phase="online", address="192.0.2.5",
                    baseline=str(self.baseline_dir / manifest["archive"]))
        state_module.write(self.state_path, data)
        with self.assertLogs(onboarding.LOGGER, level="WARNING") as logs:
            status = onboarder.resume()
        self.assertIn("does not verify", "\n".join(logs.output))
        self.assertIsNotNone(status["baseline"], "no replacement was captured")

    def test_a_whole_baseline_with_no_recorded_pointer_is_adopted(self):
        # A pointer write can fail on a full disk while the archive itself was
        # written. Capturing another one is exactly what that disk cannot afford.
        root = self.root_with()
        existing = self.capture_with(root)
        network = FakeNetwork()
        network.joined = "HomeWiFi"
        onboarder = self.onboarder(network, root=str(root))
        data = state_module.blank("debra-demo1")
        data.update(phase="online", address="192.0.2.5")
        state_module.write(self.state_path, data)
        with self.assertLogs(onboarding.LOGGER, level="WARNING") as logs:
            status = onboarder.resume()
        self.assertIn("Adopted", "\n".join(logs.output))
        self.assertEqual(status["baseline"],
                         str(self.baseline_dir / existing["archive"]))
        self.assertEqual(len(list(self.baseline_dir.glob("baseline-*.tar.gz"))), 1,
                         "a second baseline was captured on top of a whole one")


class CaptureIntegrityTests(Temp):
    """A member's size comes from the bytes that were read, not a second stat."""

    def root_with(self, size=2048):
        root = self.dir / "race-root"
        (root / "etc").mkdir(parents=True)
        (root / "etc" / "hostname").write_bytes(b"A" * size)
        return root

    def test_the_header_is_not_built_from_a_second_stat(self):
        # `gettarinfo()` stats the path again. When a writer truncated the file
        # between the read and that stat, the archive held the old buffer with
        # the new, shorter size: a silently cut member reported as captured.
        root = self.root_with()
        import tarfile as tarfile_module
        with patch.object(tarfile_module.TarFile, "gettarinfo",
                          side_effect=AssertionError("metadata was taken from a second stat")):
            manifest = baseline_module.capture(self.baseline_dir, root=str(root), stamp="S1")
        self.assertIn("etc/hostname", manifest["captured"])
        with tarfile_module.open(self.baseline_dir / manifest["archive"]) as tar:
            member = tar.getmember("etc/hostname")
            self.assertEqual(member.size, 2048)
            self.assertEqual(tar.extractfile(member).read(), b"A" * 2048)

    def test_a_file_truncated_during_the_read_is_skipped_not_cut(self):
        # The other half of the same window: the file shrinks while it is being
        # read, so the bytes and the size disagree. Either it is skipped or it
        # is whole; a member that is neither is the defect.
        root = self.root_with()
        real_open = open
        state = {"done": False}

        class Shrinking:
            def __init__(self, path):
                self._file = real_open(path, "rb")

            def fileno(self):
                return self._file.fileno()

            def read(self, size=-1):
                if not state["done"]:
                    state["done"] = True
                    (root / "etc" / "hostname").write_bytes(b"x")
                return self._file.read(size)

            def __enter__(self):
                return self

            def __exit__(self, *args):
                self._file.close()

        def fake_open(path, *args, **kwargs):
            if str(path).endswith("etc/hostname"):
                return Shrinking(path)
            return real_open(path, *args, **kwargs)

        with patch("builtins.open", fake_open):
            manifest = baseline_module.capture(self.baseline_dir, root=str(root), stamp="S2")
        self.assertNotIn("etc/hostname", manifest["captured"],
                         "a file that changed under the read was recorded as whole")
        reasons = {item["path"]: item["reason"] for item in manifest["skipped"]}
        self.assertEqual(reasons.get("etc/hostname"), "changed while being read")


class WorkerOwnershipTests(Temp):
    """Checking a token is not claiming it."""

    def busy_network(self, gate, event, seen):
        class Slow(FakeNetwork):
            def stop_hotspot(slow):
                slow.calls.append(("stop_hotspot",))
                slow.hotspot = None
                seen.append("stopping")
                gate.wait(5)
                event.set()
        return Slow()

    def test_two_workers_with_the_same_token_join_once(self):
        gate = threading.Event()
        event = threading.Event()
        seen = []
        network = self.busy_network(gate, event, seen)
        onboarder = self.onboarder(network)
        onboarder.start_hotspot()
        _, token = onboarder.admit("HomeWiFi")
        results = []

        def worker():
            results.append(onboarder.join_reserved("HomeWiFi", "correct horse", token=token))

        first = threading.Thread(target=worker)
        first.start()
        for _ in range(500):
            if event.is_set() or len(seen) == 1:
                break
            threading.Event().wait(0.01)
        second = threading.Thread(target=worker)
        second.start()
        threading.Event().wait(0.05)
        gate.set()
        first.join(10)
        second.join(10)
        joins = [call for call in network.calls if call[0] == "connect"]
        self.assertEqual(len(joins), 1, f"the same reservation joined {len(joins)} times")
        self.assertEqual(len(results), 2)

    def test_a_worker_superseded_after_its_check_cannot_settle_the_new_attempt(self):
        gate = threading.Event()
        event = threading.Event()
        seen = []
        network = self.busy_network(gate, event, seen)
        onboarder = self.onboarder(network)
        onboarder.start_hotspot()
        _, old_token = onboarder.admit("HomeWiFi")
        done = []

        def worker():
            done.append(onboarder.join_reserved("HomeWiFi", "correct horse", token=old_token))

        thread = threading.Thread(target=worker)
        thread.start()
        for _ in range(500):
            if seen:
                break
            threading.Event().wait(0.01)
        # A new generation of the attempt appears while the old worker is still
        # inside `stop_hotspot()`: the same effect a reboot-seeded retry or any
        # other writer of this record would have.
        new_token = secrets.token_hex(8)
        data = state_module.read(self.state_path)
        data.update(phase="connecting", ssid="HomeWiFi", attempt_token=new_token,
                    attempt_claimed=False)
        state_module.write(self.state_path, data)
        gate.set()
        thread.join(10)
        data = state_module.read(self.state_path)
        self.assertEqual(data["attempt_token"], new_token,
                         "the superseded worker cleared the current reservation")
        self.assertEqual(data["phase"], "connecting")

    def test_a_release_cannot_cancel_an_attempt_a_worker_already_took(self):
        network = FakeNetwork()
        onboarder = self.onboarder(network)
        onboarder.start_hotspot()
        _, token = onboarder.admit("HomeWiFi")
        self.assertIsNotNone(onboarder._claim("HomeWiFi", token))
        with self.assertLogs(onboarding.LOGGER, level="WARNING"):
            onboarder.release(token)
        self.assertEqual(state_module.read(self.state_path)["phase"], "connecting")


class JournalBoundaryTests(Temp):
    """The journal is not a place for an exception's own text."""

    def test_a_capture_failure_logs_a_sentence_not_the_error_text(self):
        failure = PermissionError(13, "denied", "/synthetic/SYNTHETIC-SECRET-R3")
        network = FakeNetwork()
        network.joined = "HomeWiFi"
        onboarder = self.onboarder(network)
        data = state_module.blank("debra-demo1")
        data.update(phase="online", ssid="HomeWiFi", address="192.0.2.40")
        state_module.write(self.state_path, data)
        with patch.object(baseline_module, "capture", side_effect=failure):
            with self.assertLogs(onboarding.LOGGER, level="WARNING") as logs:
                status = onboarder.resume()
        text = "\n".join(logs.output)
        self.assertNotIn("SYNTHETIC-SECRET-R3", text, "the journal carried the path")
        self.assertIn("could not be read", text)
        self.assertEqual(status["baseline_error"], "Some device files could not be read")


class ScanSpaceTests(unittest.TestCase):
    """A name's leading and trailing spaces are part of the name."""

    def test_a_scan_does_not_trim_a_network_name(self):
        # `nmcli -t` separates fields with `:` and escapes a literal colon as
        # `\:`. The name is the first field, and its spaces are part of it.
        out = " Home :70:WPA2\nOther:40:WPA2\n"
        adapter = nm_module.Nmcli(runner=lambda argv, timeout=None: out)
        found = adapter.scan("wlan0")
        names = [item["ssid"] for item in found]
        self.assertIn(" Home ", names, f"the scan trimmed the name: {names}")


class SetupPasswordLifetimeTests(Temp):
    """The setup password has to survive a retry and a reboot.

    It used to be regenerated on every raise. Reading it off the card needs a
    reboot, which raised the access point again and invalidated the password
    just read; and one wrong household password replaced the credential the
    phone had saved for the setup network.
    """

    def test_a_wrong_household_password_keeps_the_setup_password(self):
        network = FakeNetwork(behaviour="bad-psk")
        clock = [0.0]
        note = self.dir / "boot" / "debra-setup.txt"
        onboarder = self.onboarder(network, clock=lambda: clock[0], card_note_path=note)
        first = onboarder.start_hotspot()["hotspot"]["password"]
        clock[0] += onboarding.SUBMIT_INTERVAL_S + 1
        status = onboarder.join("HomeWiFi", "wrong password", None)
        self.assertEqual(status["phase"], "failed")
        self.assertEqual(status["hotspot"]["password"], first,
                         "the recovery access point changed its password")
        self.assertEqual(network.hotspot["password"], first,
                         "the radio was given a different password")
        self.assertIn(first, note.read_text(encoding="utf-8"),
                      "the note no longer names the password the access point uses")

    def test_a_reboot_keeps_the_setup_password(self):
        note = self.dir / "boot" / "debra-setup.txt"
        first = self.onboarder(FakeNetwork(), card_note_path=note).start_hotspot()
        password = first["hotspot"]["password"]
        # A card-reader reboot: a new process, a new radio, the same disk.
        network = FakeNetwork()
        status = self.onboarder(network, card_note_path=note).resume()
        self.assertEqual(status["hotspot"]["password"], password)
        self.assertEqual(network.hotspot["password"], password)
        self.assertIn(password, note.read_text(encoding="utf-8"))

    def test_the_password_is_recorded_before_the_access_point_is_raised(self):
        # The old order raised first: a state write that failed left a live
        # access point that no state described and no note named.
        network = FakeNetwork()
        onboarder = self.onboarder(network)
        seen = []
        real = network.start_hotspot

        def watching(name, interface, password):
            seen.append(state_module.read(self.state_path)["hotspot_password"])
            return real(name, interface, password)

        network.start_hotspot = watching
        onboarder.start_hotspot()
        self.assertEqual(seen, [state_module.read(self.state_path)["hotspot_password"]],
                         "the access point was raised before its password was recorded")

    def test_a_failed_state_write_raises_nothing_to_take_down(self):
        network = FakeNetwork()
        state_module.write(self.state_path, dict(state_module.blank("debra-demo1")))

        def full_disk(path, data):
            raise OSError(28, "No space left on device")

        with patch.object(state_module, "write", full_disk):
            with self.assertRaises(OSError):
                self.onboarder(network).start_hotspot()
        self.assertIsNone(network.hotspot,
                          "an access point was raised with nothing recording it")
        self.assertNotIn("start_hotspot", network.phases())

    def test_a_failed_note_does_not_take_the_access_point_down(self):
        # A write to the boot partition is not the network. If it fails, the
        # person can still use the page; the radio must stay up.
        blocker = self.dir / "boot"
        blocker.write_text("not a directory", encoding="utf-8")
        network = FakeNetwork()
        status = self.onboarder(network, card_note_path=blocker / "note.txt").start_hotspot()
        self.assertIsNotNone(network.hotspot,
                             "the access point was taken down because of the note")
        self.assertEqual(status["phase"], "hotspot")
        self.assertEqual(status["hotspot"]["password"], network.hotspot["password"])

    def test_two_devices_do_not_share_a_setup_password(self):
        # A fixed same-length password passed a test that only looked at the
        # random helper, not at the value the production path stores.
        self.onboarder().start_hotspot()
        first = state_module.read(self.state_path)["hotspot_password"]
        self.state_path.unlink()
        self.onboarder().start_hotspot()
        second = state_module.read(self.state_path)["hotspot_password"]
        self.assertNotEqual(first, second, "a fixed password was used for every device")
        self.assertTrue(set(first) <= set(onboarding.HOTSPOT_ALPHABET))


class DeadAttemptTests(Temp):
    """A claim belongs to a process, and a reboot is a new process."""

    def claimed(self, onboarder, ssid="HomeWiFi"):
        onboarder.start_hotspot()
        accepted, token = onboarder.admit(ssid)
        self.assertTrue(accepted)
        self.assertIsNotNone(onboarder._claim(ssid, token))
        stored = state_module.read(self.state_path)
        self.assertTrue(stored["attempt_claimed"])
        return token

    def test_a_claimed_attempt_does_not_survive_a_boot(self):
        self.claimed(self.onboarder(FakeNetwork()))
        # The worker's process is gone: a new onboarder over the same disk.
        network = FakeNetwork()
        status = self.onboarder(network).resume()
        stored = state_module.read(self.state_path)
        self.assertFalse(stored["attempt_claimed"], "a dead claim survived the boot")
        self.assertIsNone(stored["attempt_token"])
        self.assertEqual(status["phase"], "failed")
        self.assertIn("did not finish", status["last_error"])
        # And a person can try again without repairing state by hand.
        second = self.onboarder(network, clock=lambda: 1000.0)
        accepted, token = second.admit("HomeWiFi")
        self.assertTrue(accepted, "the device stayed busy after a reboot")
        self.assertEqual(
            second.join_reserved("HomeWiFi", "correct horse", None, token)["phase"], "online")

    def test_an_unexpected_worker_failure_releases_the_attempt(self):
        network = FakeNetwork()
        # A real clock is `time.monotonic`, which is never near zero; the
        # throttle compares against `_last_submit`, so a fake clock starting at
        # zero would look like a submission that had just happened.
        clock = [1000.0]
        onboarder = self.onboarder(network, clock=lambda: clock[0])
        onboarder.start_hotspot()
        accepted, token = onboarder.admit("HomeWiFi")
        self.assertTrue(accepted)

        def boom(ssid, psk, **kwargs):
            raise RuntimeError("an unclassified failure in /etc/NetworkManager/x")

        network.connect = boom
        with self.assertLogs("onboarding", level="WARNING") as logs:
            status = onboarder.join_reserved("HomeWiFi", "correct horse", None, token)
        stored = state_module.read(self.state_path)
        self.assertFalse(stored["attempt_claimed"], "the worker left its claim behind")
        self.assertNotEqual(stored["phase"], "connecting")
        self.assertEqual(status["phase"], "failed")
        self.assertNotIn("/etc/NetworkManager", " ".join(logs.output),
                         "the worker log carried a path")
        del network.connect
        clock[0] += onboarding.SUBMIT_INTERVAL_S + 1
        accepted, _ = onboarder.admit("HomeWiFi")
        self.assertTrue(accepted, "the device stayed busy after the worker failed")

    def test_a_state_write_failure_does_not_leave_the_device_busy(self):
        network = FakeNetwork()
        onboarder = self.onboarder(network, clock=lambda: 1000.0)
        onboarder.start_hotspot()
        accepted, token = onboarder.admit("HomeWiFi")
        real_write = state_module.write

        def failing(path, data):
            if data.get("phase") == "online":
                raise OSError(28, "No space left on device")
            return real_write(path, data)

        with patch.object(state_module, "write", failing):
            status = onboarder.join_reserved("HomeWiFi", "correct horse", None, token)
        stored = state_module.read(self.state_path)
        self.assertFalse(stored["attempt_claimed"])
        self.assertEqual(stored["phase"], "failed")
        self.assertNotEqual(status["phase"], "connecting")


class FailureRearmTests(Temp):
    """The failure rearm owns the admission lock until the AP is back."""

    def test_a_new_attempt_cannot_be_admitted_against_a_missing_access_point(self):
        gate = threading.Event()
        entered = threading.Event()
        network = FakeNetwork(behaviour="bad-psk")
        clock = [1000.0]
        onboarder = self.onboarder(network, clock=lambda: clock[0])
        onboarder.start_hotspot()

        real_start = network.start_hotspot
        calls = []

        def gated_start(name, interface, password=None):
            calls.append(name)
            # The first call here is the failure's recovery raise: the initial
            # access point was raised before this patch was installed.
            if len(calls) == 1:
                entered.set()
                gate.wait(5)
            return real_start(name, interface, password)

        network.start_hotspot = gated_start
        accepted, token = onboarder.admit("HomeWiFi")
        self.assertTrue(accepted)
        worker = threading.Thread(target=onboarder.join_reserved,
                                  args=("HomeWiFi", "wrong password", None, token))
        worker.start()
        self.assertTrue(entered.wait(5), "the failure rearm never raised the access point")

        # While the rearm is paused, a new request must not be admitted: it
        # would see a device whose access point is still down.
        clock[0] += onboarding.SUBMIT_INTERVAL_S + 1
        admitted = []
        newcomer = threading.Thread(target=lambda: admitted.append(onboarder.admit("Other")))
        newcomer.start()
        newcomer.join(timeout=0.5)
        self.assertTrue(newcomer.is_alive(),
                        "a new attempt was admitted while the access point was down")
        self.assertEqual(admitted, [])

        network.behaviour = "ok"
        gate.set()
        worker.join(timeout=5)
        newcomer.join(timeout=5)
        self.assertFalse(newcomer.is_alive())
        self.assertTrue(admitted and admitted[0][0], "the retry after the rearm was refused")
        # The newer attempt wins. The old worker's rearm must not overwrite it.
        status = onboarder.join_reserved("Other", "correct horse", None, admitted[0][1])
        self.assertEqual(status["phase"], "online")
        self.assertEqual(status["ssid"], "Other")


class BaselineValidationTests(Temp):
    """A hash proves correspondence to metadata, not that it is a baseline."""

    def test_unrelated_matching_bytes_are_not_adopted(self):
        self.baseline_dir.mkdir()
        outside = self.dir / "not-a-baseline.bin"
        outside.write_bytes(b"an ordinary file")
        digest = hashlib.sha256(outside.read_bytes()).hexdigest()
        (self.baseline_dir / "baseline-unrelated.json").write_text(
            json.dumps({"archive": str(outside), "sha256": digest}))
        self.assertIsNone(baseline_module.latest(self.baseline_dir),
                          "an arbitrary file was reported as a baseline")
        self.assertIsNone(baseline_module.verified(self.baseline_dir, outside))

    def test_a_manifest_pointing_outside_the_directory_is_refused(self):
        self.baseline_dir.mkdir()
        outside = self.dir / "elsewhere.tar.gz"
        outside.write_bytes(b"x")
        (self.baseline_dir / "baseline-x.json").write_text(json.dumps({
            "archive": "../elsewhere.tar.gz", "created": "S",
            "sha256": hashlib.sha256(b"x").hexdigest(), "bytes": 1,
            "captured": [], "skipped": [], "missing": [], "note": "x"}))
        self.assertIsNone(baseline_module.latest(self.baseline_dir))

    def test_a_real_capture_validates(self):
        manifest = baseline_module.capture(self.baseline_dir, root=str(self.dir / "empty"),
                                           stamp="S")
        self.assertEqual(baseline_module.latest(self.baseline_dir)["archive"],
                         manifest["archive"])
        self.assertIsNotNone(
            baseline_module.verified(self.baseline_dir,
                                     self.baseline_dir / manifest["archive"]))

    def test_a_manifest_whose_inventory_the_archive_does_not_hold_is_refused(self):
        root = self.dir / "root"
        (root / "etc").mkdir(parents=True)
        (root / "etc" / "hostname").write_text("debra-1\n", encoding="utf-8")
        manifest = baseline_module.capture(self.baseline_dir, root=str(root), stamp="S")
        path = self.baseline_dir / (manifest["archive"][:-len(".tar.gz")] + ".json")
        data = json.loads(path.read_text())
        data["captured"] = ["etc/not-there"]
        path.write_text(json.dumps(data))
        self.assertIsNone(baseline_module.latest(self.baseline_dir))

    def test_a_manifest_whose_archive_is_not_a_tar_is_refused(self):
        self.baseline_dir.mkdir()
        archive = self.baseline_dir / "baseline-fake.tar.gz"
        archive.write_bytes(b"not a tarball")
        (self.baseline_dir / "baseline-fake.json").write_text(json.dumps({
            "archive": archive.name, "created": "S",
            "sha256": hashlib.sha256(archive.read_bytes()).hexdigest(),
            "bytes": archive.stat().st_size, "captured": [], "skipped": [],
            "missing": [], "note": "x"}))
        self.assertIsNone(baseline_module.latest(self.baseline_dir))


class BaselineRecordingFailureTests(Temp):
    def test_a_capture_that_cannot_be_recorded_is_reported_in_the_state(self):
        # The pointer write failed but the error write could succeed. The state
        # must say so: a silent gap reads as progress that is not happening.
        onboarder = self.onboarder(FakeNetwork())
        real_write = state_module.write

        def failing(path, data):
            if data.get("baseline"):
                raise OSError(28, "No space left on device")
            return real_write(path, data)

        with patch.object(state_module, "write", failing):
            onboarder._capture_baseline()
        stored = state_module.read(self.state_path)
        self.assertIsNone(stored["baseline"])
        self.assertEqual(stored["baseline_error"], "The device is out of disk space")
        self.assertEqual(onboarder.status()["baseline_error"],
                         "The device is out of disk space")

    def test_a_pointer_that_cannot_be_written_does_not_capture_again(self):
        # A complete capture with no pointer is adopted, not re-captured:
        # capturing again adds another archive on a store refusing writes.
        root = self.dir / "root"
        (root / "etc").mkdir(parents=True)
        (root / "etc" / "hostname").write_text("debra-1\n", encoding="utf-8")
        baseline_module.capture(self.baseline_dir, root=str(root), stamp="S1")
        self.assertEqual(len(list(self.baseline_dir.glob("baseline-*.tar.gz"))), 1)
        onboarder = self.onboarder(FakeNetwork(), root=str(root))
        real_write = state_module.write

        def failing(path, data):
            if data.get("baseline"):
                raise OSError(28, "No space left on device")
            return real_write(path, data)

        with patch.object(state_module, "write", failing):
            onboarder._capture_baseline()
        self.assertEqual(len(list(self.baseline_dir.glob("baseline-*.tar.gz"))), 1,
                         "a second baseline was captured on a store refusing writes")
        self.assertEqual(onboarder.status()["baseline_error"],
                         "The device is out of disk space")

    def test_the_running_page_is_told_even_when_no_state_write_succeeds(self):
        # The file cannot record the failure, so the running page must.
        onboarder = self.onboarder(FakeNetwork())

        def failing(path, data):
            raise OSError(28, "No space left on device")

        with patch.object(state_module, "write", failing):
            onboarder._capture_baseline()
        self.assertEqual(onboarder.status()["baseline_error"],
                         "The device is out of disk space")


class CaptureCoherenceTests(Temp):
    def test_a_same_size_rewrite_during_the_read_is_skipped(self):
        root = self.dir / "race-root"
        (root / "etc").mkdir(parents=True)
        path = root / "etc" / "hostname"
        path.write_bytes(b"A" * (2 << 20))
        real_open = open
        state = {"done": False}

        class Rewriting:
            def __init__(self, target):
                self._file = real_open(target, "rb")

            def fileno(self):
                return self._file.fileno()

            def read(self, size=-1):
                data = self._file.read(size)
                if not state["done"]:
                    state["done"] = True
                    # Same size, different bytes: a length check cannot see it,
                    # so a torn AA/BA mixture was recorded and called verified.
                    with real_open(target_path, "wb") as stream:
                        stream.write(b"B" * (2 << 20))
                return data

            def __enter__(self):
                return self

            def __exit__(self, *args):
                self._file.close()

        target_path = path

        def fake_open(target, *args, **kwargs):
            if str(target).endswith("etc/hostname"):
                return Rewriting(target)
            return real_open(target, *args, **kwargs)

        with patch("builtins.open", fake_open):
            manifest = baseline_module.capture(self.baseline_dir, root=str(root), stamp="S")
        self.assertNotIn("etc/hostname", manifest["captured"],
                         "a file rewritten under the read was recorded as whole")
        reasons = {item["path"]: item["reason"] for item in manifest["skipped"]}
        self.assertEqual(reasons.get("etc/hostname"), "changed while being read")


class SsidLimitTests(unittest.TestCase):
    def test_exactly_32_octets_is_a_valid_name(self):
        self.assertTrue(nm_module.valid_ssid("x" * 32))
        self.assertFalse(nm_module.valid_ssid("x" * 33))
        # The limit is octets, not characters.
        self.assertTrue(nm_module.valid_ssid("\u00e9" * 16))
        self.assertFalse(nm_module.valid_ssid("\u00e9" * 17))


class ClaimLockTests(Temp):
    """Taking ownership is one atomic read-modify-write.

    Checking the token and then setting the marker is not ownership: two workers
    holding the same valid token both passed the check and both joined. The lock
    around the claim is what makes the second one lose, and nothing forced the
    two reads to overlap before.
    """

    def test_only_one_worker_can_claim_when_the_state_read_is_slow(self):
        onboarder = self.onboarder(clock=lambda: 1000.0)
        onboarder.start_hotspot()
        accepted, token = onboarder.admit("HomeWiFi")
        self.assertTrue(accepted)
        real_read = state_module.read
        second_read = threading.Event()
        seen = []

        def slow_read(path):
            data = real_read(path)
            if not threading.current_thread().name.startswith("claimer"):
                return data
            seen.append(data["attempt_claimed"])
            if len(seen) == 1:
                # Hold the first claimer inside its read-modify-write for
                # longer than the second needs to arrive. Without the lock the
                # second reads the stale record and both claim the attempt.
                second_read.wait(0.5)
            else:
                second_read.set()
            return data

        results = []

        def claim():
            results.append(onboarder._claim("HomeWiFi", token))

        with patch.object(state_module, "read", slow_read):
            threads = [threading.Thread(target=claim, name=f"claimer-{index}")
                       for index in range(2)]
            for thread in threads:
                thread.start()
            for thread in threads:
                thread.join(timeout=10)
        self.assertEqual(len(results), 2)
        claimed = [result for result in results if result is not None]
        self.assertEqual(len(claimed), 1,
                         "two workers took the same reservation: %d claims" % len(claimed))


class BaselineDurabilityTests(Temp):
    def test_the_new_names_are_made_durable_not_only_the_bytes(self):
        # A capture that is fsynced but whose names are not can still lose both
        # files after a power cut, leaving a manifest that points at nothing.
        self.baseline_dir.mkdir()
        synced = []
        real_fsync = os.fsync

        def watching(fd):
            try:
                info = os.fstat(fd)
                synced.append(stat.S_ISDIR(info.st_mode))
            except OSError:
                pass
            return real_fsync(fd)

        with patch.object(os, "fsync", watching):
            baseline_module.capture(self.baseline_dir, root=str(self.dir / "empty"),
                                    stamp="S")
        self.assertIn(True, synced, "the baseline directory itself was never fsynced")


class RearmWindowTests(Temp):
    """No request may be admitted between the failure and the raised AP.

    The r4 repair settled the failure and then re-raised the access point while
    still holding the admission lock. Pausing inside the raise cannot see that
    window, because the raise is already inside the lock: the old order released
    ownership first, so the gap is between the settlement write and the raise.
    """

    def test_nothing_is_admitted_between_the_failure_and_the_rearm(self):
        network = FakeNetwork(behaviour="bad-psk")
        clock = [1000.0]
        onboarder = self.onboarder(network, clock=lambda: clock[0])
        onboarder.start_hotspot()
        real_write = state_module.write
        entered = threading.Event()
        release = threading.Event()
        gated = []

        def gated_write(path, data):
            if (not gated and data.get("phase") == "failed"
                    and not data.get("attempt_token")):
                # This is the settlement inside `_fail`. Hold the worker here.
                gated.append(True)
                entered.set()
                release.wait(5)
            return real_write(path, data)

        with patch.object(state_module, "write", gated_write):
            accepted, token = onboarder.admit("HomeWiFi")
            self.assertTrue(accepted)
            worker = threading.Thread(target=onboarder.join_reserved,
                                      args=("HomeWiFi", "wrong password", None, token))
            worker.start()
            self.assertTrue(entered.wait(5), "the failure was never recorded")

            clock[0] += onboarding.SUBMIT_INTERVAL_S + 1
            admitted = []
            newcomer = threading.Thread(target=lambda: admitted.append(onboarder.admit("Other")))
            newcomer.start()
            newcomer.join(timeout=0.5)
            self.assertTrue(
                newcomer.is_alive(),
                "a new attempt was admitted while the access point was still down")
            self.assertEqual(admitted, [])

            release.set()
            worker.join(timeout=5)
            newcomer.join(timeout=5)
        self.assertFalse(worker.is_alive())
        self.assertFalse(newcomer.is_alive())
        self.assertTrue(admitted and admitted[0][0], "the retry after the rearm was refused")
        self.assertEqual(onboarder.status()["phase"], "connecting")


class SupersededFailureTests(Temp):
    """A worker that lost its reservation must not record its own failure.

    The settlement already re-checks the token; the failure path reached the
    same state through `start_hotspot()`, which wrote a full record. A worker
    superseded while failing wiped the newer attempt's token, published its own
    stale reason and raised the access point over it.
    """

    def test_a_superseded_worker_cannot_record_its_failure(self):
        network = FakeNetwork(behaviour="bad-psk")
        clock = [1000.0]
        onboarder = self.onboarder(network, clock=lambda: clock[0])
        onboarder.start_hotspot()
        accepted, first = onboarder.admit("HomeWiFi")
        self.assertTrue(accepted)
        # The phone never got the reply, so it retried with a different name.
        # That is the production path to a superseded worker.
        onboarder.release(first)
        clock[0] += onboarding.SUBMIT_INTERVAL_S + 1
        accepted, second = onboarder.admit("Other")
        self.assertTrue(accepted)
        raises = len([call for call in network.calls if call[0] == "start_hotspot"])

        status = onboarder._fail(first, "The Wi-Fi password was refused by the network")

        stored = state_module.read(self.state_path)
        self.assertEqual(stored["phase"], "connecting",
                         "a superseded worker ended the newer attempt")
        self.assertEqual(stored["attempt_token"], second,
                         "a superseded worker cleared the newer attempt's token")
        self.assertEqual(stored["ssid"], "Other")
        self.assertIsNone(stored["last_error"],
                          "a superseded worker published its own stale reason")
        self.assertEqual(len([call for call in network.calls
                              if call[0] == "start_hotspot"]), raises,
                         "a superseded worker raised the access point over the newer attempt")
        self.assertEqual(status["phase"], "connecting")


class HandlerBoundaryTests(Temp):
    """The request handler is a boundary too, not only the join worker."""

    def test_a_state_write_failure_answers_the_phone_instead_of_tracebacking(self):
        # `admit()` writes the state. A full disk there raised inside
        # BaseHTTPRequestHandler: socketserver printed the traceback, with the
        # state path in it, to the journal, and the phone got no reply at all.
        network = FakeNetwork()
        onboarder = self.onboarder(network, clock=lambda: 1000.0)
        onboarder.start_hotspot()
        server = onboarding.Portal(("127.0.0.1", 0), onboarder,
                                   onboarding.ASSETS / "setup.html")
        host = "127.0.0.1:%d" % server.server_port
        server.host = host
        thread = threading.Thread(target=server.serve_forever, daemon=True)
        thread.start()
        stderr = io.StringIO()
        real_write = state_module.write

        def full_disk(path, data):
            raise OSError(28, "No space left on device: " + str(self.state_path))

        request = urllib.request.Request(
            "http://" + host + "/api/join",
            data=json.dumps({"ssid": "HomeWiFi", "psk": "correct horse"}).encode(),
            method="POST")
        request.add_header("Host", host)
        request.add_header("Content-Type", "application/json")
        try:
            with patch.object(state_module, "write", full_disk), \
                    redirect_stderr(stderr):
                try:
                    with urllib.request.urlopen(request, timeout=10) as response:
                        code, body = response.status, response.read()
                except urllib.error.HTTPError as exc:
                    code, body = exc.code, exc.read()
        finally:
            server.shutdown()
            thread.join()
            server.server_close()
        self.assertEqual(code, 500)
        self.assertIn(b"could not handle the request", body)
        self.assertNotIn(str(self.state_path), stderr.getvalue(),
                         "the journal received the state path")
        self.assertNotIn("Traceback", stderr.getvalue(),
                         "socketserver printed a traceback for a handled failure")
        self.assertEqual(state_module.read(self.state_path)["phase"], "hotspot")

    def portal(self):
        """A real portal on a loopback port, stopped by this test."""
        onboarder = self.onboarder(FakeNetwork(), clock=lambda: 1000.0)
        onboarder.start_hotspot()
        server = onboarding.Portal(("127.0.0.1", 0), onboarder,
                                   onboarding.ASSETS / "setup.html")
        host = "127.0.0.1:%d" % server.server_port
        server.host = host
        thread = threading.Thread(target=server.serve_forever, daemon=True)
        thread.start()

        def stop():
            server.shutdown()
            thread.join()
            server.server_close()

        self.addCleanup(stop)
        return server, onboarder, host

    @staticmethod
    def raw(server, request):
        """One request on a fresh connection, read until the server closes."""
        with socket.create_connection(("127.0.0.1", server.server_port),
                                      timeout=10) as connection:
            connection.sendall(request)
            chunks = []
            while True:
                chunk = connection.recv(4096)
                if not chunk:
                    return b"".join(chunks)
                chunks.append(chunk)

    @staticmethod
    def join_request(host, ssid="HomeWiFi", psk="correct horse"):
        body = json.dumps({"ssid": ssid, "psk": psk}).encode()
        return (("POST /api/join HTTP/1.0\r\nHost: %s\r\n"
                 "Content-Type: application/json\r\n"
                 "Content-Length: %d\r\n\r\n" % (host, len(body))).encode() + body)

    def test_a_state_read_failure_answers_the_poll_instead_of_tracebacking(self):
        # `/api/status` is polled every fifteen seconds. The POST boundary did
        # not cover it, so a failing read escaped socketserver, printed the
        # state path to the journal and closed the connection with no reply.
        server, onboarder, host = self.portal()
        stderr = io.StringIO()
        request = urllib.request.Request("http://" + host + "/api/status")
        request.add_header("Host", host)
        failure = OSError(5, "Input/output error: " + str(self.state_path))
        with patch.object(onboarder, "status", side_effect=failure), \
                redirect_stderr(stderr):
            try:
                with urllib.request.urlopen(request, timeout=10) as response:
                    code, body = response.status, response.read()
            except urllib.error.HTTPError as exc:
                code, body = exc.code, exc.read()
        self.assertEqual(code, 500)
        self.assertIn(b"could not handle the request", body)
        self.assertNotIn(str(self.state_path), stderr.getvalue(),
                         "the journal received the state path")
        self.assertNotIn("Traceback", stderr.getvalue(),
                         "socketserver printed a traceback for a handled failure")

    def test_a_failure_after_the_reservation_gives_it_back(self):
        # `admit()` has already written `connecting` when `status()` is read for
        # the reply. An exception there answers 500; it must also release the
        # reservation, or every later submission is refused as busy until the
        # process restarts.
        server, onboarder, host = self.portal()
        with patch.object(onboarder, "status",
                          side_effect=OSError(5, "Input/output error")):
            raw = self.raw(server, self.join_request(host))
        self.assertIn(b"500", raw.split(b"\r\n", 1)[0], repr(raw[:500]))
        stored = state_module.read(self.state_path)
        self.assertEqual(stored["phase"], "hotspot",
                         "a failed handler left the device connecting")
        self.assertIsNone(stored["attempt_token"])

    def test_a_worker_that_cannot_start_answers_once_and_gives_the_reservation_back(self):
        # The 202 is already on the wire when the thread starts. If starting it
        # raises, the boundary must not put a second response on the same
        # connection, and the reservation must not be left behind.
        server, onboarder, host = self.portal()
        real_thread = threading.Thread

        class Worker:
            def start(self):
                raise RuntimeError("the worker could not start")

        def factory(*args, **kwargs):
            if kwargs.get("name") == "debra-onboarding":
                return Worker()
            return real_thread(*args, **kwargs)

        with patch.object(onboarding.threading, "Thread", factory):
            raw = self.raw(server, self.join_request(host))
        self.assertEqual(raw.count(b"HTTP/1."), 1,
                         "a second response went out on one connection: "
                         + repr(raw[:2000]))
        self.assertIn(b"202 Accepted", raw)
        stored = state_module.read(self.state_path)
        self.assertEqual(stored["phase"], "hotspot",
                         "a worker that never started left the attempt connecting")
        self.assertIsNone(stored["attempt_token"])


class PersistedBaselineFailureTests(Temp):
    """The recorded failure must outlive the process that saw it.

    The in-memory copy is what the running page shows. It is not what the next
    boot reads: without the persisted field the page says only "not captured
    yet" after a reboot, with no reason, and nothing retries visibly. There are
    two ways a baseline attempt fails - the capture itself, and recording a
    capture that succeeded - and each writes its own record, so each needs its
    own test. A write filter keyed on `baseline` only reached the second.
    """

    def test_the_next_process_sees_a_capture_failure(self):
        onboarder = self.onboarder(FakeNetwork())
        failure = OSError(28, "No space left on device")
        with patch.object(baseline_module, "capture", side_effect=failure):
            onboarder._capture_baseline()
        # The running page is told from memory, which is what hid the gap.
        self.assertEqual(onboarder.status()["baseline_error"],
                         "The device is out of disk space")
        # A later process has no memory of the failure, only the file.
        later = self.onboarder(FakeNetwork())
        self.assertEqual(later.status()["baseline_error"],
                         "The device is out of disk space",
                         "the recorded capture failure did not survive the process")

    def test_the_next_process_sees_a_pointer_write_failure(self):
        onboarder = self.onboarder(FakeNetwork())
        real_write = state_module.write

        def failing(path, data):
            if data.get("baseline"):
                raise OSError(28, "No space left on device")
            return real_write(path, data)

        with patch.object(state_module, "write", failing):
            onboarder._capture_baseline()
        self.assertEqual(onboarder.status()["baseline_error"],
                         "The device is out of disk space")
        # A later process has no memory of the failure, only the file.
        later = self.onboarder(FakeNetwork())
        self.assertEqual(later.status()["baseline_error"],
                         "The device is out of disk space",
                         "the recorded failure did not survive the process that saw it")

"""Onboarding: identity, the phase machine, the portal, and the baseline.

Every test here runs offline. The NetworkManager is a recorded double, so a pass
proves the decisions and the HTTP contract, not that a radio works.
"""

import json
import os
import stat
import sys
import tempfile
import threading
import unittest
import urllib.error
import urllib.request
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


def _glib_parse(text):
    key_file = GLib.KeyFile()
    key_file.load_from_data(text, len(text.encode("utf-8")), GLib.KeyFileFlags.NONE)
    return {"ssid": key_file.get_string("wifi", "ssid"),
            "psk": key_file.get_string("wifi-security", "psk")}


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
        data["phase"] = "hotspot"
        state_module.write(self.state_path, data)
        self.assertEqual(stat.S_IMODE(self.state_path.stat().st_mode), 0o600)
        self.assertEqual(state_module.read(self.state_path)["hostname"], "debra-345678")

    def test_unknown_keys_bad_phases_and_bad_values_are_refused(self):
        base = state_module.blank("debra-345678")
        for broken in (dict(base, extra=1), dict(base, phase="sleeping"),
                       dict(base, schema=2), dict(base, attempts=-1),
                       dict(base, country="GBR"), dict(base, hotspot={"ssid": "x"})):
            with self.assertRaises(ValueError, msg=str(broken)[:60]):
                state_module.validate(broken)

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

    def test_status_reports_the_phase_and_never_a_passphrase(self):
        code, body = self.request("/api/status")
        self.assertEqual(code, 200)
        data = json.loads(body)
        self.assertEqual(data["phase"], "hotspot")
        self.assertNotIn("psk", data)

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
    """The setup network has to be joinable by a person with no console."""

    def test_the_password_is_derived_so_it_can_be_printed_and_reread(self):
        first = onboarding.hotspot_password("debra-345678")
        self.assertEqual(first, onboarding.hotspot_password("debra-345678"))
        self.assertNotEqual(first, onboarding.hotspot_password("debra-876543"))
        self.assertGreaterEqual(len(first), 8)
        self.assertLessEqual(len(first), 63)

    def test_the_adapter_is_given_a_password_rather_than_left_to_invent_one(self):
        network = FakeNetwork()
        self.onboarder(network).start_hotspot()
        hotspot_calls = [call for call in network.calls if call[0] == "start_hotspot"]
        self.assertTrue(hotspot_calls[0][3], "start_hotspot was called without a password")

    def test_the_password_is_never_written_into_the_setup_state(self):
        onboarder = self.onboarder()
        onboarder.start_hotspot()
        stored = self.state_path.read_text(encoding="utf-8")
        password = onboarding.hotspot_password(onboarder.ensure_identity())
        self.assertNotIn(password, stored)
        self.assertNotIn("password", stored)

    def test_the_card_note_says_the_three_things_needed_before_any_page_loads(self):
        note = self.dir / "boot" / "debra-setup.txt"
        onboarder = self.onboarder(card_note_path=note)
        onboarder.start_hotspot()
        text = note.read_text(encoding="utf-8")
        self.assertIn("Debra-Setup-demo1", text)
        self.assertIn(onboarding.hotspot_password(onboarder.ensure_identity()), text)
        self.assertIn("http://", text)

    def test_a_missing_card_location_is_not_a_reason_to_fail_the_hotspot(self):
        note = self.dir / "boot" / "debra-setup.txt"
        note.parent.write_text("not a directory")  # occupies the parent path
        with self.assertLogs(onboarding.LOGGER, level="WARNING"):
            status = self.onboarder(card_note_path=note).start_hotspot()
        self.assertEqual(status["phase"], "hotspot")

    def test_the_note_is_reprinted_with_the_address_the_page_actually_bound(self):
        # The note is written when the access point comes up, before the socket
        # exists. If the page binds somewhere else, that is the address a person
        # has to type, and the earlier guess is a dead link.
        note = self.dir / "boot" / "debra-setup.txt"
        onboarder = self.onboarder(card_note_path=note)
        onboarder.start_hotspot()
        self.assertIn("http://10.42.0.1/", note.read_text(encoding="utf-8"))
        onboarder.announce_portal("192.168.50.1")
        text = note.read_text(encoding="utf-8")
        self.assertIn("http://192.168.50.1/", text)
        self.assertNotIn("10.42.0.1", text)
        self.assertEqual(onboarder.status()["portal"], "http://192.168.50.1/")

    def test_announcing_an_address_with_no_access_point_is_harmless(self):
        note = self.dir / "boot" / "debra-setup.txt"
        onboarder = self.onboarder(card_note_path=note)
        onboarder.announce_portal("192.168.50.1")
        self.assertFalse(note.exists(), "a note was written for a network that is not up")
        self.assertIsNone(onboarder.status()["portal"])


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
    def test_a_keyfile_value_round_trips_through_a_real_parser(self):
        # The previous escaping produced `Caf\; \#1`, which GLib rejects and
        # which is not what the user typed. Ask the real parser.
        for ssid, psk in (("Caf; #1", "pass;word#1"),
                          (" Home ", " space pass "),
                          ("back\\slash", "back\\slash1")):
            with self.subTest(ssid=ssid):
                directory = self.dir / ("rt-" + str(abs(hash(ssid))))
                directory.mkdir()
                recorder = Recorder()
                nm_module.Nmcli(runner=recorder).connect(ssid, psk, keyfile_dir=directory)
                text, _, _ = recorder.contents[0]
                got = _glib_parse(text)
                self.assertEqual(got["ssid"], ssid)
                self.assertEqual(got["psk"], psk)

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

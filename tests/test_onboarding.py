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


class Temp(unittest.TestCase):
    def setUp(self):
        self._temp = tempfile.TemporaryDirectory(prefix="onboard-", dir="/tmp/opencode")
        self.dir = Path(self._temp.name)
        self.state_path = self.dir / "setup.json"
        self.baseline_dir = self.dir / "baseline"

    def tearDown(self):
        self._temp.cleanup()

    def onboarder(self, network=None, **kwargs):
        # A fixed name and a serial path that cannot exist keep every test
        # independent of the machine it runs on.
        kwargs.setdefault("hostname", "debra-demo1")
        kwargs.setdefault("serial_paths", (str(self.dir / "no-serial"),))
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

    def test_identity_is_recorded_once_and_not_rewritten(self):
        serial = self.dir / "serial"
        serial.write_text("1000000012345678\n")
        network = FakeNetwork()
        onboarder = self.onboarder(network, serial_paths=(str(serial),))
        self.assertEqual(onboarder.ensure_identity(), "debra-345678")
        self.assertEqual(onboarder.ensure_identity(), "debra-345678")
        self.assertEqual(network.phases().count("set_hostname"), 1)
        self.assertEqual(state_module.read(self.state_path)["hostname"], "debra-345678")

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
        self.assertEqual(network.phases(),
                         ["set_hostname", "wifi_interface", "country", "start_hotspot"])

    def test_the_device_name_survives_the_first_hotspot(self):
        # The identity is set in the same record the hotspot then writes. When
        # the write used a record read before the name existed, it erased it.
        status = self.onboarder(FakeNetwork()).start_hotspot()
        self.assertEqual(status["hostname"], "debra-demo1")
        self.assertEqual(state_module.read(self.state_path)["hostname"], "debra-demo1")
        self.assertEqual(status["portal"], "http://debra-demo1.local/")

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
        self.assertIn("Secrets were required", status["last_error"])
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
        import tarfile as tarfile_module
        real_add = tarfile_module.TarFile.add

        def add(self, name, *args, **kwargs):
            if str(name).endswith("home.nmconnection"):
                raise PermissionError(13, "Permission denied")
            return real_add(self, name, *args, **kwargs)

        with patch.object(tarfile_module.TarFile, "add", add):
            manifest = baseline_module.capture(self.baseline_dir, root=str(root))
        self.assertIn("etc/hostname", manifest["captured"])
        self.assertEqual(manifest["skipped"][0]["path"], str(secret))
        self.assertEqual(manifest["skipped"][0]["reason"], "PermissionError")

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
    """A stand-in for `_run` that answers like nmcli and remembers argv."""

    def __init__(self, address="192.0.2.40", gateway="192.0.2.1", up_fails=False):
        self.calls, self.contents = [], []
        self.address, self.gateway, self.up_fails = address, gateway, up_fails

    def __call__(self, argv, timeout=45):
        self.calls.append(list(argv))
        if argv[1:] == ["-t", "-f", "DEVICE,TYPE,STATE", "device", "status"]:
            return "wlan0:wifi:connected\n"
        if argv[1:3] == ["-t", "-f"] and argv[4:6] == ["device", "show"]:
            return (f"IP4.ADDRESS[1]:{self.address}/24\n"
                    f"IP4.GATEWAY:{self.gateway}\n")
        if argv[1:3] == ["connection", "load"]:
            path = Path(argv[3])
            self.contents.append((path.read_text(encoding="utf-8"),
                                  stat.S_IMODE(path.stat().st_mode)))
            return ""
        if argv[1:4] == ["connection", "up", "id"]:
            if self.up_fails:
                raise nm_module.NmError("Secrets were required, but not provided.")
            return ""
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
        text, mode = recorder.contents[0]
        self.assertIn("psk=correct horse", text)
        self.assertEqual(mode, 0o600, "the staged profile must be owner-only")
        # The staged file is not left behind once NetworkManager has read it.
        self.assertEqual(list(self.dir.glob("*.nmconnection")), [])

    def test_a_keyfile_value_cannot_break_out_of_its_line(self):
        recorder = Recorder()
        nm_module.Nmcli(runner=recorder).connect("Caf; #1", "pass;word#1",
                                                 keyfile_dir=self.dir)
        text, _ = recorder.contents[0]
        self.assertIn("ssid=Caf\\; \\#1", text)
        self.assertIn("psk=pass\\;word\\#1", text)

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
        self.assertIn(["nmcli", "connection", "delete", "id",
                       recorder.calls[-1][4]], recorder.calls)

    def test_a_bad_password_length_is_refused_before_anything_runs(self):
        recorder = Recorder()
        with self.assertRaises(nm_module.NmError):
            nm_module.Nmcli(runner=recorder).connect("HomeWiFi", "short",
                                                     keyfile_dir=self.dir)
        self.assertEqual(recorder.calls, [])


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

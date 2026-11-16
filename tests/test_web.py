"""Offline web/installer checks. Commands and audio are fakes; HTTP is loopback."""

import http.client
from contextlib import contextmanager, redirect_stdout
import importlib.util
from io import StringIO
import json
import os
from pathlib import Path
import shutil
import socket
import subprocess
import sys
import tempfile
import threading
import time
import unittest
from unittest.mock import patch

from control.web import server as web
from control.web import discovery


ROOT = Path(__file__).resolve().parent.parent
SOURCE = ROOT / "control/web"
SINK = "alsa_output.test.stereo-fallback"
TOKEN = "test_" + "a" * 40

# The installer also runs directly on devices, where server.py is beside it.
spec = importlib.util.spec_from_file_location("web_install", SOURCE / "install.py")
installer = importlib.util.module_from_spec(spec)
with patch.dict(sys.modules, {"server": web}):
    spec.loader.exec_module(installer)


def payload_copy(home, changed=False):
    """A complete payload beside a fixture, optionally with different bytes.

    Only the five fixed files are copied, because that is all a release is. The
    changed copy gains one newline per file: enough for a different content
    address, and still valid Python, JavaScript, CSS and HTML.
    """
    payload = Path(home) / ("payload-changed" if changed else "payload")
    for name in installer.PAYLOAD:
        target = payload / name
        target.parent.mkdir(parents=True, exist_ok=True)
        data = (SOURCE / name).read_bytes()
        target.write_bytes(data + (b"\n" if changed else b""))
    return payload


class FakeCommands:
    def __init__(self):
        self.calls = []
        self.percent, self.muted, self.present = 36, False, True
        self.failed = None

    def __call__(self, argv, *, timeout=web.COMMAND_TIMEOUT):
        if not 0 < timeout <= web.COMMAND_TIMEOUT:
            raise AssertionError("Command timeout must fit the request budget")
        self.calls.append(argv)
        if self.failed and self.failed in argv:
            raise web.Unavailable("private raw command output")
        if argv[:4] == ["pactl", "--format=json", "list", "sinks"]:
            return json.dumps([{
                "name": SINK, "description": "<not markup>", "mute": self.muted,
                "volume": {"left": {"value_percent": f"{self.percent}%"},
                           "right": {"value_percent": f"{self.percent}%"}}
            }] if self.present else [])
        if argv[:2] == ["pactl", "set-sink-volume"]:
            self.percent = int(argv[3][:-1])
            return ""
        if argv[:2] == ["pactl", "set-sink-mute"]:
            self.muted = argv[3] == "1"
            return ""
        if argv[0] == "systemctl":
            return "\n\n".join(
                f"Id={unit}\nLoadState=loaded\nActiveState=active\nUnitFileState=enabled"
                for unit in argv if unit.endswith(".service")
            )
        if argv == ["vcgencmd", "get_throttled"]:
            return "throttled=0x10000"
        if argv == ["vcgencmd", "pmic_read_adc"]:
            return "EXT5V_V volt(24)=5.08700000V\nVDD_CORE_V volt(15)=0.812V"
        raise AssertionError(f"Unexpected command: {argv}")


class BackendTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory(prefix="web-", dir="/tmp/opencode")
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name)
        self.commands = FakeCommands()
        self.backend = web.Backend(SINK, {"speaker": "retained"}, self.commands, self.root)

    def put(self, path, text):
        target = self.root / path.lstrip("/")
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_text(text)

    def test_get_status_has_no_mutations(self):
        status = self.backend.status()
        self.assertEqual(status["audio"]["percent"], 36)
        self.assertFalse(status["audio"]["muted"])
        self.assertEqual(status["selected_hardware"]["speaker"], "retained")
        self.assertFalse(any("set-sink" in " ".join(call) for call in self.commands.calls))

    def test_volume_and_mute_are_separate_and_explicit(self):
        self.backend.change_audio("volume", {"percent": 0})
        self.assertIn(["pactl", "set-sink-volume", SINK, "0%"], self.commands.calls)
        self.assertFalse(self.commands.muted)
        self.backend.change_audio("mute", {"muted": True})
        self.assertEqual(self.commands.percent, 0)
        self.assertTrue(self.commands.muted)

    def test_reject_invalid_volume_types_ranges_and_fields(self):
        for payload in ({"percent": True}, {"percent": 0.5}, {"percent": "36"},
                        {"percent": -1}, {"percent": 101}, {}, {"percent": 36, "sink": "other"}):
            with self.subTest(payload=payload), self.assertRaises(ValueError):
                self.backend.change_audio("volume", payload)
        self.assertEqual(self.commands.calls, [])

    def test_reject_invalid_mute_and_action(self):
        for action, payload in (("mute", {"muted": 1}), ("mute", {"muted": "true"}),
                                ("mute", {"muted": False, "extra": 1}), ("restart", {})):
            with self.subTest(action=action, payload=payload), self.assertRaises(ValueError):
                self.backend.change_audio(action, payload)

    def test_sink_missing_never_falls_back_or_restarts(self):
        self.commands.present = False
        with self.assertRaises(web.Unavailable):
            self.backend.change_audio("volume", {"percent": 36})
        self.assertEqual(self.commands.calls, [["pactl", "--format=json", "list", "sinks"]])

    def test_a_two_mic_family_needs_a_number_boundary(self):
        # `2-mic` occurs inside `12-Mics`, so a twelve-microphone product was
        # reported as this two-microphone board.
        option = web.HAT_OPTIONS[0]
        for product, expected in (
                ("ReSpeaker 2-Mics Pi HAT", True),
                ("Seeed 2mic voice card", True),
                ("ReSpeaker 2 Mic Array", True),
                ("ReSpeaker 2-microphone HAT", True),
                ("ReSpeaker_2-Mics_Pi_HAT", True),
                ("ReSpeaker 12-Mics Pi HAT", False),
                ("ReSpeaker 22-mic array", False),
                ("ReSpeaker 4 Mic Array", False),
                ("Seeed unrelated sensor HAT", False)):
            with self.subTest(product=product):
                self.assertEqual(web.hat_family_match(product, option), expected)

    def test_a_vendor_word_must_stand_on_its_own(self):
        # A plain substring read `respeaker` inside `NotReSpeaker` and `seeed`
        # inside `Unseeeded`, so any string containing those letters was
        # reported as this family. A board name is a word, not a substring.
        option = web.HAT_OPTIONS[0]
        for product in ("NotReSpeaker unrelated 2-mic gadget",
                        "Unseeeded 2mic",
                        "Norespeaker 2-mic array"):
            with self.subTest(product=product):
                self.assertIs(web.hat_family_match(product, option), False)
        # An ALSA card id has no word boundaries. It is not an EEPROM product
        # string, and matching it would need a different rule with different
        # evidence; the card is reported separately, as a card.
        self.assertIs(web.hat_family_match("seeed2micvoicec", option), False)

    def test_the_alternative_is_not_asked_about_the_eeprom(self):
        # "No HAT" is an alternative, not a board the EEPROM can name. Reporting
        # "the EEPROM does not name a ReSpeaker board" in that row said the
        # opposite of the ReSpeaker row's evidence about the very same string.
        # The payload keeps its documented shape: `detected` is null, which is
        # the "nothing established" value it already had.
        self.put("/sys/firmware/devicetree/base/hat/product", "ReSpeaker 2-Mics Pi HAT\0")
        self.put("/proc/asound/cards", " 0 [seeed2micvoicec]: simple-card\n")
        respeaker, none = self.backend.setup()["hardware"]["options"]
        self.assertIs(respeaker["detected"], True)
        self.assertIsNone(none["detected"])
        self.assertEqual(set(none), {"id", "label", "summary", "detected", "card", "applied",
                                     "caveats"})
        self.assertIs(web.hat_family_match("ReSpeaker 2-Mics Pi HAT", web.HAT_OPTIONS[1]), None)

    def test_reject_implicit_sink_and_command_injection(self):
        for sink in ("@DEFAULT_SINK@", "", "-option", "test; touch foo", "has space", "a\nb"):
            with self.subTest(sink=sink), self.assertRaises(ValueError):
                web.Backend(sink, {})

    def test_malformed_audio_is_unavailable(self):
        for raw in ("bad json", "null", "{}", '[{"name": null}]',
                    json.dumps([{"name": SINK, "volume": {}, "mute": False}])):
            self.backend.runner = lambda argv, **kwargs: raw
            self.assertFalse(self.backend.audio()["available"])

    def test_audio_failure_is_sanitized(self):
        self.commands.failed = "pactl"
        status = self.backend.status()
        self.assertFalse(status["audio"]["available"])
        self.assertNotIn("private raw", json.dumps(status))

    def test_cache_still_reads_external_volume(self):
        self.backend.status()
        self.commands.percent, self.commands.muted = 19, True
        self.commands.calls.clear()
        status = self.backend.status()
        self.assertEqual(status["audio"]["percent"], 19)
        self.assertTrue(status["audio"]["muted"])
        self.assertEqual(len(self.commands.calls), 1)

    def test_components_are_not_end_to_end_health(self):
        components = self.backend.components()
        self.assertTrue(components[0]["unit_found"])
        self.assertEqual(components[0]["configuration"], "Not yet inspected")
        self.assertEqual(components[-2]["active"], "unknown")
        self.assertEqual(len(self.commands.calls), 2)

    def test_power_supply_is_not_cpu_core_voltage(self):
        power = self.backend.power()
        self.assertEqual(power["supply_voltage_v"], 5.087)
        self.assertFalse(power["undervoltage_now"])
        self.assertTrue(power["undervoltage_since_boot"])
        self.backend.runner = lambda argv, **kwargs: "VDD_CORE_V volt(15)=0.812V"
        self.assertIsNone(self.backend.power()["supply_voltage_v"])

    def test_missing_metrics_are_null(self):
        data, _ = web.metrics(self.root)
        self.assertIsNone(data["model"])
        self.assertIsNone(data["uptime_s"])
        self.assertIsNone(data["zswap_enabled"])
        self.assertIsNone(data["swap_io"]["pswpin_pages_per_s"])

    def test_cpu_uses_deltas_and_excludes_duplicate_guest_time(self):
        self.put("/proc/stat", "cpu 100 0 50 200 50 0 0 0 80 0\ncpu0 100 0 50 200 50 0 0 0 80 0")
        data, previous = web.metrics(self.root)
        self.assertIsNone(data["cpu_percent"]["cpu"])
        self.put("/proc/stat", "cpu 130 0 60 230 80 0 0 0 100 0\ncpu0 130 0 60 230 80 0 0 0 100 0")
        data, _ = web.metrics(self.root, previous, 2)
        self.assertEqual(data["cpu_percent"], {"cpu": 40.0, "cpu0": 40.0})

    def test_resources_and_swap_counters(self):
        self.put("/proc/meminfo", "MemTotal: 1000 kB\nMemAvailable: 400 kB\nbad: nope")
        self.put("/proc/vmstat", "pswpin 100\npswpout 200\n")
        self.put("/sys/block/zram0/mm_stat", "10000 5000 6000 0 0 0 0")
        self.put("/sys/module/zswap/parameters/enabled", "Y")
        self.put("/proc/uptime", "123.5 99")
        data, previous = web.metrics(self.root)
        self.put("/proc/vmstat", "pswpin 110\npswpout 220\n")
        data, _ = web.metrics(self.root, previous, 2)
        self.assertEqual(data["memory"]["MemAvailable"], 409600)
        self.assertEqual(data["zram"][0]["memory_bytes"], 6000)
        self.assertTrue(data["zswap_enabled"])
        self.assertEqual(data["uptime_s"], 123.5)
        self.assertEqual(data["swap_io"]["pswpout_pages_per_s"], 10)

    def test_malformed_and_nonfinite_metrics_do_not_break_status(self):
        self.put("/proc/uptime", "garbage")
        self.put("/sys/class/thermal/thermal_zone0/temp", "nan")
        self.put("/proc/net/wireless", "head\nhead\nwlan0: 0000 70. -42. -256\nwlan1: 0000 70. 212. -256")
        status = self.backend.status()
        self.assertIsNone(status["uptime_s"])
        self.assertIsNone(status["temperature_c"])
        self.assertEqual(status["wifi"][0]["signal_dbm"], -42)
        self.assertIsNone(status["wifi"][1]["signal_dbm"])
        json.dumps(status, allow_nan=False)

    def test_expired_queued_write_never_invokes_commands(self):
        started = time.monotonic()
        with self.backend.lock:
            with self.assertRaises(web.RequestExpired):
                self.backend.change_audio("volume", {"percent": 24}, deadline=started + 0.05)
        self.assertLess(time.monotonic() - started, 1)
        self.assertEqual(self.commands.calls, [])
        self.assertEqual(self.commands.percent, 36)

    def test_expiry_during_availability_probe_prevents_mutation(self):
        def slow_probe(argv, **kwargs):
            threading.Event().wait(0.05)
            return self.commands(argv, **kwargs)
        self.backend.runner = slow_probe
        with self.assertRaises(web.RequestExpired):
            self.backend.change_audio("volume", {"percent": 24}, deadline=time.monotonic() + 0.02)
        self.assertEqual(self.commands.calls, [["pactl", "--format=json", "list", "sinks"]])
        self.assertEqual(self.commands.percent, 36)

    def test_subprocess_timeout_uses_remaining_request_budget(self):
        with patch.object(web.subprocess, "run") as run:
            run.return_value.returncode = 0
            run.return_value.stdout = ""
            backend = web.Backend(SINK, {}, root=self.root)
            backend.command(["fixture"], deadline=time.monotonic() + 0.1)
        self.assertGreater(run.call_args.kwargs["timeout"], 0)
        self.assertLessEqual(run.call_args.kwargs["timeout"], 0.1)


class VersionTests(unittest.TestCase):
    """The page must be able to name the build it is running.

    A release directory is named by the digest of its payload, so that digest is
    the only version identifier that cannot drift: it is derived from the bytes,
    not assigned by hand. These tests keep the server's copy of the rule equal to
    the installer's, which is what makes a device page and an install report
    comparable.
    """

    def test_the_server_names_a_release_the_way_the_installer_does(self):
        with tempfile.TemporaryDirectory() as home:
            payload = payload_copy(home)
            expected = installer.payload_digest(
                {name: (payload / name).read_bytes() for name in installer.PAYLOAD})
            self.assertEqual(web.release_version(payload)["release"], expected)

    def test_the_installer_has_no_second_copy_of_the_rule(self):
        # One definition, imported. A private copy would keep working while the
        # two silently disagreed about what a release is.
        self.assertEqual(installer.PAYLOAD, web.PAYLOAD)
        self.assertIs(installer.payload_digest, web.payload_digest)

    def test_a_changed_payload_is_a_different_release(self):
        with tempfile.TemporaryDirectory() as home:
            before = web.release_version(payload_copy(home))
            after = web.release_version(payload_copy(home, changed=True))
        self.assertEqual(len(before["release"]), 64)
        self.assertEqual(before["short"], before["release"][:12])
        self.assertNotEqual(before["release"], after["release"])

    def test_an_unreadable_payload_is_reported_not_guessed(self):
        # A missing file must not yield a digest of the files that remain: that
        # would be a plausible-looking version for a broken install.
        with tempfile.TemporaryDirectory() as home:
            payload = payload_copy(home)
            (payload / "assets/app.js").unlink()
            version = web.release_version(payload)
        self.assertIsNone(version["release"])
        self.assertIsNone(version["short"])
        self.assertIn("unreadable", version["error"])

    def test_a_payload_file_is_part_of_the_identity(self):
        # Every file in the payload moves the digest; a file left out of the
        # list would let a real change keep the old version.
        with tempfile.TemporaryDirectory() as home:
            baseline = web.release_version(payload_copy(home))["release"]
            payload = payload_copy(home)
            for name in installer.PAYLOAD:
                with self.subTest(name):
                    target = payload / name
                    original = target.read_bytes()
                    target.write_bytes(original + b" ")
                    try:
                        self.assertNotEqual(web.release_version(payload)["release"], baseline)
                    finally:
                        target.write_bytes(original)


class HTTPTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.temp = tempfile.TemporaryDirectory(prefix="web-http-", dir="/tmp/opencode")
        cls.commands = FakeCommands()
        cls.backend = web.Backend(SINK, {}, cls.commands, Path(cls.temp.name))
        cls.server = web.Server(("127.0.0.1", 0), cls.backend, TOKEN, [])
        cls.host = f"127.0.0.1:{cls.server.server_port}"
        cls.server.hosts = frozenset([cls.host])
        cls.thread = threading.Thread(target=cls.server.serve_forever, daemon=True)
        cls.thread.start()

    @classmethod
    def tearDownClass(cls):
        cls.server.shutdown()
        cls.server.server_close()
        cls.thread.join()
        cls.temp.cleanup()

    def setUp(self):
        self.commands.calls.clear()
        self.commands.percent, self.commands.muted, self.commands.present = 36, False, True
        self.commands.failed = None

    def request(self, method="GET", path="/api/status", body=None, **headers):
        defaults = {"Host": self.host, "Authorization": "Bearer " + TOKEN}
        if method == "POST":
            defaults.update({"Origin": "http://" + self.host, "Content-Type": "application/json"})
        defaults.update(headers)
        # None means omit the header entirely, rather than sending an empty one.
        defaults = {name: value for name, value in defaults.items() if value is not None}
        connection = http.client.HTTPConnection("127.0.0.1", self.server.server_port, timeout=5)
        connection.request(method, path, body, defaults)
        response = connection.getresponse()
        data = response.read()
        result = response.status, dict(response.getheaders()), data
        connection.close()
        return result

    def test_authenticated_status_read_only(self):
        code, _, raw = self.request()
        self.assertEqual(code, 200)
        self.assertEqual(json.loads(raw)["audio"]["percent"], 36)
        self.assertFalse(any("set-sink" in " ".join(call) for call in self.commands.calls))

    def test_status_names_the_build_that_is_running(self):
        code, _, raw = self.request()
        self.assertEqual(code, 200)
        version = json.loads(raw)["version"]
        self.assertEqual(version["release"], web.release_version()["release"])
        self.assertEqual(version["short"], version["release"][:12])
        self.assertFalse(version["restart_required"])

    def test_a_file_changed_under_a_running_process_asks_for_a_restart(self):
        # The development host reads assets from disk on every request, so an
        # edit is served while the code that loaded it is old. Reporting only one
        # digest would present a half-updated build as a single version.
        running = self.server.version["release"]
        other = {"release": "0" * 64, "short": "0" * 12, "error": None}
        with patch.object(web, "release_version", return_value=other):
            code, _, raw = self.request()
        self.assertEqual(code, 200)
        version = json.loads(raw)["version"]
        self.assertEqual(version["release"], running)
        self.assertEqual(version["on_disk"], "0" * 64)
        self.assertTrue(version["restart_required"])

    def test_static_page_requires_no_key_and_has_security_headers(self):
        for path in ("/", "/app.js", "/style.css"):
            code, headers, body = self.request(path=path, Authorization="")
            self.assertEqual(code, 200)
            self.assertIn("frame-ancestors 'none'", headers["Content-Security-Policy"])
            self.assertEqual(headers["Cache-Control"], "no-store")
            self.assertEqual(headers["Referrer-Policy"], "no-referrer")
            self.assertNotIn(TOKEN.encode(), body)

    def test_missing_wrong_or_query_key_cannot_read_status(self):
        for auth in ("", "Bearer wrong"):
            self.assertEqual(self.request(Authorization=auth)[0], 401)
        self.assertEqual(self.request(path="/api/status?key=" + TOKEN, Authorization="")[0], 401)

    def test_audio_writes_require_key_before_any_command(self):
        for path, body in (("/api/audio/volume", '{"percent":20}'),
                           ("/api/audio/mute", '{"muted":true}')):
            for label, auth in (("missing", None), ("wrong", "Bearer wrong"),
                                ("empty bearer", "Bearer ")):
                with self.subTest(path=path, auth=label):
                    self.commands.calls.clear()
                    code, _, _ = self.request("POST", path, body, Authorization=auth)
                    # Check both together: even a 401 must not hide a command.
                    self.assertEqual((code, self.commands.calls), (401, []),
                                     f"{path} with {label} authorization")
            with self.subTest(path=path, auth="valid"):
                self.commands.calls.clear()
                self.assertEqual(self.request("POST", path, body)[0], 200)
                self.assertIn(["pactl", "set-sink-" + path.rsplit("/", 1)[1], SINK,
                               "20%" if path.endswith("volume") else "1"], self.commands.calls)

    def test_non_action_requests_never_control_services(self):
        commands = FakeCommands()
        forbidden = []
        user_units = [unit for _, unit, user in web.SERVICES if user]
        system_units = [unit for _, unit, user in web.SERVICES if not user]
        user_show = ["systemctl", "--user", "show", *user_units,
                     "--property=Id,LoadState,ActiveState,UnitFileState"]
        system_show = ["systemctl", "show", *system_units,
                       "--property=Id,LoadState,ActiveState,UnitFileState"]
        allowed = [["pactl", "--format=json", "list", "sinks"], user_show, system_show,
                   ["vcgencmd", "get_throttled"], ["vcgencmd", "pmic_read_adc"]]

        def runner(argv, *, timeout=web.COMMAND_TIMEOUT):
            if argv not in allowed:
                # HTTP handlers run in threads: record instead of raising there,
                # then fail in the test thread even if the handler swallows errors.
                forbidden.append(list(argv))
                return ""
            return commands(argv, timeout=timeout)

        browse = ["avahi-browse", "-rtp", "-t", "_debra._tcp"]
        subprocess_calls = []
        def subprocess_runner(argv, **kwargs):
            subprocess_calls.append(list(argv))
            if argv != browse:
                forbidden.append(list(argv))
            return subprocess.CompletedProcess(argv, 0, "", "")

        cache = web.DiscoveryCache()
        with patch.object(self.backend, "runner", runner), patch.object(self.backend, "cached", None), \
                patch.object(self.backend, "cache_time", None), \
                patch.object(self.server, "discovery", cache), \
                patch.object(web.subprocess, "run", side_effect=subprocess_runner):
            def check(label, method="GET", path="/api/status", body=None, expected=200):
                code, _, _ = self.request(method, path, body)
                self.assertEqual(forbidden, [], f"{label} ran a forbidden command")
                self.assertEqual(code, expected, label)

            for path in ("/", "/app.js", "/style.css"):
                check("page load", path=path)
            check("initial status")
            # Status genuinely probes services; only the two exact show commands
            # are allowed, not start/stop/restart or a changed systemctl invocation.
            self.assertEqual([call for call in commands.calls if call[0] == "systemctl"],
                             [user_show, system_show])
            # Keep this specifically on the cached path even under a slow host.
            self.backend.cache_time = time.monotonic() + 3600
            check("status poll")
            check("device list", path="/api/devices")
            cache.scan()
            self.assertEqual(forbidden, [], "discovery ran a forbidden command")
            self.assertEqual(subprocess_calls, [browse])
            check("discovered device list", path="/api/devices")
            # Reconnect has no server endpoint: it reloads and reads status again.
            check("reconnect page", path="/")
            self.backend.cached = None
            check("reconnect status")
            commands.present = False
            for path, body in (("/api/audio/volume", '{"percent":20}'),
                               ("/api/audio/mute", '{"muted":true}')):
                check("failed audio write", "POST", path, body, expected=503)
            self.assertEqual(subprocess_calls, [browse])

    def test_device_inventory_public_in_key_mode_but_status_protected(self):
        # Send no Authorization header at all, not an empty bearer value.
        connection = http.client.HTTPConnection("127.0.0.1", self.server.server_port, timeout=5)
        for path, expected in (("/api/devices", 200), ("/api/status", 401)):
            connection.request("GET", path, headers={"Host": self.host})
            response = connection.getresponse()
            raw = response.read()
            self.assertEqual(response.status, expected, f"{path} without a key")
            if path == "/api/devices":
                self.assertIn("devices", json.loads(raw))
        connection.close()
        self.assertEqual(self.commands.calls, [])

    def test_unrecognized_host_and_cross_site_rejected(self):
        for headers in ({"Host": "attacker.test:8787"}, {"Origin": "http://attacker.test"},
                        {"Sec-Fetch-Site": "cross-site"}):
            self.assertEqual(self.request(**headers)[0], 403)

    def test_a_cross_site_link_to_the_page_is_served(self):
        # A Switch link goes from another Debra's page to this one, so Chromium
        # marks it cross-site. Refusing it showed a JSON error instead of the
        # device. This is the exact header set the browser sends.
        navigation = {"Sec-Fetch-Site": "cross-site", "Sec-Fetch-Mode": "navigate",
                      "Sec-Fetch-Dest": "document"}
        code, headers, body = self.request(path="/", **navigation)
        self.assertEqual(code, 200)
        self.assertEqual(headers["Content-Type"], "text/html; charset=utf-8")
        self.assertIn(b"<html", body)

    def test_cross_site_is_still_refused_for_state_and_writes(self):
        navigation = {"Sec-Fetch-Site": "cross-site", "Sec-Fetch-Mode": "navigate",
                      "Sec-Fetch-Dest": "document"}
        # The navigation exemption is for the page, not for its data: a
        # cross-site GET of the status, a cross-site write, and a cross-site
        # subresource load are all still refused.
        self.assertEqual(self.request(path="/api/status", **navigation)[0], 403)
        self.assertEqual(self.request(path="/api/setup", **navigation)[0], 403)
        self.assertEqual(self.request("POST", "/api/audio/volume", '{"percent":10}',
                                      **navigation)[0], 403)
        for headers in ({"Sec-Fetch-Site": "cross-site"},
                        {"Sec-Fetch-Site": "cross-site", "Sec-Fetch-Mode": "cors",
                         "Sec-Fetch-Dest": "empty"},
                        {"Sec-Fetch-Site": "cross-site", "Sec-Fetch-Mode": "navigate",
                         "Sec-Fetch-Dest": "iframe"},
                        {"Sec-Fetch-Site": "cross-site", "Sec-Fetch-Mode": "navigate",
                         "Sec-Fetch-Dest": "document", "Origin": "http://other.test"}):
            with self.subTest(headers=headers):
                self.assertEqual(self.request(path="/", **headers)[0], 403)
        self.assertEqual(self.commands.calls, [])

    def test_writes_require_same_origin_even_with_key(self):
        for origin in ("", "null", "http://attacker.test"):
            self.assertEqual(self.request("POST", "/api/audio/volume", '{"percent":36}', Origin=origin)[0], 403)
        self.assertEqual(self.commands.calls, [])

    def test_write_only_fixed_audio_actions(self):
        code, _, raw = self.request("POST", "/api/audio/volume", '{"percent":0}')
        self.assertEqual(code, 200)
        self.assertEqual(json.loads(raw)["percent"], 0)
        self.assertEqual(self.request("POST", "/api/restart", "{}")[0], 404)
        self.assertEqual(self.request("GET", "/api/audio/volume")[0], 404)

    def test_invalid_requests_do_not_mutate(self):
        for body in ('{"percent":true}', '{"percent":101}', "[]", "{", "", "x" * 1025):
            with self.subTest(body=body[:40]):
                self.assertEqual(self.request("POST", "/api/audio/volume", body)[0], 400)
        self.assertEqual(self.request("POST", "/api/audio/mute", '{"muted":true}',
                                     **{"Content-Type": "text/plain"})[0], 400)
        self.assertFalse(any("set-sink" in " ".join(call) for call in self.commands.calls))

    def test_an_oversized_but_valid_json_body_is_refused_before_any_write(self):
        # The old oversized case was `"x" * 1025`, which is not JSON: it was
        # refused by the parser whether or not the size bound existed, so
        # deleting the bound left every test green. JSON permits trailing
        # whitespace, so this body is valid, has the one accepted key, and is
        # over the limit. Only the bound can refuse it.
        body = '{"percent": 36}' + " " * 1200
        self.assertGreater(len(body), 1024)
        code, _, raw = self.request("POST", "/api/audio/volume", body)
        self.assertEqual(code, 400)
        self.assertIn(b"Invalid audio request", raw)
        self.assertFalse(any("set-sink" in " ".join(call) for call in self.commands.calls),
                         "an oversized body reached the native volume command")

    def test_unavailable_write_is_sanitized_and_has_no_fallback(self):
        self.commands.present = False
        code, _, raw = self.request("POST", "/api/audio/mute", '{"muted":true}')
        self.assertEqual(code, 503)
        self.assertNotIn(b"private raw", raw)
        self.assertFalse(any("set-sink" in " ".join(call) for call in self.commands.calls))

    def test_path_traversal_and_query_do_not_serve_files(self):
        for path in ("/../server.py", "/%2e%2e/server.py", "/style.css?x=1", "/access.key"):
            self.assertEqual(self.request(path=path)[0], 404)

    def test_duplicate_and_ambiguous_headers_are_rejected(self):
        common = [f"Host: {self.host}", "Authorization: Bearer " + TOKEN,
                  f"Origin: http://{self.host}", "Content-Type: application/json"]
        cases = [(f"Host: {self.host}", 403), ("Authorization: Bearer " + TOKEN, 401),
                 (f"Origin: http://{self.host}", 403),
                 ("Content-Length: 2", 400), ("Transfer-Encoding: chunked", 400)]
        for extra, expected in cases:
            with self.subTest(extra=extra):
                request = "\r\n".join(["POST /api/audio/mute HTTP/1.1", *common,
                                       "Content-Length: 2", extra, "", "{}"])
                with socket.create_connection(self.server.server_address, timeout=5) as stream:
                    stream.sendall(request.encode())
                    response = stream.recv(4096)
                self.assertEqual(int(response.split()[1]), expected)

    def test_transfer_encoding_presence_and_strict_decimal_length(self):
        common = ["POST /api/audio/volume HTTP/1.1", f"Host: {self.host}",
                  "Authorization: Bearer " + TOKEN, f"Origin: http://{self.host}",
                  "Content-Type: application/json"]
        body = '{"percent":100}'
        cases = [
            ["Transfer-Encoding:", "Content-Length: 15"],
            ["Transfer-Encoding:", "Transfer-Encoding: chunked", "Content-Length: 15"],
            ["Content-Length: +15"], ["Content-Length: 1_5"],
            ["Content-Length: 15, 15"], ["Content-Length: -15"],
            ["Content-Length: 15", "Content-Length: 15"],
        ]
        for headers in cases:
            with self.subTest(headers=headers):
                request = "\r\n".join([*common, *headers, "", body])
                with socket.create_connection(self.server.server_address, timeout=5) as stream:
                    stream.sendall(request.encode())
                    response = stream.recv(4096)
                self.assertEqual(int(response.split()[1]), 400)
        self.assertEqual(self.commands.calls, [])
        self.assertEqual(self.commands.percent, 36)

    def test_slow_drip_headers_and_body_have_overall_deadline(self):
        original = self.server.request_timeout
        self.server.request_timeout = 0.3
        self.addCleanup(setattr, self.server, "request_timeout", original)
        for initial in (
                b"GET /api/status HTTP/1.1\r\nX-Slow: ",
                ("\r\n".join(["POST /api/audio/volume HTTP/1.1", f"Host: {self.host}",
                              "Authorization: Bearer " + TOKEN, f"Origin: http://{self.host}",
                              "Content-Type: application/json", "Content-Length: 1000",
                              "", ""])).encode()):
            with self.subTest(initial=initial[:30]):
                stop = threading.Event()
                with socket.create_connection(self.server.server_address, timeout=2) as stream:
                    stream.sendall(initial)
                    def drip():
                        while not stop.wait(0.04):
                            try:
                                stream.sendall(b"x")
                            except OSError:
                                break
                    sender = threading.Thread(target=drip, daemon=True)
                    started = time.monotonic()
                    sender.start()
                    try:
                        # Timeout shuts down the socket even while bytes arrive.
                        while stream.recv(4096):
                            pass
                    finally:
                        stop.set()
                        sender.join(timeout=1)
                    self.assertLess(time.monotonic() - started, 1.5)
                    self.assertGreaterEqual(time.monotonic() - started, 0.2)
        self.assertEqual(self.commands.calls, [])

    def test_http_write_waiting_for_backend_expires_without_late_mutation(self):
        original_timeout = self.server.request_timeout
        self.server.request_timeout = 0.3
        self.addCleanup(setattr, self.server, "request_timeout", original_timeout)
        finished = threading.Event()
        change_audio = self.backend.change_audio
        def observed(*args, **kwargs):
            try:
                return change_audio(*args, **kwargs)
            finally:
                finished.set()
        request = "\r\n".join([
            "POST /api/audio/volume HTTP/1.1", f"Host: {self.host}",
            "Authorization: Bearer " + TOKEN, f"Origin: http://{self.host}",
            "Content-Type: application/json", "Content-Length: 14", "", '{"percent":24}'])
        with patch.object(self.backend, "change_audio", side_effect=observed):
            with self.backend.lock:
                with socket.create_connection(self.server.server_address, timeout=2) as stream:
                    stream.sendall(request.encode())
                    while stream.recv(4096):
                        pass
                self.assertTrue(finished.wait(1), "Backend wait outlived the request deadline")
        self.assertEqual(self.commands.calls, [])
        self.assertEqual(self.commands.percent, 36)

    def test_invalid_server_key_rejected(self):
        for key in ("short", "x" * 129, "é" * 40, "x" * 40 + "\n"):
            with self.subTest(key=key), self.assertRaises(ValueError):
                web.Server(("127.0.0.1", 0), self.backend, key, [])

    def test_connection_worker_limit(self):
        class Stream:
            def settimeout(self, value):
                self.timeout = value
        # Isolate the semaphore from real requests whose connection has closed
        # but whose worker may still be returning through its finally block.
        with web.Server(("127.0.0.1", 0), None, TOKEN, []) as server:
            acquired = 0
            try:
                for _ in range(8):
                    self.assertTrue(server.verify_request(Stream(), ("127.0.0.1", 1)))
                    acquired += 1
                self.assertFalse(server.verify_request(Stream(), ("127.0.0.1", 1)))
            finally:
                for _ in range(acquired):
                    server.slots.release()


class NoAuthTests(unittest.TestCase):
    """`--auth none` is an explicit mode, not a missing key."""

    def setUp(self):
        self.temp = tempfile.TemporaryDirectory(prefix="web-noauth-", dir="/tmp/opencode")
        self.addCleanup(self.temp.cleanup)
        self.commands = FakeCommands()
        backend = web.Backend(SINK, {}, self.commands, Path(self.temp.name))
        self.devices = [{"name": "debra-3c6b3f",
                         "url": "http://debra-3c6b3f.local:8787/", "label": "Lab Pi 5"}]
        self.server = web.Server(("127.0.0.1", 0), backend, None, [], self.devices)
        self.host = f"127.0.0.1:{self.server.server_port}"
        self.server.hosts = frozenset([self.host])
        self.thread = threading.Thread(target=self.server.serve_forever, daemon=True)
        self.thread.start()
        self.addCleanup(self.close)

    def close(self):
        self.server.shutdown()
        self.server.server_close()
        self.thread.join()

    def request(self, method="GET", path="/api/status", body=None, **headers):
        defaults = {"Host": self.host}
        if method == "POST":
            defaults.update({"Origin": "http://" + self.host, "Content-Type": "application/json"})
        defaults.update(headers)
        connection = http.client.HTTPConnection("127.0.0.1", self.server.server_port, timeout=5)
        connection.request(method, path, body, defaults)
        response = connection.getresponse()
        data = response.read()
        result = response.status, dict(response.getheaders()), data
        connection.close()
        return result

    def test_status_is_readable_without_a_key_and_reports_the_mode(self):
        code, _, raw = self.request()
        self.assertEqual(code, 200)
        self.assertEqual(json.loads(raw)["auth"], "none")
        self.assertEqual(json.loads(raw)["audio"]["percent"], 36)

    def test_writes_still_require_same_origin_and_the_host_check(self):
        self.assertEqual(self.request("POST", "/api/audio/volume", '{"percent":20}',
                                      Origin="http://attacker.test")[0], 403)
        self.assertEqual(self.commands.calls, [])
        self.assertEqual(self.request(Host="attacker.test:8787")[0], 403)
        self.assertEqual(self.request("POST", "/api/audio/volume", '{"percent":20}')[0], 200)

    def test_device_list_is_served_without_a_key(self):
        code, _, raw = self.request(path="/api/devices")
        self.assertEqual(code, 200)
        self.assertEqual(json.loads(raw)["devices"],
                         [dict(device, source="configured") for device in self.devices])


class StartupTests(unittest.TestCase):
    def test_invalid_listening_ports_exit_with_a_message_not_a_traceback(self):
        with tempfile.TemporaryDirectory(prefix="web-port-", dir="/tmp/opencode") as temp:
            # Keep key mode and an absent state directory: a regressed validator
            # fails on the key before it can bind port 80 or probe host audio.
            for port in (80, 70000, 0, 1023, 65536, -1):
                with self.subTest(port=port):
                    result = subprocess.run(
                        [sys.executable, "-B", str(SOURCE / "server.py"), "serve",
                         "--sink", SINK, "--port", str(port),
                         "--state-dir", str(Path(temp) / "absent")],
                        capture_output=True, text=True, timeout=5)
                    self.assertNotEqual(result.returncode, 0)
                    self.assertIn("--port must be an integer from 1024 to 65535", result.stderr)
                    self.assertNotIn("Traceback", result.stderr)
                    self.assertNotIn("listening", result.stdout)

    def test_unprivileged_listening_port_boundaries_are_accepted(self):
        with tempfile.TemporaryDirectory(prefix="web-port-", dir="/tmp/opencode") as temp:
            for port in (1024, 65535):
                with self.subTest(port=port):
                    argv = ["server.py", "serve", "--state-dir", temp, "--sink", SINK,
                            "--auth", "none", "--port", str(port)]
                    with patch.object(sys, "argv", argv), patch.object(web, "Server") as server, \
                            patch.object(web, "DiscoveryCache"), patch("builtins.print"):
                        web.main()
                    self.assertEqual(server.call_args.args[0], ("127.0.0.1", port))


class DeviceListTests(unittest.TestCase):
    def load(self, value):
        with tempfile.TemporaryDirectory(prefix="web-devices-", dir="/tmp/opencode") as temp:
            path = Path(temp) / "devices.json"
            path.write_text(json.dumps(value))
            return web.load_devices(path)

    def test_accepts_plain_host_port_links(self):
        self.assertEqual(self.load([{"name": "debra-1", "url": "http://debra-1.local:8787/"}])[0]["name"],
                         "debra-1")

    def test_default_port_is_refused_with_a_reason(self):
        # Chromium normalizes http://host:80/ to http://host/, which the Host
        # allowlist cannot accept; an accepted-then-broken link is worse than a
        # link that never appears.
        with self.assertRaises(ValueError) as caught:
            web.canonical_device_url("http://device.local:80/")
        self.assertIn("Port 80", str(caught.exception))

    def test_canonical_url_contract(self):
        cases = {
            "HTTP://DEVICE.Local:08787": "http://device.local:8787/",
            "http://127.0.0.1:1/": "http://127.0.0.1:1/",
            "http://device.local:65535": "http://device.local:65535/",
            # A browser drops the default port, so a :80 link could never
            # satisfy the Host check this service applies.
            "http://device.local:80/": None,
            "http://device.local:0/": None,
            "http://device.local:65536/": None,
            "http://device.local:99999/": None,
            " http://device.local:8787/": None,
            "http://device.local:87\t87/": None,
            "http://device.local:8787/\n": None,
            "http://device.local:8787/?": None,
            "http://device.local:8787/#": None,
            "http://user@device.local:8787/": None,
            "http://device.local:8787/path": None,
            "https://device.local:8787/": None,
            "http://127.01.0.1:8787/": None,
            "http://127.1:8787/": None,
            "http://0x7f:8787/": None,
            "http://bad-.local:8787/": None,
            "http://a..local:8787/": None,
        }
        for url, expected in cases.items():
            with self.subTest(url=url):
                if expected is None:
                    with self.assertRaises(ValueError):
                        self.load([{"name": "test", "url": url}])
                else:
                    self.assertEqual(self.load([{"name": "test", "url": url}])[0]["url"], expected)

    def test_rejects_anything_but_plain_http_host_port(self):
        for url in ("https://debra-1.local:8787/", "http://user:pw@debra-1.local:8787/",
                    "http://debra-1.local:8787/status", "http://debra-1.local:8787/?x=1",
                    "http://debra-1.local:8787/#key=secret", "javascript:alert(1)",
                    "http://debra-1.local", "file:///etc/passwd"):
            with self.subTest(url=url), self.assertRaises(ValueError):
                self.load([{"name": "debra-1", "url": url}])

    def test_rejects_unknown_fields_and_oversized_lists(self):
        with self.assertRaises(ValueError):
            self.load([{"name": "debra-1", "url": "http://debra-1.local:8787/", "key": "secret"}])
        with self.assertRaises(ValueError):
            self.load([{"name": f"debra-{n}", "url": "http://debra-1.local:8787/"} for n in range(51)])


class DiscoveryTests(unittest.TestCase):
    def setUp(self):
        self.configured = [
            {"name": "first", "url": "http://first.local:8787/", "label": "My label"},
            {"name": "second", "url": "http://second.local:8787/", "label": "Second"},
        ]
        self.cache = web.DiscoveryCache(browse=lambda: {"devices": [], "error": None})
        self.server = web.Server(("127.0.0.1", 0), None, TOKEN, [], self.configured, self.cache)
        self.host = f"127.0.0.1:{self.server.server_port}"
        self.server.hosts = frozenset([self.host])
        self.thread = threading.Thread(target=self.server.serve_forever, daemon=True)
        self.thread.start()
        self.addCleanup(self.close)

    def close(self):
        self.server.shutdown()
        self.server.server_close()
        self.thread.join()
        if self.cache.thread is not None:
            self.cache.thread.join(timeout=2)

    def request(self, path):
        connection = http.client.HTTPConnection("127.0.0.1", self.server.server_port, timeout=2)
        try:
            connection.request("GET", path, headers={"Host": self.host})
            response = connection.getresponse()
            return response.status, json.loads(response.read())
        finally:
            connection.close()

    def served(self, *extra):
        """The list /api/devices returns: configured rows marked, then extras."""
        return [dict(device, source="configured") for device in self.configured] + list(extra)

    def scan(self, records, error=None):
        self.cache.browse = lambda: {"devices": records, "error": error}
        self.cache.scan()

    def test_merge_canonical_urls_configured_first_and_label_wins(self):
        self.scan([
            {"name": "claim", "url": "HTTP://FIRST.LOCAL:08787", "label": "Spoofed"},
            {"name": "new", "url": "HTTP://NEW.LOCAL:08787", "label": "Kitchen",
             "host": "new.local", "addresses": ["192.0.2.1"]},
            {"name": "duplicate", "url": "http://new.local:8787/", "label": "Other"},
        ])
        code, data = self.request("/api/devices")
        self.assertEqual(code, 200)
        expected = self.served(
            {"name": "new", "url": "http://new.local:8787/", "label": "Kitchen",
             "source": "discovered"})
        # A discovered record matching a configured URL adds no row, but the row
        # must say it was found both ways or working discovery looks hand-written.
        expected[0]["source"] = "configured+discovered"
        self.assertEqual(data["devices"], expected)
        self.assertEqual(self.request("/api/status")[0], 401)

    def test_duplicate_configured_urls_appear_once(self):
        self.server.devices = (*self.configured, dict(self.configured[0], label="Duplicate"))
        code, body = self.request("/api/devices")
        self.assertEqual((code, body["devices"]), (200, self.served()))

    def test_invalid_discovered_hosts_ports_names_and_labels_are_dropped(self):
        records = [
            {"name": "badhost", "url": "http://bad-.local:8787/", "label": ""},
            {"name": "badport", "url": "http://okay.local:65536/", "label": ""},
            {"name": "defaultport", "url": "http://okay.local:80/", "label": ""},
            {"name": "nonlocal", "url": "http://okay.example:8787/", "label": ""},
            {"name": "ip", "url": "http://192.0.2.1:8787/", "label": ""},
            {"name": "x" * 65, "url": "http://okay.local:8787/", "label": ""},
            {"name": "bad name", "url": "http://okay.local:8787/", "label": ""},
            {"name": "badlabel", "url": "http://okay.local:8787/", "label": "x" * 81},
            {"name": "good", "url": "http://okay.local:8787/"},
            None,
        ]
        self.scan(records)
        self.assertEqual(self.request("/api/devices")[1]["devices"], self.served(
            {"name": "good", "url": "http://okay.local:8787/", "label": "",
             "source": "discovered"}))

    def test_device_list_says_which_host_is_serving_it(self):
        # The page marks its own row with this, so it never offers to "switch"
        # to the server it is already on. Nothing else about the device is added.
        code, body = self.request("/api/devices")
        self.assertEqual(code, 200)
        self.assertEqual(set(body["self"]), {"hostname", "port"})
        self.assertEqual(body["self"]["hostname"], socket.gethostname())
        self.assertEqual(body["self"]["port"], self.server.server_address[1])

    def test_devices_found_both_ways_say_so_and_discovery_reports_its_state(self):
        # A working discovery that finds nothing looks identical to a broken one,
        # so the response carries when it last scanned and whether it is running.
        self.scan([{"name": "first", "url": "http://first.local:8787/", "label": "ignored"},
                   {"name": "other", "url": "http://other.local:8787/", "label": "Other"}])
        code, body = self.request("/api/devices")
        self.assertEqual(code, 200)
        sources = {device["name"]: device["source"] for device in body["devices"]}
        self.assertEqual(sources, {"first": "configured+discovered", "second": "configured",
                                   "other": "discovered"})
        status = body["discovery"]
        self.assertEqual(status["found"], 2)
        self.assertIsNone(status["error"])
        self.assertIsInstance(status["seconds_since_scan"], int)
        self.assertFalse(status["enabled"])  # no worker thread was started here

    def test_discovery_status_reports_an_error_and_never_started(self):
        cache = web.DiscoveryCache(browse=lambda: {"devices": [], "error": "avahi-browse timed out"})
        self.assertIsNone(cache.status()["seconds_since_scan"])
        self.assertFalse(cache.status()["enabled"])
        cache.scan()
        status = cache.status()
        self.assertEqual(status["error"], "avahi-browse timed out")
        self.assertEqual(status["found"], 0)
        self.assertIsInstance(status["seconds_since_scan"], int)

    def test_worker_dying_after_startup_is_reported_and_not_called_active(self):
        # A thread object outlives its thread. Before this, a worker that died
        # after a successful scan still reported enabled: true and error: null.
        cache = web.DiscoveryCache(browse=lambda: {"devices": [], "error": None})
        with patch.object(cache.stop, "wait", side_effect=RuntimeError("fixture worker crash")):
            cache.start()
            cache.thread.join(timeout=2)
        self.assertFalse(cache.thread.is_alive())
        status = cache.status()
        self.assertFalse(status["enabled"])
        self.assertIn("Discovery worker stopped", status["error"])
        self.assertIn("RuntimeError", status["error"])

    def test_hub_revalidation_keeps_the_named_rejection_reason(self):
        # The parser logs its own drops, but the hub revalidates independently.
        # Silently discarding that second rejection left no warning anywhere.
        with self.assertLogs(discovery.LOGGER, level="WARNING") as logs:
            self.scan([{"name": "badport", "url": "http://debra.local:80/"},
                       {"name": "good", "url": "http://good.local:8787/"}])
        code, body = self.request("/api/devices")
        self.assertEqual(code, 200)
        self.assertEqual(body["devices"], self.served(
            {"name": "good", "url": "http://good.local:8787/", "label": "",
             "source": "discovered"}))
        status = body["discovery"]
        self.assertIsNone(status["error"])  # the scan itself worked
        self.assertEqual(len(status["refused"]), 1)
        self.assertIn("Port 80", status["refused"][0])
        self.assertIn("Port 80", "\n".join(logs.output))

    def test_a_record_the_parser_refuses_is_reported_by_the_page(self):
        # The parser drops a bad advertisement before the hub sees it, so the
        # hub's own revalidation never ran and the page said "found 0" with no
        # refusal. This drives the real browse() -> parse() -> scan() path with
        # only the avahi process faked.
        text = "\n".join([
            '=;eth0;IPv4;Bad;_debra._tcp;local;debra.local;192.0.2.1;80;'
            '"name=bad" "label=Bad"',
            '=;eth0;IPv4;Good;_debra._tcp;local;good.local;192.0.2.2;8787;'
            '"name=good" "label=Good"',
        ]) + "\n"
        cache = web.DiscoveryCache(browse=discovery.browse)
        with patch.object(discovery.subprocess, "run",
                          return_value=subprocess.CompletedProcess([], 0, text, "")):
            cache.scan()
        status = cache.status()
        self.assertIsNone(status["error"])
        self.assertEqual(status["found"], 1)
        self.assertEqual(len(status["refused"]), 1,
                         f"the parser's refusal never reached the page: {status['refused']}")
        self.assertIn("bad", status["refused"][0])
        self.assertIn("Port 80", status["refused"][0])
        self.assertEqual([device["name"] for device in cache.snapshot()], ["good"])

    def test_refusals_are_counted_per_advertisement_not_per_reason(self):
        text = "\n".join([
            '=;eth0;IPv4;One;_debra._tcp;local;one.local;192.0.2.1;80;"name=one"',
            '=;eth0;IPv4;Two;_debra._tcp;local;two.local;192.0.2.2;80;"name=two"',
        ]) + "\n"
        cache = web.DiscoveryCache(browse=discovery.browse)
        with patch.object(discovery.subprocess, "run",
                          return_value=subprocess.CompletedProcess([], 0, text, "")):
            cache.scan()
        # The page says "Refused N advertisements"; two identical reasons are
        # still two advertisements.
        self.assertEqual(len(cache.status()["refused"]), 2)

    def test_two_refusals_with_one_name_and_reason_are_still_two_advertisements(self):
        # Two advertised records that share an instance name and are refused for
        # the same reason (one port 0, one port 65536) are two devices missing
        # from the page. Reducing the cache to a set of display strings counted
        # them as one.
        text = "\n".join([
            '=;eth0;IPv4;Collision;_debra._tcp;local;collision.local;192.0.2.1;0;'
            '"name=Collision"',
            '=;eth0;IPv4;Collision;_debra._tcp;local;collision.local;192.0.2.2;65536;'
            '"name=Collision"',
        ]) + "\n"
        cache = web.DiscoveryCache(browse=discovery.browse)
        with patch.object(discovery.subprocess, "run",
                          return_value=subprocess.CompletedProcess([], 0, text, "")):
            cache.scan()
        refused = cache.status()["refused"]
        self.assertEqual(len(refused), 2, refused)
        # They are still one display string each: the count is what tells them
        # apart, and the page prints "Refused 2 advertisements" from it.
        self.assertEqual(set(refused), {"Collision: Device Collision: invalid URL: Invalid host or port"})
        self.assertEqual(cache.snapshot(), ())

    def test_error_timeout_exception_and_empty_clear_previous_cache(self):
        record = {"name": "new", "url": "http://new.local:8787/", "label": "New"}
        for outcome in ("error", "timeout", "exception", "empty", "malformed"):
            with self.subTest(outcome=outcome):
                self.scan([record])
                self.assertEqual(len(self.request("/api/devices")[1]["devices"]), 3)
                if outcome == "error":
                    self.scan([record], "browse failed")
                elif outcome == "empty":
                    self.scan([])
                else:
                    def fail():
                        if outcome == "timeout":
                            raise subprocess.TimeoutExpired("avahi-browse", 8)
                        if outcome == "exception":
                            raise RuntimeError("unexpected")
                        return {"devices": None, "error": None}
                    self.cache.browse = fail
                    self.cache.scan()
                code, body = self.request("/api/devices")
        self.assertEqual((code, body["devices"]), (200, self.served()))

    def test_missing_avahi_clears_cache_using_default_browser(self):
        self.scan([{"name": "old", "url": "http://old.local:8787/", "label": "Old"}])
        self.cache.browse = web.DiscoveryCache().browse
        with patch.object(discovery.subprocess, "run", side_effect=FileNotFoundError()):
            self.cache.scan()
        code, body = self.request("/api/devices")
        self.assertEqual((code, body["devices"]), (200, self.served()))

    def test_request_serves_cache_while_background_scan_is_blocked(self):
        started, release = threading.Event(), threading.Event()
        self.addCleanup(release.set)
        def blocked_browse():
            started.set()
            release.wait(4)
            return {"devices": [], "error": None}
        self.cache.browse = blocked_browse
        self.cache.start()
        self.assertTrue(started.wait(1))
        start = time.monotonic()
        code, body = self.request("/api/devices")
        self.assertEqual((code, body["devices"]), (200, self.served()))
        self.assertLess(time.monotonic() - start, 1)
        self.assertTrue(self.cache.thread.is_alive())
        release.set()

    def test_last_good_cache_remains_during_next_scan(self):
        record = {"name": "new", "url": "http://new.local:8787/", "label": "New"}
        self.scan([record])
        started, release = threading.Event(), threading.Event()
        self.addCleanup(release.set)
        def blocked_browse():
            started.set()
            release.wait(4)
            return {"devices": [], "error": None}
        self.cache.browse = blocked_browse
        self.cache.start()
        self.assertTrue(started.wait(1))
        self.assertEqual(self.request("/api/devices")[1]["devices"][-1]["name"], "new")
        release.set()

    def test_cli_and_hub_accept_the_same_records(self):
        from tools import discover
        cases = [
            ("lowest", "low.local", "1", "Low"),
            ("highest", "high.local", "65535", "High"),
            ("canonical", "UPPER.LOCAL", "08787", "Canonical"),
            ("x" * 64, "limit.local", "8787", "y" * 80),
            ("defaultport", "default.local", "80", "Default"),
            ("nonlocal", "device.example", "8787", "External"),
            ("notlocal", "notlocal", "8787", "Not .local"),
            ("ip", "192.0.2.1", "8787", "IP"),
            ("zero", "zero.local", "0", "Zero"),
            ("highport", "highport.local", "65536", "High"),
            ("badhost", "bad-.local", "8787", "Bad"),
            ("x" * 65, "longname.local", "8787", "Long name"),
            ("bad name", "space.local", "8787", "Bad name"),
            ("longlabel", "longlabel.local", "8787", "y" * 81),
        ]
        text = "\n".join(
            f'=;eth0;IPv4;instance-{i};_debra._tcp;local;{host};192.0.2.1;{port};'
            f'"name={name}" "label={label}"'
            for i, (name, host, port, label) in enumerate(cases))
        self.cache.browse = web.DiscoveryCache().browse
        output = StringIO()
        with patch.object(discovery.subprocess, "run", return_value=
                          subprocess.CompletedProcess([], 0, text, "")), \
                self.assertLogs(discovery.LOGGER, level="WARNING") as logs:
            with redirect_stdout(output):
                self.assertEqual(discover.main(["--json"]), 0)
            self.cache.scan()
        cli_devices = json.loads(output.getvalue())["devices"]
        code, body = self.request("/api/devices")
        self.assertEqual(code, 200)
        discovered = [row for row in body["devices"] if row["source"] == "discovered"]
        self.assertEqual([row["name"] for row in cli_devices],
                         ["canonical", "highest", "lowest", "x" * 64])
        self.assertEqual(discovered, [
            {"name": row["name"], "url": row["url"], "label": row["label"], "source": "discovered"}
            for row in cli_devices])
        self.assertEqual(cli_devices[0]["url"], "http://upper.local:8787/")
        self.assertIn("Port 80", "\n".join(logs.output))
        self.assertIn("must end with .local", "\n".join(logs.output))

    def test_shared_parser_change_reaches_cli_and_server(self):
        from tools import discover
        text = '\n'.join([
            '=;eth0;IPv4;Debra\\; test;_debra._tcp;local;debra.local;192.0.2.1;8787;'
            '"name=debra-1" "label=Kitchen"',
            '=;wifi;IPv6;Debra\\; test;_debra._tcp;local;debra.local;::1;8787;'
            '"name=debra-1" "label=Kitchen"',
            '=;eth0;IPv4;Other;_http._tcp;local;other.local;192.0.2.2;80;',
        ])
        original_parse = discovery.parse
        def changed_parse(output, refused=None):
            records = original_parse(output, refused)
            for record in records:
                record["label"] = "Changed parser"
            return records
        self.cache.browse = web.DiscoveryCache().browse
        output = StringIO()
        with patch.object(discovery.subprocess, "run",
                          return_value=subprocess.CompletedProcess([], 0, text, "")) as run, \
                patch.object(discovery, "parse", side_effect=changed_parse) as parse:
            with redirect_stdout(output):
                self.assertEqual(discover.main(["--json"]), 0)
            self.cache.scan()
        self.assertEqual(parse.call_count, 2)
        self.assertEqual(json.loads(output.getvalue())["devices"][0]["label"], "Changed parser")
        self.assertEqual(self.request("/api/devices")[1]["devices"], self.served(
            {"name": "debra-1", "url": "http://debra.local:8787/",
             "label": "Changed parser", "source": "discovered"}))
        self.assertEqual(run.call_count, 2)
        self.assertEqual(run.call_args.args[0], ["avahi-browse", "-rtp", "-t", "_debra._tcp"])
        self.assertEqual(run.call_args.kwargs["timeout"], 8)

    def test_self_announcement_on_two_interfaces_is_one_device(self):
        text = '\n'.join([
            '=;eth0;IPv4;Debra self;_debra._tcp;local;self.local;192.0.2.1;8787;"name=self"',
            '=;wlan0;IPv6;Debra self;_debra._tcp;local;self.local;::1;8787;"name=self"',
        ])
        self.cache.browse = web.DiscoveryCache().browse
        with patch.object(discovery.subprocess, "run",
                          return_value=subprocess.CompletedProcess([], 0, text, "")):
            self.cache.scan()
        self.assertEqual(self.request("/api/devices")[1]["devices"], self.served(
            {"name": "self", "url": "http://self.local:8787/", "label": "Debra self",
             "source": "discovered"}))

    def test_serve_starts_discovery_without_waiting_for_a_request(self):
        with tempfile.TemporaryDirectory(prefix="web-start-", dir="/tmp/opencode") as temp:
            argv = ["server.py", "serve", "--state-dir", temp, "--sink", SINK, "--auth", "none"]
            with patch.object(sys, "argv", argv), patch.object(web, "DiscoveryCache") as cache, \
                    patch.object(web, "Server") as server, patch("builtins.print"):
                web.main()
        cache.return_value.start.assert_called_once_with()
        self.assertIs(server.call_args.args[5], cache.return_value)
        server.return_value.__enter__.return_value.serve_forever.assert_called_once_with()

    def test_worker_start_failure_reports_reason_and_keeps_configured_links(self):
        for stage in ("construct", "start"):
            for error in (RuntimeError("no threads"), OSError("resource exhausted")):
                with self.subTest(stage=stage, error=type(error).__name__):
                    target, name = ((threading, "Thread") if stage == "construct"
                                    else (threading.Thread, "start"))
                    with patch.object(target, name, side_effect=error):
                        self.cache.start()
                    self.assertIsNone(self.cache.thread)
                    code, body = self.request("/api/devices")
                    self.assertEqual((code, body["devices"]), (200, self.served()))
                    self.assertEqual(body["discovery"], {
                        "enabled": False, "found": 0, "seconds_since_scan": None,
                        "error": f"Discovery thread could not start ({type(error).__name__}: {error})",
                        "refused": []})


class InstallerTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory(prefix="web-install-", dir="/tmp/opencode")
        self.addCleanup(self.temp.cleanup)
        self.home = Path(self.temp.name)
        self.state = self.home / ".config/debra/web"
        self.unit = self.home / ".config/systemd/user/debra-web.service"

    def install(self, hosts=None, source=SOURCE, **kwargs):
        return installer.install(self.home, source, SINK, "127.0.0.1", 8787,
                                 hosts or ["device.local:8787"], "/usr/bin/python3", **kwargs)

    def test_init_key_permissions_and_preservation(self):
        self.assertTrue(web.init_state(self.state))
        key = web.load_key(self.state)
        self.assertGreaterEqual(len(key), 32)
        self.assertEqual(self.state.stat().st_mode & 0o777, 0o700)
        self.assertEqual((self.state / "access.key").stat().st_mode & 0o777, 0o600)
        self.assertFalse(web.init_state(self.state))
        self.assertEqual(web.load_key(self.state), key)

    def test_interrupted_staging_creation_can_retry(self):
        with patch.object(web.tempfile, "mkstemp", side_effect=OSError("creation interrupted")):
            with self.assertRaises(OSError):
                web.init_state(self.state)
        self.assertFalse((self.state / "access.key").exists())
        self.assertTrue(web.init_state(self.state))
        web.load_key(self.state)

    def test_interrupted_key_write_retained_separately_and_retry_succeeds(self):
        real_fdopen = web.os.fdopen
        @contextmanager
        def interrupted(fd, *args):
            with real_fdopen(fd, *args) as stream:
                class Writer:
                    def write(self, data):
                        stream.write(data[:5])
                        stream.flush()
                        raise OSError("write interrupted")
                yield Writer()
        with patch.object(web.os, "fdopen", side_effect=interrupted):
            with self.assertRaises(OSError):
                web.init_state(self.state)
        self.assertFalse((self.state / "access.key").exists())
        artifact = next(self.state.glob(".access-key.staged-*"))
        self.assertEqual(artifact.stat().st_size, 5)
        self.assertEqual(artifact.stat().st_mode & 0o777, 0o600)
        self.assertTrue(web.init_state(self.state))
        key = web.load_key(self.state)
        self.assertFalse(web.init_state(self.state))
        self.assertEqual(web.load_key(self.state), key)
        self.assertTrue(artifact.exists())

    def test_interrupted_key_publication_can_retry(self):
        with patch.object(web.os, "link", side_effect=OSError("publish interrupted")):
            with self.assertRaises(OSError):
                web.init_state(self.state)
        self.assertFalse((self.state / "access.key").exists())
        self.assertTrue(web.init_state(self.state))
        web.load_key(self.state)

    def test_concurrent_key_publication_preserves_existing_key(self):
        real_link = web.os.link
        key = "existing_" + "b" * 40
        def competing_key(staged, target):
            fd = os.open(target, os.O_WRONLY | os.O_CREAT | os.O_EXCL, 0o600)
            with os.fdopen(fd, "w") as stream:
                stream.write(key + "\n")
            real_link(staged, target)
        with patch.object(web.os, "link", side_effect=competing_key):
            self.assertFalse(web.init_state(self.state))
        self.assertEqual(web.load_key(self.state), key)

    def test_insecure_and_symlinked_key_rejected(self):
        web.init_state(self.state)
        key = self.state / "access.key"
        key.chmod(0o644)
        with self.assertRaises(ValueError):
            web.load_key(self.state)
        key.chmod(0o600)
        saved = self.state / "saved.key"
        key.rename(saved)
        key.symlink_to(saved)
        with self.assertRaises(OSError):
            web.load_key(self.state)
        self.assertTrue(saved.exists())

    def test_insecure_state_rejected(self):
        self.state.mkdir(parents=True)
        # `mkdir(mode=…)` is masked by the process umask, so under `umask 0077`
        # this fixture was 0700 and the test failed for the wrong reason.
        self.state.chmod(0o755)
        with self.assertRaises(ValueError):
            web.init_state(self.state)
        self.assertFalse((self.state / "access.key").exists())

    def test_install_only_fixed_payload_idempotent_preserves_key(self):
        result = self.install()
        key = web.load_key(self.state)
        self.assertTrue(result["changed"])
        self.assertIn("--sink", self.unit.read_text())
        self.assertNotIn(key, self.unit.read_text())
        release = self.home / ".local/share/debra/web/releases" / result["release"]
        self.assertEqual(sorted(str(p.relative_to(release)) for p in release.rglob("*") if p.is_file()),
                         sorted(installer.PAYLOAD))
        self.assertFalse(self.install()["changed"])
        self.assertEqual(web.load_key(self.state), key)

    def test_installed_server_serves_configured_devices_without_avahi(self):
        help_result = subprocess.run([sys.executable, "-B", str(SOURCE / "install.py"), "--help"],
                                     cwd=self.home, capture_output=True, text=True, timeout=5)
        self.assertEqual(help_result.returncode, 0, help_result.stderr)
        self.assertIn("--sink", help_result.stdout)
        configured = [{"name": "first", "url": "http://first.local:8787/", "label": "First"}]
        result = self.install(devices=configured)
        release = self.home / ".local/share/debra/web/releases" / result["release"]
        for name in installer.PAYLOAD:
            self.assertEqual((release / name).read_bytes(), (SOURCE / name).read_bytes())
        empty_path = self.home / "empty-path"
        empty_path.mkdir()
        env = dict(os.environ, PATH=str(empty_path), PYTHONNOUSERSITE="1")
        env.pop("PYTHONPATH", None)
        probe = subprocess.run([sys.executable, "-B", "-c",
                                "import discovery, json; print(json.dumps(discovery.browse()))"],
                               cwd=release, env=env, capture_output=True, text=True, timeout=5)
        self.assertEqual(probe.returncode, 0, probe.stderr)
        self.assertEqual(json.loads(probe.stdout),
                         {"devices": [], "error": "avahi-browse is not installed"})
        devices = self.home / "configured.json"
        devices.write_text(json.dumps(configured))
        with socket.socket() as reservation:
            reservation.bind(("127.0.0.1", 0))
            port = reservation.getsockname()[1]
        host = f"127.0.0.1:{port}"
        process = subprocess.Popen(
            [sys.executable, "-B", str(release / "server.py"), "serve", "--state-dir", str(self.state),
             "--sink", SINK, "--auth", "none", "--port", str(port), "--host", host,
             "--devices", str(devices)], cwd=self.home, env=env,
            stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True)
        try:
            deadline = time.monotonic() + 5
            while True:
                try:
                    connection = http.client.HTTPConnection("127.0.0.1", port, timeout=0.5)
                    connection.request("GET", "/api/devices", headers={"Host": host})
                    response = connection.getresponse()
                    status, body = response.status, json.loads(response.read())
                    connection.close()
                    break
                except (OSError, http.client.HTTPException):
                    if process.poll() is not None or time.monotonic() >= deadline:
                        self.fail("Installed server did not start")
                    time.sleep(0.05)
            self.assertEqual((status, body["devices"]),
                             (200, [dict(device, source="configured") for device in configured]))
            self.assertIsNone(process.poll())
        finally:
            process.terminate()
            process.communicate(timeout=5)

    def test_update_preserves_recoverable_previous_unit(self):
        self.install()
        old = self.unit.read_bytes()
        result = self.install(["other.local:8787"])
        self.assertEqual(Path(result["previous_unit"]).read_bytes(), old)
        self.assertEqual(Path(result["previous_unit"]).stat().st_mode & 0o777, 0o600)
        # Demonstrate restoring exact previous configuration in the fixture.
        self.unit.write_bytes(Path(result["previous_unit"]).read_bytes())
        self.assertEqual(self.unit.read_bytes(), old)

    def test_refuses_unmanaged_service_without_touching_it(self):
        self.unit.parent.mkdir(parents=True)
        self.unit.write_text("user's own service")
        with self.assertRaises(ValueError):
            self.install()
        self.assertEqual(self.unit.read_text(), "user's own service")
        self.assertFalse(self.state.exists())

    def test_invalid_host_refused_before_writes(self):
        for hosts in (["device.local"], ["device.local:22"], ["evil:8787/x"], ["evil\n:8787"]):
            with self.subTest(hosts=hosts), self.assertRaises(ValueError):
                self.install(hosts)
        self.assertFalse(self.state.exists())

    def test_invalid_listening_port_refused_before_installer_writes(self):
        for port in (80, 70000, 1023, 65536):
            with self.subTest(port=port), self.assertRaisesRegex(ValueError, "1024 to 65535"):
                installer.install(self.home, SOURCE, SINK, "127.0.0.1", port,
                                  [f"device.local:{port}"], "/usr/bin/python3")
            self.assertFalse(self.state.exists())
            self.assertFalse(self.unit.exists())

    def test_systemd_quoting(self):
        self.assertEqual(installer.quoted('a % " \\'), '"a %% \\" \\\\"')
        self.assertEqual(installer.quoted("$HOME"), '"$$HOME"')
        with self.assertRaises(ValueError):
            installer.quoted("arg\nExecStart=bad")

    def test_the_unit_round_trips_through_the_installers_own_quoting(self):
        # The installer's own quoting has to survive the decoder that restore
        # reads with. Restore used to split on whitespace and strip double
        # quotes, so a HOME holding a space, a percent or a dollar decoded into
        # a path that does not exist.
        for value in ("/home/a b/.local", "/home/100%/.local", "/home/cost$5/.local",
                      '/home/quote"back\\slash/.local', "plain", ""):
            with self.subTest(value=value):
                self.assertEqual(installer.exec_arguments(installer.quoted(value)), [value])
        self.assertEqual(installer.exec_arguments('"a" "b c" "d e" "f"'),
                         ["a", "b c", "d e", "f"])

    def test_an_exec_start_this_installer_did_not_write_is_refused(self):
        # Everything below is valid systemd that `quoted()` never emits. A
        # decoder that accepts more than it can reproduce has already checked
        # a different path from the one systemd would start: the r9 review
        # showed `he\x20home` read as `hex20home`, with only the wrong release
        # present, and restore exited 0.
        for value in ("/usr/bin/true one two", "\"a\"b", '"a""b"', "'a b'",
                      '"a\\x20b"', '"a\\nb"', '"a%i"', '"a$HOME"', '"a" ',
                      '"unterminated'):
            with self.subTest(value=value):
                with self.assertRaisesRegex(ValueError, "not in the form this installer writes"):
                    installer.exec_arguments(value)
        # Single quotes are refused even though systemd accepts them: the
        # installer never writes one, so restore will not guess at its C
        # escapes and expansion rules.
        self.assertEqual(installer.exec_arguments('"-a" ""'), ["-a", ""])

    def test_the_start_command_is_read_from_the_service_section_only(self):
        # systemd ignores ExecStart in [Unit] and treats an empty ExecStart= as
        # a reset, so neither unit has a start command. Finding the first
        # literal ExecStart anywhere reported both as restorable.
        true = installer.quoted("/usr/bin/true")
        cases = {
            "plain": installer.MARKER + f"[Service]\nExecStart={true}\n",
            "spaced": installer.MARKER + f"[Service]\nExecStart = {true}\n",
            "ignore-failure": installer.MARKER + f"[Service]\nExecStart=-{true}\n",
        }
        for name, text in cases.items():
            with self.subTest(case=name):
                self.assertEqual(installer.service_commands(text.encode()), [["/usr/bin/true"]])
        one, two = installer.quoted("one"), installer.quoted("two")
        for name, text in {
            "commented": installer.MARKER + f"[Service]\n# ExecStart={true}\n",
            "wrong-section": installer.MARKER + f"[Unit]\nExecStart={true}\n",
            "reset": installer.MARKER + f"[Service]\nExecStart={true}\nExecStart=\n",
            "empty": installer.MARKER + "[Service]\nExecStart=\n",
        }.items():
            with self.subTest(case=name):
                self.assertEqual(installer.service_commands(text.encode()), [])
        self.assertEqual(installer.service_commands(
            (installer.MARKER + f"[Service]\nExecStart={true} {one} {two}\n").encode()),
            [["/usr/bin/true", "one", "two"]])

    def test_interrupted_release_publish_can_retry_without_overwrite(self):
        with patch.object(Path, "rename", side_effect=OSError("simulated interruption")):
            with self.assertRaises(OSError):
                self.install()
        self.assertFalse(self.unit.exists())
        key = web.load_key(self.state)
        self.assertTrue(self.install()["changed"])
        self.assertEqual(web.load_key(self.state), key)
        pending = self.home / ".local/share/debra/web/releases"
        self.assertEqual(len(list(pending.glob(".pending-*"))), 1)

    def test_interrupted_unit_replace_preserves_previous_and_can_retry(self):
        self.install()
        old = self.unit.read_bytes()
        with patch.object(installer.os, "replace", side_effect=OSError("simulated interruption")):
            with self.assertRaises(OSError):
                self.install(["other.local:8787"])
        self.assertEqual(self.unit.read_bytes(), old)
        backups = self.home / ".local/share/debra/web/previous-units"
        self.assertEqual(next(backups.iterdir()).read_bytes(), old)
        self.assertTrue(self.install(["other.local:8787"])["changed"])

    def test_refuses_symlinked_release_parent(self):
        self.install()
        base = self.home / ".local/share/debra/web"
        (base / "releases").rename(base / "saved-releases")
        (base / "releases").symlink_to(base / "saved-releases")
        old = self.unit.read_bytes()
        with self.assertRaises(ValueError):
            self.install()
        self.assertEqual(self.unit.read_bytes(), old)

    def test_auth_none_is_an_explicit_unit_argument(self):
        result = self.install(auth="none")
        text = self.unit.read_text()
        self.assertIn('"--auth" "none"', text)
        self.assertTrue(result["changed"])
        with self.assertRaises(ValueError):
            self.install(auth="off")

    def test_device_list_is_copied_private_and_referenced(self):
        devices = [{"name": "debra-3c6b3f", "url": "http://debra-3c6b3f.local:8787/",
                    "label": "Lab Pi 5"}]
        self.install(devices=devices)
        stored = next(self.state.glob("devices-*.json"))
        self.assertEqual(json.loads(stored.read_text()), devices)
        self.assertEqual(stored.stat().st_mode & 0o777, 0o600)
        self.assertIn(str(stored), self.unit.read_text())
        # Dropping the list is a normal install change, not a special case.
        self.install()
        self.assertNotIn("--devices", self.unit.read_text())

    def test_list_only_change_rolls_back_to_immutable_previous_list(self):
        first = [{"name": "first", "url": "http://first.local:8787/", "label": "A"}]
        second = [{"name": "second", "url": "http://second.local:8787/", "label": "B"}]
        self.install(devices=first)
        old_unit = self.unit.read_bytes()
        old_list = next(self.state.glob("devices-*.json"))
        old_bytes = old_list.read_bytes()
        result = self.install(devices=second)
        self.assertTrue(result["changed"])
        self.assertEqual(Path(result["previous_unit"]).read_bytes(), old_unit)
        lists = list(self.state.glob("devices-*.json"))
        self.assertEqual(len(lists), 2)
        new_list = next(path for path in lists if path != old_list)
        self.assertIn(str(new_list), self.unit.read_text())
        self.assertEqual(json.loads(new_list.read_bytes()), second)
        self.assertEqual(old_list.read_bytes(), old_bytes)
        self.unit.write_bytes(Path(result["previous_unit"]).read_bytes())
        self.assertIn(str(old_list), self.unit.read_text())
        self.assertEqual(web.load_devices(old_list), first)

    def test_identical_list_restores_private_mode_and_refuses_tampering(self):
        devices = [{"name": "first", "url": "http://first.local:8787/"}]
        self.install(devices=devices)
        stored = next(self.state.glob("devices-*.json"))
        stored.chmod(0o644)
        self.assertFalse(self.install(devices=devices)["changed"])
        self.assertEqual(stored.stat().st_mode & 0o777, 0o600)
        stored.write_text("unexpected")
        with self.assertRaises(ValueError):
            self.install(devices=devices)
        self.assertEqual(stored.read_text(), "unexpected")

    def test_symlinked_content_addressed_list_is_refused(self):
        devices = [{"name": "first", "url": "http://first.local:8787/"}]
        self.install(devices=devices)
        stored = next(self.state.glob("devices-*.json"))
        saved = self.state / "saved-list.json"
        stored.rename(saved)
        stored.symlink_to(saved)
        with self.assertRaises(OSError):
            self.install(devices=devices)
        self.assertEqual(json.loads(saved.read_text()),
                         [installer.validate_device(devices[0])])

    def test_upgrade_preserves_legacy_shared_list_for_previous_unit(self):
        first = [{"name": "first", "url": "http://first.local:8787/"}]
        second = [{"name": "second", "url": "http://second.local:8787/"}]
        self.install(devices=first)
        stored = next(self.state.glob("devices-*.json"))
        legacy = self.state / "devices.json"
        legacy.write_bytes(stored.read_bytes())
        self.unit.write_text(self.unit.read_text().replace(str(stored), str(legacy)))
        old_unit = self.unit.read_bytes()
        old_list = legacy.read_bytes()
        result = self.install(auth="none", devices=second)
        self.assertTrue(result["changed"])
        self.assertEqual(Path(result["previous_unit"]).read_bytes(), old_unit)
        self.assertEqual(legacy.read_bytes(), old_list)
        self.assertEqual(web.load_devices(legacy)[0]["name"], "first")


if __name__ == "__main__":
    unittest.main()


class RestoreCommandTests(unittest.TestCase):
    """The rollback the README tells a person to run, run the way it says.

    The supplied tests copied bytes by hand, so the actual entry point was never
    executed: `--host` was required even in restore mode, and following the
    guide stopped the service and then exited with an argument error.
    """

    def setUp(self):
        self.temp = tempfile.TemporaryDirectory(prefix="web-restore-", dir="/tmp/opencode")
        self.addCleanup(self.temp.cleanup)
        self.home = Path(self.temp.name)
        self.unit = self.home / ".config/systemd/user/debra-web.service"

    def install(self, hosts=None, source=SOURCE, **kwargs):
        return installer.install(self.home, source, SINK, "127.0.0.1", 8787,
                                 hosts or ["device.local:8787"], "/usr/bin/python3", **kwargs)

    def run_cli(self, *arguments, home=None):
        environment = dict(os.environ, HOME=str(home or self.home))
        return subprocess.run([sys.executable, "-B", str(SOURCE / "install.py"),
                               *arguments],
                              capture_output=True, text=True, env=environment, timeout=90)

    def upgraded(self):
        first = self.install()
        old_unit = self.unit.read_bytes()
        second = self.install(["other.local:8787"])
        self.assertTrue(second["changed"])
        self.assertNotEqual(self.unit.read_bytes(), old_unit)
        return first, second, old_unit

    def test_the_documented_restore_command_needs_no_host(self):
        # The guide stops the service, then restores. This is that command.
        _, second, old_unit = self.upgraded()
        before = self.unit.stat().st_ino
        result = self.run_cli("--restore", second["previous_unit"])
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertIn("Unit restored", result.stdout)
        self.assertEqual(self.unit.read_bytes(), old_unit)
        self.assertNotEqual(self.unit.stat().st_ino, before,
                            "the unit was written in place, not published by rename")
        self.assertEqual(list(self.unit.parent.glob("*.restore")), [],
                         "a failed restore left its staging file behind")

    def test_installing_without_a_host_is_refused_with_a_reason(self):
        result = self.run_cli("--sink", SINK)
        self.assertEqual(result.returncode, 2)
        self.assertIn("--host", result.stderr)
        self.assertFalse(self.unit.exists())

    def test_a_restore_refuses_a_unit_whose_release_is_gone(self):
        first, second, _ = self.upgraded()
        release = (self.home / ".local/share/debra/web/releases" / first["release"])
        shutil.rmtree(release)
        before = self.unit.read_bytes()
        result = self.run_cli("--restore", second["previous_unit"])
        self.assertEqual(result.returncode, 2)
        self.assertIn("not installed", result.stderr)
        self.assertEqual(self.unit.read_bytes(), before,
                         "a refusal still changed the unit")

    def test_a_restore_refuses_a_commented_out_exec_start(self):
        previous = self.home / "previous.service"
        previous.write_text(installer.MARKER + "[Service]\n# ExecStart=/bin/false\n")
        with self.assertRaisesRegex(ValueError, "no ExecStart line"):
            installer.restore_unit(self.home, previous)
        self.assertFalse(self.unit.exists())

    def test_a_home_with_a_space_percent_and_dollar_restores_its_own_unit(self):
        # The installer writes systemd quoting and escapes `%` and `$` for the
        # same paths restore has to read back. Splitting on whitespace and
        # stripping double quotes looked for `<space-split>/...`,
        # `home%%percent/...` and `home$$dollar/...`, so the documented rollback
        # refused the release the installer itself had just written.
        awkward = tempfile.TemporaryDirectory(prefix="web restore %$100 -", dir="/tmp/opencode")
        self.addCleanup(awkward.cleanup)
        home = Path(awkward.name)
        unit = home / ".config/systemd/user/debra-web.service"
        first = installer.install(home, SOURCE, SINK, "127.0.0.1", 8787,
                                  ["device.local:8787"], "/usr/bin/python3")
        old_unit = unit.read_bytes()
        second = installer.install(home, SOURCE, SINK, "127.0.0.1", 8787,
                                   ["other.local:8787"], "/usr/bin/python3")
        self.assertTrue(second["changed"])
        text = unit.read_text()
        self.assertIn("%%", text)
        self.assertIn("$$", text)
        self.assertIn(" ", text)
        # The unit really names the retained release, and only the decoder says so.
        release = home / ".local/share/debra/web/releases" / first["release"]
        arguments = installer.service_commands(unit.read_bytes())[0]
        self.assertIn(str(release / "server.py"), arguments)
        self.assertIn(str(home / ".config/debra/web"), arguments)
        result = self.run_cli("--restore", second["previous_unit"], home=home)
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertIn("Unit restored", result.stdout)
        self.assertEqual(unit.read_bytes(), old_unit)

    def test_a_rollback_across_two_releases_refuses_a_gone_release(self):
        # The older missing-release test changed only the hostname, so both
        # units named one release and removing it said nothing about the
        # release the *previous* unit names.
        first = self.install()
        second = self.install(source=payload_copy(self.home, changed=True))
        self.assertNotEqual(first["release"], second["release"])
        previous = Path(second["previous_unit"])
        self.assertIn(first["release"], previous.read_text())
        self.assertIn(second["release"], self.unit.read_text())
        releases = self.home / ".local/share/debra/web/releases"
        gone = releases / first["release"]
        gone.rename(gone.with_name(gone.name + ".preserved"))
        before = self.unit.read_bytes()
        result = self.run_cli("--restore", second["previous_unit"])
        self.assertEqual(result.returncode, 2)
        self.assertIn("not installed", result.stderr)
        self.assertEqual(self.unit.read_bytes(), before, "a refusal still changed the unit")
        self.assertTrue((releases / (first["release"] + ".preserved")).is_dir(),
                        "the fixture removed a release instead of preserving it")
        # With the release back, the same command restores the same bytes: the
        # refusal was about the release, not about the unit.
        (releases / (first["release"] + ".preserved")).rename(gone)
        again = self.run_cli("--restore", second["previous_unit"])
        self.assertEqual(again.returncode, 0, again.stderr)
        self.assertEqual(self.unit.read_bytes(), previous.read_bytes())

    def test_a_restore_refuses_an_incomplete_release(self):
        # A release is named by what its installer wrote, so a file removed
        # afterwards changes the digest and the rollback is refused. This used
        # to be caught by a checklist against today's PAYLOAD, which also
        # refused intact older releases that never contained the file - the lab
        # Pi 5 held two of those, and neither `server.py` imported it.
        first = self.install()
        second = self.install(["other.local:8787"])
        release = self.home / ".local/share/debra/web/releases" / first["release"]
        (release / "discovery.py").rename(release / "preserved-discovery.py")
        before = self.unit.read_bytes()
        result = self.run_cli("--restore", second["previous_unit"])
        self.assertEqual(result.returncode, 2)
        self.assertIn("no longer match", result.stderr)
        self.assertEqual(self.unit.read_bytes(), before, "a refusal still changed the unit")
        self.assertTrue((release / "preserved-discovery.py").exists())

    def test_a_restore_refuses_a_release_path_the_installer_does_not_keep(self):
        # Any recognisable `server.py` under `releases/` used to be accepted, so
        # a unit naming a release this installer never wrote restored happily.
        previous = self.home / "previous.service"
        command = " ".join(installer.quoted(part) for part in
                           ("/usr/bin/python3", "-B",
                            "/not/installed/releases/abc/server.py", "serve",
                            "--sink", "s"))
        previous.write_text(installer.MARKER + f"[Service]\nExecStart={command}\n")
        with self.assertRaisesRegex(ValueError, "not a release this installer keeps"):
            installer.restore_unit(self.home, previous)
        self.assertFalse(self.unit.exists())

    def test_a_restore_refuses_a_relative_script(self):
        # `release_problem` used to skip every argument not starting with `/`,
        # so a start command that named no managed entrypoint at all was
        # accepted: there was simply nothing for the release check to inspect.
        # `python3 not-installed/server.py serve` is refused by systemd itself,
        # and restore published it as a successful rollback.
        first = self.install()
        previous = self.home / "previous.service"
        command = " ".join(installer.quoted(part) for part in
                           ("/usr/bin/python3", "-B", "not-installed/server.py", "serve",
                            "--sink", "s"))
        previous.write_text(installer.MARKER + f"[Service]\nExecStart={command}\n")
        before = self.unit.read_bytes()
        with self.assertRaisesRegex(ValueError, "not a release this installer keeps"):
            installer.restore_unit(self.home, previous)
        self.assertEqual(self.unit.read_bytes(), before,
                         "a refusal still changed the unit")
        self.assertTrue((self.home / ".local/share/debra/web/releases"
                         / first["release"]).is_dir(),
                        "the fixture removed the release it should still have")

    def test_a_restore_refuses_a_start_command_that_names_no_release(self):
        # The same hole without a path at all: a marker-bearing unit whose
        # command runs something else entirely. Every argument is relative or an
        # option, so the release check found nothing to check and reported a
        # complete, verified release.
        self.install()
        previous = self.home / "previous.service"
        command = " ".join(installer.quoted(part) for part in
                           ("/usr/bin/python3", "-B", "-c", "print(1)"))
        previous.write_text(installer.MARKER + f"[Service]\nExecStart={command}\n")
        before = self.unit.read_bytes()
        with self.assertRaisesRegex(ValueError, "does not run the server's serve mode"):
            installer.restore_unit(self.home, previous)
        self.assertEqual(self.unit.read_bytes(), before,
                         "a refusal still changed the unit")

    def test_a_restore_refuses_a_unit_without_the_installer_marker(self):
        # Restore is for a snapshot this installer wrote. An arbitrary unit may
        # use systemd syntax the decoder does not reproduce, and accepting it
        # on a best effort is how a wrong path gets validated.
        previous = self.home / "previous.service"
        command = " ".join(installer.quoted(part)
                           for part in ("/usr/bin/python3", "/etc/hosts", "serve"))
        previous.write_text(f"[Service]\nExecStart={command}\n")
        with self.assertRaisesRegex(ValueError, "unit this installer wrote"):
            installer.restore_unit(self.home, previous)
        self.assertFalse(self.unit.exists())

    def test_a_generated_unit_with_a_missing_closing_quote_is_refused(self):
        # The old decoder silently closed an unterminated quote. A unit
        # truncated at its last quote therefore passed the release check and
        # replaced the working unit, contrary to its own docstring.
        self.install()
        text = self.unit.read_text()
        line = next(line for line in text.splitlines() if line.startswith("ExecStart="))
        previous = self.home / "previous.service"
        previous.write_text(text.replace(line, line[:-1], 1))
        before = self.unit.read_bytes()
        with self.assertRaisesRegex(ValueError, "not in the form this installer writes"):
            installer.restore_unit(self.home, previous)
        self.assertEqual(self.unit.read_bytes(), before)

    def test_a_c_escape_is_refused_rather_than_read_as_a_different_path(self):
        # systemd decodes `\x20` to a space. A decoder that leaves the text as
        # `x20` checks a path systemd will not start; the r9 review showed that
        # restore then exited 0 because only the misread release existed.
        previous = self.home / "previous.service"
        command = '"' + "/usr/bin/python3" + '" ' + '"he\\x20home/server.py"'
        previous.write_text(installer.MARKER + f"[Service]\nExecStart={command}\n")
        with self.assertRaisesRegex(ValueError, "not in the form this installer writes"):
            installer.restore_unit(self.home, previous)
        self.assertFalse(self.unit.exists())

    def test_a_restore_refuses_more_than_one_start_command(self):
        # Type=simple runs one ExecStart. The installer writes one, so a unit
        # with two is not a unit it wrote.
        first = self.install()
        release = self.home / ".local/share/debra/web/releases" / first["release"]
        command = " ".join(installer.quoted(part)
                           for part in ("/usr/bin/python3", str(release / "server.py"),
                                        "serve"))
        previous = self.home / "previous.service"
        previous.write_text(installer.MARKER
                            + f"[Service]\nExecStart={command}\nExecStart={command}\n")
        with self.assertRaisesRegex(ValueError, "more than one start command"):
            installer.restore_unit(self.home, previous)

    def test_a_dash_prefixed_start_command_is_checked_without_the_dash(self):
        # `-` means "ignore failure" to systemd, not part of the executable: the
        # old code looked for a file whose path began with a dash and refused a
        # release that was present.
        first = self.install()
        release = self.home / ".local/share/debra/web/releases" / first["release"]
        command = " ".join(installer.quoted(part)
                           for part in ("/usr/bin/python3", "-B",
                                        str(release / "server.py"), "serve",
                                        "--sink", "s"))
        previous = self.home / "previous.service"
        previous.write_text(installer.MARKER + f"[Service]\nExecStart=-{command}\n")
        self.assertEqual(installer.restore_unit(self.home, previous), self.unit)
        self.assertEqual(self.unit.read_bytes(), previous.read_bytes())

    def test_a_restore_refuses_a_release_whose_content_changed(self):
        # The directory name is the digest of its five files. A file edited in
        # place keeps the name and every file present, so only the digest says
        # the restored unit would start different code.
        first = self.install()
        second = self.install(["other.local:8787"])
        release = self.home / ".local/share/debra/web/releases" / first["release"]
        changed = release / "server.py"
        changed.write_bytes(changed.read_bytes() + b"\n# changed\n")
        before = self.unit.read_bytes()
        result = self.run_cli("--restore", second["previous_unit"])
        self.assertEqual(result.returncode, 2)
        self.assertIn("no longer match", result.stderr)
        self.assertEqual(self.unit.read_bytes(), before, "a refusal still changed the unit")

    def test_a_restore_refuses_a_linked_release(self):
        # A release directory that is a link can be repointed after the check;
        # the five files still hash correctly through it.
        first = self.install()
        second = self.install(["other.local:8787"])
        releases = self.home / ".local/share/debra/web/releases"
        release = releases / first["release"]
        preserved = release.with_name(release.name + ".preserved")
        release.rename(preserved)
        release.symlink_to(preserved)
        before = self.unit.read_bytes()
        result = self.run_cli("--restore", second["previous_unit"])
        self.assertEqual(result.returncode, 2)
        self.assertIn("not installed", result.stderr)
        self.assertEqual(self.unit.read_bytes(), before)
        self.assertTrue(release.is_symlink(), "the fixture replaced the release")

    def test_a_restore_refuses_a_linked_payload_file(self):
        # `is_file()` follows a link, so the digest could be satisfied by a
        # copy while the file that starts is somewhere else.
        first = self.install()
        second = self.install(["other.local:8787"])
        release = self.home / ".local/share/debra/web/releases" / first["release"]
        (release / "server.py").rename(release / "server-real.py")
        (release / "server.py").symlink_to(release / "server-real.py")
        before = self.unit.read_bytes()
        result = self.run_cli("--restore", second["previous_unit"])
        self.assertEqual(result.returncode, 2)
        self.assertIn("is a link", result.stderr)
        self.assertEqual(self.unit.read_bytes(), before)

    def test_a_restore_refuses_a_linked_payload_directory(self):
        # The leaf is a real file; its parent is the link. Checking only the
        # leaf proves nothing about the path the service reaches.
        first = self.install()
        second = self.install(["other.local:8787"])
        release = self.home / ".local/share/debra/web/releases" / first["release"]
        (release / "assets").rename(release / "assets-real")
        (release / "assets").symlink_to(release / "assets-real")
        before = self.unit.read_bytes()
        result = self.run_cli("--restore", second["previous_unit"])
        self.assertEqual(result.returncode, 2)
        self.assertIn("is a link", result.stderr)
        self.assertEqual(self.unit.read_bytes(), before)

    def test_a_restore_refuses_a_linked_releases_directory(self):
        # own-02 in the r10 review: the immediate parent check covered `web/`
        # and `releases/`, but renaming `releases` and pointing the name at the
        # preserved copy repoints every release at once, with every byte and
        # digest inside still matching.
        first = self.install()
        second = self.install(["other.local:8787"])
        releases = self.home / ".local/share/debra/web/releases"
        preserved = releases.with_name("releases.preserved")
        releases.rename(preserved)
        releases.symlink_to(preserved)
        before = self.unit.read_bytes()
        result = self.run_cli("--restore", second["previous_unit"])
        self.assertEqual(result.returncode, 2)
        self.assertIn("is a link", result.stderr)
        self.assertEqual(self.unit.read_bytes(), before,
                         "a refusal still changed the unit")
        self.assertTrue((preserved / first["release"]).is_dir(),
                        "the fixture removed the release instead of preserving it")

    def test_a_restore_refuses_a_linked_managed_ancestor(self):
        # own-02's other half: `.local/share` is two levels above `releases`,
        # and installation already refuses a linked ancestor there. Restore
        # checked only `web/` and `releases/`, so the same tree installed and
        # then restored through a link.
        self.install()
        second = self.install(["other.local:8787"])
        share = self.home / ".local/share"
        preserved = share.with_name("share.preserved")
        share.rename(preserved)
        share.symlink_to(preserved)
        before = self.unit.read_bytes()
        result = self.run_cli("--restore", second["previous_unit"])
        self.assertEqual(result.returncode, 2)
        self.assertIn("is a link", result.stderr)
        self.assertEqual(self.unit.read_bytes(), before,
                         "a refusal still changed the unit")

    def test_a_restore_refuses_a_linked_non_entry_payload_file(self):
        # own-07 in the r10 review: the entry file was covered, but the other
        # four payload files were only checked for existence, so a same-content
        # link at `discovery.py` passed every web test.
        first = self.install()
        second = self.install(["other.local:8787"])
        release = self.home / ".local/share/debra/web/releases" / first["release"]
        (release / "discovery.py").rename(release / "discovery-real.py")
        (release / "discovery.py").symlink_to(release / "discovery-real.py")
        before = self.unit.read_bytes()
        result = self.run_cli("--restore", second["previous_unit"])
        self.assertEqual(result.returncode, 2)
        self.assertIn("is a link", result.stderr)
        self.assertEqual(self.unit.read_bytes(), before,
                         "a refusal still changed the unit")

    def rewrite(self, source, mutate):
        """A preserved unit whose start command is `mutate(argv)` of the original."""
        text = Path(source).read_text()
        line = next(line for line in text.splitlines() if line.startswith("ExecStart="))
        argv = mutate(list(installer.service_commands(text.encode())[0]))
        command = " ".join(installer.quoted(part) for part in argv)
        previous = self.home / "previous.service"
        previous.write_text(text.replace(line, f"ExecStart={command}", 1))
        return previous

    def test_a_restore_refuses_a_command_with_no_audio_sink(self):
        # The installed server refuses a missing --sink before it opens a socket
        # ("--sink is required"), so publishing such a unit reported a successful
        # rollback for a service that cannot start.
        _, second, _ = self.upgraded()

        def drop_sink(argv):
            index = argv.index("--sink")
            return argv[:index] + argv[index + 2:]

        previous = self.rewrite(second["previous_unit"], drop_sink)
        before = self.unit.read_bytes()
        result = self.run_cli("--restore", previous)
        self.assertEqual(result.returncode, 2)
        self.assertIn("names no audio sink", result.stderr)
        self.assertEqual(self.unit.read_bytes(), before,
                         "a refusal still changed the unit")

    def test_a_restore_refuses_an_auth_mode_the_server_does_not_have(self):
        _, second, _ = self.upgraded()

        def bad_auth(argv):
            argv[argv.index("--auth") + 1] = "invalid"
            return argv

        previous = self.rewrite(second["previous_unit"], bad_auth)
        before = self.unit.read_bytes()
        result = self.run_cli("--restore", previous)
        self.assertEqual(result.returncode, 2)
        self.assertIn("not a mode the installed server accepts", result.stderr)
        self.assertEqual(self.unit.read_bytes(), before,
                         "a refusal still changed the unit")

    def test_a_restore_refuses_a_non_server_payload_entrypoint(self):
        # The entry point must be `server.py`, not merely "one of the five
        # payload files". `discovery.py` defines functions and serves nothing, so
        # a unit that ran it would be published as a working rollback and start
        # no listener at all.
        first, second, _ = self.upgraded()
        release = self.home / ".local/share/debra/web/releases" / first["release"]

        def use_discovery(argv):
            argv[2] = str(release / "discovery.py")
            return argv

        previous = self.rewrite(second["previous_unit"], use_discovery)
        before = self.unit.read_bytes()
        result = self.run_cli("--restore", previous)
        self.assertEqual(result.returncode, 2)
        self.assertIn("not the server.py of a release", result.stderr)
        self.assertEqual(self.unit.read_bytes(), before,
                         "a refusal still changed the unit")

    def test_a_restore_refuses_a_start_command_that_is_not_the_installed_shape(self):
        # The command line itself is checked, not only the paths that happen to
        # appear in it. Each of these is a unit this installer never writes.
        release = "/home/x/.local/share/debra/web/releases/abc/server.py"
        refusals = {
            "too short": ["/usr/bin/python3", "-B", release],
            "relative interpreter": ["python3", "-B", release, "serve"],
            "no -B": ["/usr/bin/python3", release, "serve", "x"],
            "no serve": ["/usr/bin/python3", "-B", release, "run"],
            "unknown option": ["/usr/bin/python3", "-B", release, "serve", "--exec", "sh"],
            "option without value": ["/usr/bin/python3", "-B", release, "serve", "--port"],
            "relative state directory": ["/usr/bin/python3", "-B", release, "serve",
                                         "--state-dir", "state"],
            "no sink": ["/usr/bin/python3", "-B", release, "serve", "--auth", "key"],
            "empty sink": ["/usr/bin/python3", "-B", release, "serve", "--sink", ""],
            "unknown auth": ["/usr/bin/python3", "-B", release, "serve",
                             "--sink", "s", "--auth", "open"],
            "unprivileged port": ["/usr/bin/python3", "-B", release, "serve",
                                  "--sink", "s", "--port", "80"],
            "non-numeric port": ["/usr/bin/python3", "-B", release, "serve",
                                 "--sink", "s", "--port", "http"],
            "malformed host": ["/usr/bin/python3", "-B", release, "serve",
                               "--sink", "s", "--host", "not-a-host"],
        }
        for name, argv in refusals.items():
            with self.subTest(name):
                self.assertIsNotNone(installer.start_command_problem(argv),
                                     f"{name} was accepted as the installed shape")
        written = ["/usr/bin/python3", "-B", release, "serve",
                   "--state-dir", "/home/x/.config/debra/web", "--bind", "0.0.0.0",
                   "--port", "8787", "--sink", "s", "--auth", "key",
                   "--host", "device.local:8787", "--host", "other.local:8787"]
        self.assertIsNone(installer.start_command_problem(written))

    def test_a_restore_refuses_an_entrypoint_that_is_not_payload(self):
        # The five files hash correctly, so the release check passes, while the
        # unit starts a different script that is not covered by that digest.
        first = self.install()
        second = self.install(["other.local:8787"])
        release = self.home / ".local/share/debra/web/releases" / first["release"]
        (release / "helper.sh").write_text("#!/bin/sh\nexit 0\n")
        previous = self.home / "previous.service"
        command = " ".join(installer.quoted(part)
                           for part in ("/usr/bin/python3", "-B",
                                        str(release / "helper.sh"), "serve",
                                        "--sink", "s"))
        # Keep the release the retained unit names, so completeness alone would
        # not refuse it.
        retained = second["previous_unit"]
        text = Path(retained).read_text()
        line = next(line for line in text.splitlines() if line.startswith("ExecStart="))
        previous.write_text(text.replace(line, f"ExecStart={command}", 1))
        with self.assertRaisesRegex(ValueError, "not the server.py of a release"):
            installer.restore_unit(self.home, previous)

    def test_a_restore_refuses_a_traversing_entrypoint(self):
        # `relative_to()` is lexical: `releases/<id>/../elsewhere.py` is inside
        # the releases spelling and outside the release it names.
        first = self.install()
        releases = self.home / ".local/share/debra/web/releases"
        (releases / "elsewhere.py").write_text("print('not in a release')\n")
        previous = self.home / "previous.service"
        command = " ".join(installer.quoted(part)
                           for part in ("/usr/bin/python3", "-B",
                                        str(releases / first["release"] / ".." / "elsewhere.py"),
                                        "serve", "--sink", "s"))
        previous.write_text(installer.MARKER + f"[Service]\nExecStart={command}\n")
        with self.assertRaisesRegex(ValueError, "leaves the release"):
            installer.restore_unit(self.home, previous)

    def test_the_unit_is_never_absent_while_being_replaced(self):
        # Renaming the current unit aside before the rename leaves a window in
        # which neither version is loadable. The final bytes are identical, so
        # only interception at the publication can see it.
        first, second, _ = self.upgraded()
        seen = []
        real_replace = installer.os.replace

        def watching(source, destination):
            seen.append(Path(destination).exists())
            return real_replace(source, destination)

        with patch.object(installer.os, "replace", watching):
            installer.restore_unit(self.home, second["previous_unit"])
        self.assertEqual(seen, [True],
                         "the unit was absent when the new file was published")

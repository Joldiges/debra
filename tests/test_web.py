"""Offline web/installer checks. Commands and audio are fakes; HTTP is loopback."""

import http.client
from contextlib import contextmanager, redirect_stdout
import importlib.util
from io import StringIO
import json
import os
from pathlib import Path
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
        self.assertEqual(json.loads(raw)["devices"], self.devices)


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
        self.assertEqual(data["devices"], self.configured + [
            {"name": "new", "url": "http://new.local:8787/", "label": "Kitchen",
             "source": "discovered"}])
        self.assertEqual(self.request("/api/status")[0], 401)

    def test_duplicate_configured_urls_appear_once(self):
        self.server.devices = (*self.configured, dict(self.configured[0], label="Duplicate"))
        self.assertEqual(self.request("/api/devices"), (200, {"devices": self.configured}))

    def test_invalid_discovered_hosts_ports_names_and_labels_are_dropped(self):
        records = [
            {"name": "badhost", "url": "http://bad-.local:8787/", "label": ""},
            {"name": "badport", "url": "http://okay.local:65536/", "label": ""},
            {"name": "bad name", "url": "http://okay.local:8787/", "label": ""},
            {"name": "badlabel", "url": "http://okay.local:8787/", "label": "x" * 81},
            {"name": "good", "url": "http://okay.local:8787/"},
            None,
        ]
        self.scan(records)
        self.assertEqual(self.request("/api/devices")[1]["devices"], self.configured + [
            {"name": "good", "url": "http://okay.local:8787/", "label": "",
             "source": "discovered"}])

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
                self.assertEqual(self.request("/api/devices"), (200, {"devices": self.configured}))

    def test_missing_avahi_clears_cache_using_default_browser(self):
        self.scan([{"name": "old", "url": "http://old.local:8787/", "label": "Old"}])
        self.cache.browse = web.DiscoveryCache().browse
        with patch.object(discovery.subprocess, "run", side_effect=FileNotFoundError()):
            self.cache.scan()
        self.assertEqual(self.request("/api/devices"), (200, {"devices": self.configured}))

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
        self.assertEqual(self.request("/api/devices"), (200, {"devices": self.configured}))
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
        def changed_parse(output):
            records = original_parse(output)
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
        self.assertEqual(self.request("/api/devices")[1]["devices"], self.configured + [
            {"name": "debra-1", "url": "http://debra.local:8787/",
             "label": "Changed parser", "source": "discovered"}])
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
        self.assertEqual(self.request("/api/devices")[1]["devices"], self.configured + [
            {"name": "self", "url": "http://self.local:8787/", "label": "Debra self",
             "source": "discovered"}])

    def test_serve_starts_discovery_without_waiting_for_a_request(self):
        with tempfile.TemporaryDirectory(prefix="web-start-", dir="/tmp/opencode") as temp:
            argv = ["server.py", "serve", "--state-dir", temp, "--sink", SINK, "--auth", "none"]
            with patch.object(sys, "argv", argv), patch.object(web, "DiscoveryCache") as cache, \
                    patch.object(web, "Server") as server, patch("builtins.print"):
                web.main()
        cache.return_value.start.assert_called_once_with()
        self.assertIs(server.call_args.args[5], cache.return_value)
        server.return_value.__enter__.return_value.serve_forever.assert_called_once_with()

    def test_worker_start_failure_leaves_configured_links_available(self):
        with patch.object(threading.Thread, "start", side_effect=RuntimeError("no threads")):
            self.cache.start()
        self.assertIsNone(self.cache.thread)
        self.assertEqual(self.request("/api/devices"), (200, {"devices": self.configured}))


class InstallerTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory(prefix="web-install-", dir="/tmp/opencode")
        self.addCleanup(self.temp.cleanup)
        self.home = Path(self.temp.name)
        self.state = self.home / ".config/debra/web"
        self.unit = self.home / ".config/systemd/user/debra-web.service"

    def install(self, hosts=None, **kwargs):
        return installer.install(self.home, SOURCE, SINK, "127.0.0.1", 8787,
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
        self.state.mkdir(parents=True, mode=0o755)
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
            self.assertEqual((status, body), (200, {"devices": configured}))
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

    def test_systemd_quoting(self):
        self.assertEqual(installer.quoted('a % " \\'), '"a %% \\" \\\\"')
        self.assertEqual(installer.quoted("$HOME"), '"$$HOME"')
        with self.assertRaises(ValueError):
            installer.quoted("arg\nExecStart=bad")

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
        self.assertEqual(json.loads(saved.read_text()), devices)

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

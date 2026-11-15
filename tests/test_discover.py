"""Offline tests for shared discovery. Synthetic avahi output only: no network,
no avahi daemon, no device. The parser is the part worth testing; the browse
call is stubbed."""

import json
import os
import subprocess
import sys
import tempfile
import unittest
from contextlib import redirect_stdout
from io import StringIO
from pathlib import Path
from unittest import mock

SOURCE = Path(__file__).resolve().parent.parent
if str(SOURCE) not in sys.path:
    sys.path.insert(0, str(SOURCE))

from control.web import discovery as discover  # noqa: E402
from tools import discover as cli  # noqa: E402

RESOLVED = (
    '=;eth0;IPv4;Debra debra-3c6b3f;_debra._tcp;local;debra-3c6b3f.local;192.168.0.8;8787;'
    '"name=debra-3c6b3f" "label=Lab Pi 5"'
)


class ParseTests(unittest.TestCase):
    def test_one_record_across_interfaces(self):
        text = "\n".join([
            "+;eth0;IPv4;Debra debra-3c6b3f;_debra._tcp;local",
            RESOLVED,
            RESOLVED.replace("eth0", "wlp1s0"),
        ])
        records = discover.parse(text)
        self.assertEqual(len(records), 1)
        self.assertEqual(records[0]["name"], "debra-3c6b3f")
        self.assertEqual(records[0]["label"], "Lab Pi 5")
        self.assertEqual(records[0]["url"], "http://debra-3c6b3f.local:8787/")
        self.assertEqual(records[0]["addresses"], ["192.168.0.8"])

    def test_missing_txt_falls_back_to_the_instance_name(self):
        line = '=;eth0;IPv4;debra-ab;_debra._tcp;local;ab.local;10.0.0.2;8787;'
        records = discover.parse(line)
        self.assertEqual(records[0]["name"], "debra-ab")
        self.assertEqual(records[0]["label"], "debra-ab")

    def test_rejects_hosts_ports_and_services_that_are_not_plain_debra(self):
        bad = [
            '=;eth0;IPv4;x;_debra._tcp;local;evil.example.com;1.2.3.4;8787;',
            '=;eth0;IPv4;x;_debra._tcp;local;ok.local;1.2.3.4;99999;',
            '=;eth0;IPv4;x;_debra._tcp;local;ok.local;1.2.3.4;0;',
            '=;eth0;IPv4;x;_http._tcp;local;ok.local;1.2.3.4;80;',
            '=;eth0;IPv4;x;_debra._tcp;local;ok.local;1.2.3.4;8787',
            'not an avahi line',
        ]
        with self.assertLogs(discover.LOGGER, level="WARNING"):
            self.assertEqual(discover.parse("\n".join(bad)), [])

    def test_sorted_by_name(self):
        text = "\n".join([
            '=;eth0;IPv4;b;_debra._tcp;local;b.local;10.0.0.2;8787;"name=bbb"',
            '=;eth0;IPv4;a;_debra._tcp;local;a.local;10.0.0.1;8787;"name=aaa"',
        ])
        self.assertEqual([r["name"] for r in discover.parse(text)], ["aaa", "bbb"])

    def test_device_list_matches_the_configured_record_shape(self):
        # Exercise the real adapter, browse wrapper and parser, not a comprehension
        # in this test that builds exactly the shape it then asserts.
        with mock.patch.object(discover.subprocess, "run", return_value=
                               subprocess.CompletedProcess([], 0, RESOLVED, "")):
            devices = cli.device_list()
        self.assertEqual(devices, [{"name": "debra-3c6b3f", "label": "Lab Pi 5",
                                    "url": "http://debra-3c6b3f.local:8787/"}])

    def test_acceptance_returns_specific_drop_reasons(self):
        good = {"name": "debra", "url": "http://debra.local:8787/", "label": "Lab"}
        cases = [
            (None, "must be an object"),
            ({"name": "debra"}, "missing url"),
            ({"url": good["url"]}, "missing name"),
            (dict(good, name="x" * 65), "1-64"),
            (dict(good, name="bad name"), "1-64"),
            (dict(good, label="x" * 81), "up to 80"),
            (dict(good, label=None), "up to 80"),
            (dict(good, url="http://debra.local:80/"), "Port 80"),
            (dict(good, url="http://debra.example:8787/"), "must end with .local"),
            (dict(good, url="http://192.0.2.1:8787/"), "must end with .local"),
            (dict(good, url="http://bad-.local:8787/"), "Invalid host or port"),
            (dict(good, url="http://debra.local:0/"), "Invalid host or port"),
            (dict(good, url="http://debra.local:65536/"), "Invalid host or port"),
            (dict(good, url="http://debra.local:no/"), "Expected http://host:port/"),
            (dict(good, url="https://debra.local:8787/"), "Expected http://host:port/"),
            (dict(good, url="x" * 201), "up to 200"),
        ]
        for record, expected in cases:
            with self.subTest(record=record):
                entry, reason = discover.accept_record(record)
                self.assertIsNone(entry)
                self.assertIn(expected, reason)
        entry, reason = discover.accept_record(dict(good, url="HTTP://DEBRA.LOCAL:08787"))
        self.assertEqual((entry, reason), (good, None))

    def test_parser_applies_acceptance_before_interface_coalescing(self):
        # A rejected interface must not suppress a later acceptable announcement.
        bad = RESOLVED.replace('"name=debra-3c6b3f"', '"name=' + "x" * 65 + '"')
        with self.assertLogs(discover.LOGGER, level="WARNING") as logs:
            records = discover.parse(bad + "\n" + RESOLVED)
        self.assertEqual([r["name"] for r in records], ["debra-3c6b3f"])
        self.assertIn("1-64", logs.output[0])


class BrowseTests(unittest.TestCase):
    def run_browse(self, **kwargs):
        with mock.patch.object(subprocess, "run", **kwargs):
            return discover.browse()

    def test_missing_binary_is_a_reason_not_an_exception(self):
        result = self.run_browse(side_effect=FileNotFoundError())
        self.assertEqual(result["devices"], [])
        self.assertIn("not installed", result["error"])

    def test_timeout_is_reported(self):
        result = self.run_browse(side_effect=subprocess.TimeoutExpired("avahi-browse", 8))
        self.assertIn("timed out", result["error"])

    def test_failed_exit_is_reported(self):
        result = self.run_browse(return_value=subprocess.CompletedProcess([], 2, "", ""))
        self.assertIn("exited 2", result["error"])

    def test_success_returns_records(self):
        result = self.run_browse(return_value=subprocess.CompletedProcess([], 0, RESOLVED, ""))
        self.assertIsNone(result["error"])
        self.assertEqual(len(result["devices"]), 1)

    def test_command_is_read_only_and_bounded(self):
        with mock.patch.object(subprocess, "run",
                               return_value=subprocess.CompletedProcess([], 0, "", "")) as run:
            discover.browse()
        argv = run.call_args.args[0]
        self.assertEqual(argv[0], "avahi-browse")
        self.assertIn("-t", argv)
        self.assertEqual(argv[-1], discover.SERVICE)
        self.assertEqual(run.call_args.kwargs["timeout"], 8)


class CliTests(unittest.TestCase):
    def test_cli_reports_dropped_records_on_stderr_in_both_output_modes(self):
        # A fake executable supplies avahi -rtp text to the actual CLI process;
        # no daemon, multicast scan, HTTP device or audio command is used.
        text = "\n".join([RESOLVED, RESOLVED.replace(";8787;", ";80;")])
        with tempfile.TemporaryDirectory(prefix="discover-cli-", dir="/tmp/opencode") as temp:
            avahi = Path(temp) / "avahi-browse"
            avahi.write_text(f"#!{sys.executable}\nprint({text!r})\n")
            avahi.chmod(0o700)
            for args in ([], ["--json"]):
                with self.subTest(args=args):
                    result = subprocess.run(
                        [sys.executable, "-B", str(SOURCE / "tools/discover.py"), *args],
                        env=dict(os.environ, PATH=temp), capture_output=True, text=True, timeout=5)
                    self.assertEqual(result.returncode, 0, result.stderr)
                    self.assertIn("Dropped discovery record", result.stderr)
                    self.assertIn("Port 80 is unsupported", result.stderr)
                    self.assertNotIn("Dropped", result.stdout)
                    if args:
                        records = json.loads(result.stdout)["devices"]
                        self.assertEqual([r["url"] for r in records],
                                         ["http://debra-3c6b3f.local:8787/"])
                    else:
                        self.assertIn("http://debra-3c6b3f.local:8787/", result.stdout)

    def run_cli(self, result, args=()):
        output = StringIO()
        with mock.patch.object(discover, "browse", return_value=result), redirect_stdout(output):
            code = cli.main(list(args))
        return code, output.getvalue()

    def test_error_empty_and_json_exit_codes_and_output(self):
        error = {"devices": [], "error": "avahi-browse is not installed"}
        self.assertEqual(self.run_cli(error), (1, "Discovery unavailable: avahi-browse is not installed\n"))
        self.assertEqual(self.run_cli(error, ["--json"]),
                         (0, '{\n "devices": [],\n "error": "avahi-browse is not installed"\n}\n'))
        self.assertEqual(self.run_cli({"devices": [], "error": None}),
                         (0, "No _debra._tcp service found. Is the device advertising?\n"))

    def test_table_and_device_list(self):
        result = {"devices": discover.parse(RESOLVED), "error": None}
        code, output = self.run_cli(result)
        self.assertEqual(code, 0)
        self.assertEqual(output,
                         f"{'Name':22s} {'Label':28s} {'URL':34s} Address\n"
                         f"{'debra-3c6b3f':22s} {'Lab Pi 5':28s} "
                         f"{'http://debra-3c6b3f.local:8787/':34s} 192.168.0.8\n")
        with mock.patch.object(discover, "browse", return_value=result):
            self.assertEqual(cli.device_list(), [{"name": "debra-3c6b3f", "label": "Lab Pi 5",
                                                   "url": "http://debra-3c6b3f.local:8787/"}])


if __name__ == "__main__":
    unittest.main()

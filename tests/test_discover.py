"""Offline tests for tools/discover.py. Synthetic avahi output only: no network,
no avahi daemon, no device. The parser is the part worth testing; the browse
call is stubbed."""

import subprocess
import sys
import unittest
from pathlib import Path
from unittest import mock

SOURCE = Path(__file__).resolve().parent.parent
if str(SOURCE) not in sys.path:
    sys.path.insert(0, str(SOURCE))

import tools.discover as discover  # noqa: E402

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
        line = '=;eth0;IPv4;Debra ab;_debra._tcp;local;ab.local;10.0.0.2;8787;'
        records = discover.parse(line)
        self.assertEqual(records[0]["name"], "Debra ab")
        self.assertEqual(records[0]["label"], "Debra ab")

    def test_rejects_hosts_ports_and_services_that_are_not_plain_debra(self):
        bad = [
            '=;eth0;IPv4;x;_debra._tcp;local;evil.example.com;1.2.3.4;8787;',
            '=;eth0;IPv4;x;_debra._tcp;local;ok.local;1.2.3.4;99999;',
            '=;eth0;IPv4;x;_debra._tcp;local;ok.local;1.2.3.4;0;',
            '=;eth0;IPv4;x;_http._tcp;local;ok.local;1.2.3.4;80;',
            '=;eth0;IPv4;x;_debra._tcp;local;ok.local;1.2.3.4;8787',
            'not an avahi line',
        ]
        self.assertEqual(discover.parse("\n".join(bad)), [])

    def test_sorted_by_name(self):
        text = "\n".join([
            '=;eth0;IPv4;b;_debra._tcp;local;b.local;10.0.0.2;8787;"name=bbb"',
            '=;eth0;IPv4;a;_debra._tcp;local;a.local;10.0.0.1;8787;"name=aaa"',
        ])
        self.assertEqual([r["name"] for r in discover.parse(text)], ["aaa", "bbb"])

    def test_device_list_matches_the_configured_record_shape(self):
        devices = [{"name": r["name"], "url": r["url"], "label": r["label"]}
                   for r in discover.parse(RESOLVED)]
        self.assertEqual(set(devices[0]), {"name", "url", "label"})


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
        self.assertEqual(run.call_args.kwargs["timeout"], discover.BROWSE_TIMEOUT_S)


if __name__ == "__main__":
    unittest.main()

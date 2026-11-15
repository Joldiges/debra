"""Offline checks for the device audio self-test's arithmetic and failure path.

The self-test itself runs on a Pi with a HAT and is never imported by a host
test for its side effects. What a host *can* check is its reporting: a dead
capture is the case the tool exists to detect, and it used to print -Infinity,
which is not valid JSON and so breaks anything that later reads the report.
The failure path is checked with faked subprocesses, so no device is touched:
the point of the test is that a failed capture still restores the mixer and
still reports why it failed.
"""

import contextlib
import importlib.util
import io
import json
import math
from pathlib import Path
import sys
import tempfile
import types
import unittest

SOURCE = Path(__file__).resolve().parent.parent


def load():
    """Import tools/audio_selftest.py by path; it is a script, not a package."""
    spec = importlib.util.spec_from_file_location(
        "debra_audio_selftest", SOURCE / "tools" / "audio_selftest.py")
    module = importlib.util.module_from_spec(spec)
    saved = sys.argv
    sys.argv = [saved[0]]
    try:
        spec.loader.exec_module(module)
    finally:
        sys.argv = saved
    return module


def completed(returncode=0, stdout="", stderr=""):
    return types.SimpleNamespace(returncode=returncode, stdout=stdout, stderr=stderr)


class DecibelReportTests(unittest.TestCase):
    def setUp(self):
        self.module = load()

    def test_silence_reports_a_finite_floor_not_an_infinity(self):
        value = self.module.dbfs(0)
        self.assertTrue(math.isfinite(value), "a dead capture must be a finite number")
        self.assertEqual(value, -120.0)

    def test_a_report_containing_silence_is_strict_json(self):
        # allow_nan=False is what a strict reader does; -Infinity would raise here.
        text = json.dumps({"floor": self.module.dbfs(0)}, allow_nan=False)
        self.assertEqual(json.loads(text)["floor"], -120.0)

    def test_full_scale_is_zero_dbfs(self):
        self.assertAlmostEqual(self.module.dbfs(32768.0), 0.0, places=6)


class FailurePathTests(unittest.TestCase):
    """A broken capture must not leave the codec at the test settings."""

    def setUp(self):
        self.module = load()
        self.temp = tempfile.TemporaryDirectory(prefix="selftest-", dir="/tmp/opencode")
        self.addCleanup(self.temp.cleanup)
        self.cwd = Path.cwd()
        self.addCleanup(lambda: __import__("os").chdir(self.cwd))

        module = self.module
        self.commands = []
        module.WORK = self.temp.name
        module.STATE = str(Path(self.temp.name) / "pre.state")
        module.card_index = lambda: 0

        def fake_run(cmd, timeout=30):
            self.commands.append(list(cmd))
            return completed()

        module.run = fake_run
        module.amixer = lambda *args: fake_run(["amixer", "-c", module.CARD, *args])

        def broken_record(path, seconds):
            raise RuntimeError("arecord failed")

        module.record = broken_record

    def test_a_failed_capture_restores_the_mixer_and_explains_itself(self):
        output = io.StringIO()
        with contextlib.redirect_stdout(output):
            code = self.module.main()

        self.assertEqual(code, 1)
        report = json.loads(output.getvalue())  # strict-valid JSON, no -Infinity
        self.assertFalse(report["verdict"]["run_complete"])
        self.assertIn("RuntimeError: arecord failed", report["error"])
        self.assertIn("RuntimeError: arecord failed", report["traceback"])
        # The store happens before the mixer is touched and the restore after
        # the failure; the restore is the reason the finally block exists.
        alsactl = [cmd for cmd in self.commands if cmd[0] == self.module.ALSACTL]
        self.assertEqual([cmd[3] for cmd in alsactl], ["store", "restore"])
        self.assertEqual(report["steps"]["mixer_restore"]["rc"], 0)

    def test_a_missing_card_is_a_complete_report_too(self):
        self.module.card_index = lambda: None
        output = io.StringIO()
        with contextlib.redirect_stdout(output):
            code = self.module.main()

        self.assertEqual(code, 1)
        report = json.loads(output.getvalue())
        self.assertFalse(report["verdict"]["card_present"])
        self.assertFalse(report["verdict"]["run_complete"])
        self.assertFalse([cmd for cmd in self.commands if cmd[0] == self.module.ALSACTL],
                         "nothing should be stored or restored when there is no card")


if __name__ == "__main__":
    unittest.main()

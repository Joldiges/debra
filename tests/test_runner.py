"""Offline regression checks for runner errors and path boundaries."""

import contextlib
import io
import tempfile
import unittest
from pathlib import Path
from unittest import mock

from tools import scheduled_runner as runner


class RunnerSafetyTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory(prefix="runner-", dir="/tmp/opencode")
        self.addCleanup(self.temp.cleanup)
        root = Path(self.temp.name)
        paths = {"RUNNER_DIR": root, "RUNS_DIR": root / "runs",
                 "CONFIG_PATH": root / "config.json", "QUEUE_PATH": root / "queue.json",
                 "STATE_PATH": root / "state.json", "STOP_PATH": root / "STOP",
                 "LOCK_PATH": root / "run.lock"}
        for name, value in paths.items():
            patch = mock.patch.object(runner, name, value)
            patch.start()
            self.addCleanup(patch.stop)
        runner.ensure_layout()

    def test_bad_json_is_reported_without_traceback(self):
        runner.QUEUE_PATH.write_text("{")
        err = io.StringIO()
        with contextlib.redirect_stderr(err):
            result = runner.main(["status"])
        self.assertNotEqual(result, 0)
        self.assertIn("unavailable", err.getvalue())
        self.assertIn("JSONDecodeError", err.getvalue())
        self.assertNotIn("Traceback", err.getvalue())

    def test_task_id_cannot_escape_runner_directory(self):
        err = io.StringIO()
        with contextlib.redirect_stderr(err):
            result = runner.main(["add", "--id", "../outside", "--prompt", "x" * 50])
        self.assertNotEqual(result, 0)
        self.assertIn("invalid task id", err.getvalue())
        self.assertEqual(runner._read_json(runner.QUEUE_PATH, {})["tasks"], [])

    def test_filesystem_error_is_reported_without_traceback(self):
        err = io.StringIO()
        with mock.patch.object(runner, "_read_json", side_effect=PermissionError("denied")), \
             contextlib.redirect_stderr(err):
            result = runner.main(["status"])
        self.assertEqual(result, 1)
        self.assertIn("runner unavailable (PermissionError)", err.getvalue())
        self.assertNotIn("Traceback", err.getvalue())


if __name__ == "__main__":
    unittest.main()

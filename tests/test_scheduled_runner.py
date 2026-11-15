"""Offline tests for tools/scheduled_runner.py.

These exercise queue/budget/lock/prompt logic only. They never start a model
call and never touch the real .local/runner tree.
"""

import json
import sys
import tempfile
import unittest
from pathlib import Path
from unittest import mock

SOURCE = Path(__file__).resolve().parent.parent
if str(SOURCE) not in sys.path:
    sys.path.insert(0, str(SOURCE))

import tools.scheduled_runner as runner  # noqa: E402  (path set above)


class RunnerStateTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.root = Path(self.tmp.name)
        self.patches = [
            mock.patch.object(runner, "RUNNER_DIR", self.root),
            mock.patch.object(runner, "QUEUE_PATH", self.root / "queue.json"),
            mock.patch.object(runner, "STATE_PATH", self.root / "state.json"),
            mock.patch.object(runner, "CONFIG_PATH", self.root / "config.json"),
            mock.patch.object(runner, "STOP_PATH", self.root / "STOP"),
            mock.patch.object(runner, "LOCK_PATH", self.root / "run.lock"),
            mock.patch.object(runner, "RUNS_DIR", self.root / "runs"),
        ]
        for patch in self.patches:
            patch.start()
        runner.ensure_layout()

    def tearDown(self):
        for patch in reversed(self.patches):
            patch.stop()
        self.tmp.cleanup()

    def test_ensure_layout_creates_defaults(self):
        config = json.loads((self.root / "config.json").read_text())
        self.assertIn("daily_budget_usd", config)
        self.assertEqual(json.loads((self.root / "queue.json").read_text())["tasks"], [])

    def test_add_rejects_duplicate_and_short_prompt(self):
        good = "Investigate a specific public question and report sources for every claim made."
        with mock.patch("sys.stdout"):
            self.assertEqual(runner.main(["add", "--id", "T1", "--prompt", good]), 0)
            self.assertEqual(runner.main(["add", "--id", "T1", "--prompt", good]), 2)
            self.assertEqual(runner.main(["add", "--id", "T2", "--prompt", "too short"]), 2)
        queue = json.loads((self.root / "queue.json").read_text())
        self.assertEqual([t["id"] for t in queue["tasks"]], ["T1"])

    def test_next_pending_skips_finished_tasks(self):
        queue = {"tasks": [
            {"id": "a", "status": "done"},
            {"id": "b", "status": "pending"},
            {"id": "c", "status": "pending"},
        ]}
        self.assertEqual(runner.next_pending(queue)["id"], "b")
        self.assertIsNone(runner.next_pending({"tasks": [{"id": "a", "status": "failed"}]}))

    def test_budget_accounting(self):
        state = {"days": {"2026-11-15": {"tasks": 2, "cost_usd": 0.5}}, "tasks": {}}
        config = {"daily_budget_usd": 1.5}
        self.assertAlmostEqual(runner.spent_today(state, "2026-11-15"), 0.5)
        self.assertAlmostEqual(runner.budget_remaining(state, config, "2026-11-15"), 1.0)
        self.assertAlmostEqual(runner.budget_remaining(state, config, "2026-11-16"), 1.5)

    def test_null_budget_means_no_local_cap(self):
        state = {"days": {"2026-11-15": {"tasks": 9, "cost_usd": 42.0}}, "tasks": {}}
        self.assertEqual(runner.budget_remaining(state, {"daily_budget_usd": None}), float("inf"))

    def test_lock_is_exclusive_and_stale_lock_is_reclaimed(self):
        self.assertTrue(runner.acquire_lock())
        self.assertFalse(runner.acquire_lock())
        runner.release_lock()
        (self.root / "run.lock").write_text(json.dumps({"pid": 999999, "started": "x"}))
        self.assertTrue(runner.acquire_lock())
        runner.release_lock()

    def test_stop_file_prevents_runs(self):
        (self.root / "STOP").write_text("")
        with mock.patch("sys.stdout"):
            self.assertEqual(runner.main(["run", "--once"]), 0)

    def test_prompt_always_carries_guardrails(self):
        prompt = runner.build_prompt({"prompt": "Do the thing."})
        self.assertTrue(prompt.startswith("Do the thing."))
        self.assertIn("upstream-documented", prompt)
        self.assertIn("Never place a password", prompt)
        self.assertIn("Do not delete files", prompt)

    def test_dry_run_does_not_write_state(self):
        with mock.patch("sys.stdout"):
            runner.main(["add", "--id", "D1", "--prompt",
                         "Answer one bounded public documentation question with citations."])
            before = (self.root / "queue.json").read_text()
            self.assertEqual(runner.main(["run", "--once", "--dry-run"]), 0)
            self.assertEqual((self.root / "queue.json").read_text(), before)


if __name__ == "__main__":
    unittest.main()

"""Offline tests of deterministic refill and its interaction with a run."""

import contextlib
import io
import json
import tempfile
import unittest
from pathlib import Path
from unittest import mock

from tools import scheduled_runner as runner


SCOPE = "Investigate one specific public question and report the source and its limitations."


class RefillTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory(prefix="refill-", dir="/tmp/opencode")
        self.addCleanup(self.temp.cleanup)
        root = Path(self.temp.name)
        paths = {"RUNNER_DIR": root / "state", "RUNS_DIR": root / "state/runs",
                 "CONFIG_PATH": root / "state/config.json", "QUEUE_PATH": root / "state/queue.json",
                 "STATE_PATH": root / "state/state.json", "STOP_PATH": root / "state/STOP",
                 "LOCK_PATH": root / "state/run.lock", "BACKLOG_PATH": root / "backlog.md"}
        for name, value in paths.items():
            patch = mock.patch.object(runner, name, value)
            patch.start()
            self.addCleanup(patch.stop)
        runner.ensure_layout()
        self.backlog([f"A | ready | First | {SCOPE}",
                      f"B | ready | Second | {SCOPE}",
                      f"C | ready | Third | {SCOPE}",
                      f"D | ready | Fourth | {SCOPE}",
                      f"E | not-ready | Human | {SCOPE}"])

    def backlog(self, lines):
        runner.BACKLOG_PATH.write_text("# Research\n```debra-research-backlog\n" +
                                       "\n".join(lines) + "\n```\n")

    def queue(self):
        return json.loads(runner.QUEUE_PATH.read_text())

    def put_tasks(self, tasks):
        runner._write_json(runner.QUEUE_PATH, {"version": 1, "tasks": tasks})

    def call(self, *args):
        out, err = io.StringIO(), io.StringIO()
        with contextlib.redirect_stdout(out), contextlib.redirect_stderr(err):
            result = runner.main(list(args))
        return result, out.getvalue(), err.getvalue()

    def test_threshold_verbatim_and_idempotent_including_finished_ids(self):
        self.put_tasks([{"id": "A", "status": "done", "prompt": "original"},
                        {"id": "X", "status": "pending", "prompt": "existing"},
                        {"id": "Y", "status": "failed"}])
        rc, out, _ = self.call("refill", "--min-pending", "3")
        self.assertEqual(rc, 0)
        self.assertIn("skipped A (line 3): already in queue", out)
        self.assertIn("added B: Second", out)
        self.assertIn("added C: Third", out)
        self.assertIn("skipped D (line 6): threshold met", out)
        self.assertIn("skipped E (line 7): not ready", out)
        tasks = self.queue()["tasks"]
        self.assertEqual([t["id"] for t in tasks], ["A", "X", "Y", "B", "C"])
        self.assertEqual(tasks[0]["prompt"], "original")
        self.assertEqual(tasks[-1]["prompt"], SCOPE)
        before = runner.QUEUE_PATH.read_bytes()
        self.call("refill")
        self.assertEqual(runner.QUEUE_PATH.read_bytes(), before)

    def test_dry_run_makes_no_state_or_lock_changes(self):
        before = {p.name: p.read_bytes() for p in runner.RUNNER_DIR.iterdir() if p.is_file()}
        rc, out, _ = self.call("refill", "--dry-run")
        after = {p.name: p.read_bytes() for p in runner.RUNNER_DIR.iterdir() if p.is_file()}
        self.assertEqual(rc, 0)
        self.assertIn("would add A: First", out)
        self.assertIn("would add C: Third", out)
        self.assertEqual(before, after)

    def test_malformed_and_duplicate_backlog_lines_are_skipped(self):
        self.backlog([f"DUP | ready | One | {SCOPE}", f"DUP | ready | Two | {SCOPE}",
                      "BAD | ready | missing scope", f"../escape | ready | Bad id | {SCOPE}",
                      f"BAD2 | ready | extra | pipe | {SCOPE}",
                      f"BAD3 | maybe | Bad readiness | {SCOPE}",
                      "BAD4 | ready | Short | short", f"GOOD | ready | Good | {SCOPE}"])
        rc, out, err = self.call("refill")
        self.assertEqual(rc, 0)
        self.assertEqual(out.count("duplicate backlog id"), 2)
        self.assertEqual(err.count("malformed"), 5)
        self.assertEqual([t["id"] for t in self.queue()["tasks"]], ["GOOD"])

    def test_invalid_or_duplicate_fences_fail_closed(self):
        for data in ("no block", "```debra-research-backlog\nA | ready | T | " + SCOPE,
                     "```debra-research-backlog\n```\n```debra-research-backlog\n```\n"):
            with self.subTest(data=data):
                runner.BACKLOG_PATH.write_text(data)
                before = runner.QUEUE_PATH.read_bytes()
                rc, _, _ = self.call("refill")
                self.assertNotEqual(rc, 0)
                self.assertEqual(before, runner.QUEUE_PATH.read_bytes())

    def test_zero_and_negative_threshold(self):
        rc, out, _ = self.call("refill", "--min-pending", "0")
        self.assertEqual(rc, 0)
        self.assertIn("threshold met", out)
        self.assertEqual(self.queue()["tasks"], [])
        self.assertNotEqual(self.call("refill", "--min-pending", "-1")[0], 0)

    def test_running_task_prevents_refill_and_manual_add(self):
        self.put_tasks([{"id": "A", "status": "pending", "prompt": SCOPE}])
        self.assertTrue(runner.acquire_lock())
        self.addCleanup(runner.release_lock)
        before = runner.QUEUE_PATH.read_bytes()
        rc, _, err = self.call("refill")
        self.assertNotEqual(rc, 0)
        self.assertIn("runner active", err)
        self.assertNotEqual(self.call("add", "--id", "X", "--prompt", SCOPE)[0], 0)
        self.assertEqual(runner.QUEUE_PATH.read_bytes(), before)

    def test_running_status_is_not_pending_or_modified(self):
        original = {"id": "A", "status": "running", "prompt": "untouchable"}
        self.put_tasks([original])
        self.call("refill", "--min-pending", "1")
        tasks = self.queue()["tasks"]
        self.assertEqual(tasks[0], original)
        self.assertEqual([(t["id"], t["status"]) for t in tasks],
                         [("A", "running"), ("B", "pending")])
        self.assertEqual(tasks[1]["prompt"], SCOPE)

    def test_unreadable_lock_is_not_reclaimed(self):
        runner.LOCK_PATH.write_text("")
        self.assertFalse(runner.acquire_lock())
        self.assertTrue(runner.LOCK_PATH.exists())

    def test_scheduled_run_refills_then_executes_with_one_lock(self):
        seen = []

        def fake_run(task, cfg, run_dir):
            seen.append(task["id"])
            self.assertTrue(runner.LOCK_PATH.exists())
            self.assertNotEqual(self.call("refill")[0], 0)
            return {"task": task["id"], "ok": True, "rc": 0, "cost_usd": 0,
                    "duration_s": 0, "session": None, "started_utc": runner._now()}

        with mock.patch.object(runner, "_runner_is_committed", return_value=True), \
             mock.patch.object(runner, "opencode_available", return_value=True), \
             mock.patch.object(runner, "run_task", side_effect=fake_run):
            self.assertEqual(self.call("run", "--once")[0], 0)
            self.assertEqual([(t["id"], t["status"]) for t in self.queue()["tasks"]],
                             [("A", "done"), ("B", "pending"), ("C", "pending")])
            self.assertEqual(self.call("run", "--once")[0], 0)
        self.assertEqual(seen, ["A", "B"])
        self.assertEqual([(t["id"], t["status"]) for t in self.queue()["tasks"]],
                         [("A", "done"), ("B", "done"), ("C", "pending"), ("D", "pending")])

    def test_uncommitted_runner_does_not_auto_refill(self):
        with mock.patch.object(runner, "_runner_is_committed", return_value=False):
            rc, out, _ = self.call("run", "--once")
        self.assertEqual(rc, 0)
        self.assertIn("queue empty", out)
        self.assertEqual(self.queue()["tasks"], [])

    def test_commit_gate_compares_working_file_with_git_head(self):
        script = runner.RUNNER_DIR / "candidate.py"
        script.write_bytes(b"candidate")
        result = mock.Mock(returncode=0, stdout=b"candidate")
        with mock.patch.object(runner, "__file__", str(script)), \
             mock.patch.object(runner.subprocess, "run", return_value=result) as git:
            self.assertTrue(runner._runner_is_committed())
            self.assertEqual(git.call_args.args[0], ["git", "show", "HEAD:tools/scheduled_runner.py"])
            script.write_bytes(b"different")
            self.assertFalse(runner._runner_is_committed())
            result.returncode = 1
            self.assertFalse(runner._runner_is_committed())

    def test_missing_backlog_does_not_block_existing_pending_task(self):
        self.put_tasks([{"id": "X", "status": "pending", "prompt": SCOPE}])
        runner.BACKLOG_PATH.rename(runner.BACKLOG_PATH.with_suffix(".saved"))
        record = {"task": "X", "ok": True, "rc": 0, "cost_usd": 0,
                  "duration_s": 0, "session": None, "started_utc": runner._now()}
        with mock.patch.object(runner, "_runner_is_committed", return_value=True), \
             mock.patch.object(runner, "opencode_available", return_value=True), \
             mock.patch.object(runner, "run_task", return_value=record):
            rc, _, err = self.call("run", "--once")
        self.assertEqual(rc, 0)
        self.assertIn("automatic refill skipped", err)
        self.assertEqual(self.queue()["tasks"][0]["status"], "done")

    def test_refill_write_failure_does_not_execute_unpersisted_task(self):
        with mock.patch.object(runner, "_runner_is_committed", return_value=True), \
             mock.patch.object(runner, "_write_json", side_effect=PermissionError), \
             mock.patch.object(runner, "run_task") as run_task:
            rc, _, err = self.call("run", "--once")
        self.assertEqual(rc, 1)
        self.assertIn("PermissionError", err)
        run_task.assert_not_called()
        self.assertEqual(self.queue()["tasks"], [])
        self.assertFalse(runner.LOCK_PATH.exists())

    def test_stop_and_exhausted_budget_prevent_scheduled_refill(self):
        runner.STOP_PATH.write_text("")
        with mock.patch.object(runner, "_runner_is_committed", return_value=True):
            rc, out, _ = self.call("run", "--once")
        self.assertEqual(rc, 0)
        self.assertIn("stop file", out)
        self.assertEqual(self.queue()["tasks"], [])
        runner.STOP_PATH.unlink()
        runner._write_json(runner.CONFIG_PATH, {"daily_budget_usd": 0})
        with mock.patch.object(runner, "_runner_is_committed", return_value=True):
            rc, out, _ = self.call("run", "--once")
        self.assertEqual(rc, 0)
        self.assertIn("budget exhausted", out)
        self.assertEqual(self.queue()["tasks"], [])


if __name__ == "__main__":
    unittest.main()

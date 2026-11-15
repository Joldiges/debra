"""Offline tests for tools/activity.py.

They use a temporary runner tree, stub the OpenCode and web probes, and never
start a model call, contact a device, or touch the real .local/runner state.
"""

import contextlib
import io
import json
import os
import subprocess
import sys
import tempfile
import time
import unittest
from pathlib import Path
from unittest import mock

SOURCE = Path(__file__).resolve().parent.parent
if str(SOURCE) not in sys.path:
    sys.path.insert(0, str(SOURCE))

import tools.activity as activity  # noqa: E402  (path set above)
import tools.scheduled_runner as runner  # noqa: E402  (path set above)


class ActivityTests(unittest.TestCase):
    def setUp(self):
        self._tmp = tempfile.TemporaryDirectory(prefix="activity-", dir="/tmp/opencode")
        root = Path(self._tmp.name)
        self.runner_dir = root / "runner"
        self.runner_dir.mkdir()
        self.paths = {
            "RUNNER_DIR": self.runner_dir,
            "QUEUE_PATH": self.runner_dir / "queue.json",
            "STATE_PATH": self.runner_dir / "state.json",
            "CONFIG_PATH": self.runner_dir / "config.json",
        }
        patches = [mock.patch.object(runner, name, value) for name, value in self.paths.items()]
        patches.append(mock.patch.object(activity, "STATUS_DIR", root / "status"))
        for patch in patches:
            patch.start()
            self.addCleanup(patch.stop)
        self.addCleanup(self._tmp.cleanup)
        self.write_queue()
        self.write_state()

    def write_queue(self, pending=("T2",), done=("T1",)):
        tasks = [{"id": task_id, "title": f"title {task_id}", "status": "pending"} for task_id in pending]
        tasks += [{"id": task_id, "title": f"title {task_id}", "status": "done"} for task_id in done]
        self.paths["QUEUE_PATH"].write_text(json.dumps({"version": 1, "tasks": tasks}))

    def write_state(self, cost=0.25):
        self.paths["STATE_PATH"].write_text(json.dumps({
            "version": 1,
            "days": {"2026-11-15": {"tasks": 1, "cost_usd": cost}},
            "tasks": {"T1": {"status": "done", "cost_usd": cost,
                             "finished_utc": "2026-11-15T07:00:00Z"}},
        }))

    def write_log(self, *entries):
        with (self.runner_dir / "activity.log").open("w") as handle:
            for entry in entries:
                handle.write(json.dumps(entry) + "\n")

    def write_lock(self, pid):
        (self.runner_dir / "run.lock").write_text(json.dumps({"pid": pid, "started": "x"}))

    def render(self):
        with mock.patch.object(activity, "sessions_snapshot",
                               return_value={"error": None, "sessions": []}), \
             mock.patch.object(activity, "web_snapshot",
                               return_value={"port": 8787, "listening": True}):
            return activity.render(8787)

    def test_running_task_pending_queue_and_spend(self):
        import os
        self.write_lock(os.getpid())
        self.write_log({"event": "start", "utc": "2026-11-15T19:04:35Z",
                        "task": "T2", "title": "title T2",
                        "model": "openrouter/example#high"})
        text = self.render()
        self.assertIn("Running now:** `T2`", text)
        self.assertIn("1 pending, 1 done of 2", text)
        self.assertIn("$0.2500", text)
        self.assertIn("Next: `T2`", text)
        self.assertIn("Listening on http://127.0.0.1:8787/", text)

    def test_idle_when_no_lock_holder(self):
        self.write_log({"event": "finish", "utc": "2026-11-15T19:04:35Z",
                        "task": "T1", "ok": True, "cost_usd": 0.25})
        text = self.render()
        self.assertIn("**Idle**", text)
        self.assertNotIn("Running now", text)

    def test_stale_lock_pid_is_not_running(self):
        self.write_lock(999999)
        self.write_log({"event": "start", "utc": "2026-11-15T19:04:35Z",
                        "task": "T2", "title": "title T2", "model": "m"})
        self.assertIn("**Idle**", self.render())

    def test_stop_file_is_reported(self):
        (self.runner_dir / "STOP").write_text("")
        self.assertIn("Stopped by STOP file", self.render())

    def test_session_probe_failure_is_reported_not_hidden(self):
        with mock.patch.object(activity, "sessions_snapshot",
                               return_value={"error": "opencode unavailable (OSError)",
                                             "sessions": []}), \
             mock.patch.object(activity, "web_snapshot",
                               return_value={"port": 8787, "listening": False}):
            text = activity.render(8787)
        self.assertIn("opencode unavailable", text)
        self.assertIn("Not listening on port 8787", text)

    def test_write_is_atomic_and_readable(self):
        target = activity.write("# snapshot")
        self.assertEqual(target.name, "activity.md")
        self.assertEqual(target.read_text(), "# snapshot\n")
        self.assertFalse(target.with_suffix(".md.tmp").exists())

    def test_live_lock_without_start_event_is_running(self):
        process = subprocess.Popen([sys.executable, "-c", "import time; time.sleep(60)"])
        self.addCleanup(process.wait)
        self.addCleanup(process.terminate)
        self.write_lock(process.pid)
        self.write_log({"event": "finish", "task": "old"})
        text = self.render()
        self.assertIn("Running now:** `unknown`", text)
        self.assertNotIn("**Idle**", text)

    def test_nonexistent_lock_pid_is_idle_even_with_start_event(self):
        self.write_lock(2147483647)
        self.write_log({"event": "start", "task": "old"})
        self.assertIn("**Idle**", self.render())

    def test_server_override_environment_is_ignored(self):
        # `opencode api` discovers the background service itself; no argument or
        # environment value may point it at another host.
        with mock.patch.dict(os.environ, {"OPENCODE_SERVER": "http://attacker.invalid:4096",
                                          "OPENCODE_API_URL": "http://attacker.invalid:4096"}), \
             mock.patch.object(subprocess, "run") as run:
            run.return_value = subprocess.CompletedProcess([], 0, b'{"data": []}')
            result = activity.sessions_snapshot()
        self.assertIsNone(result["error"])
        argv = run.call_args.args[0]
        self.assertEqual(argv, ["opencode", "api", "get", "/api/session"])
        env = run.call_args.kwargs["env"]
        self.assertNotIn("OPENCODE_SERVER", env)
        self.assertNotIn("OPENCODE_API_URL", env)

    def session_result(self, payload):
        encoded = json.dumps(payload).encode()
        with mock.patch.object(subprocess, "run",
                               return_value=subprocess.CompletedProcess([], 0, encoded)):
            return activity.sessions_snapshot()

    def test_malformed_session_records_are_unavailable(self):
        bad_payloads = [
            [], {"data": {}}, {"data": ["not a record"]},
            {"data": [{"time": "malformed"}]},
            {"data": [{"time": []}]},
            {"data": [{"model": ["malformed"]}]},
            {"data": [{"model": {"id": 5}}]},
            {"data": [{"cost": "bad-cost"}]},
            {"data": [{"time": {"busy": "bad-time"}}]},
            {"data": [{"title": ["not safe to render"]}]},
        ]
        for payload in bad_payloads:
            with self.subTest(payload=payload):
                result = self.session_result(payload)
                self.assertIsNotNone(result["error"])
                self.assertIn("unavailable", result["error"])
                self.assertEqual(result["sessions"], [])

    def test_valid_session_uses_the_cli_and_preserves_unknown(self):
        data = {"data": [{"title": "example", "time": {"created": 123},
                          "model": {"providerID": "example", "id": "model"}}]}
        with mock.patch.object(subprocess, "run",
                               return_value=subprocess.CompletedProcess(
                                   [], 0, json.dumps(data).encode())) as run:
            result = activity.sessions_snapshot()
        run.assert_called_once()
        self.assertEqual(run.call_args.args[0], ["opencode", "api", "get", "/api/session"])
        self.assertEqual(run.call_args.kwargs["timeout"], activity.OPENCODE_TIMEOUT_S)
        self.assertIsNone(result["error"])
        self.assertIsNone(result["sessions"][0]["working"])
        self.assertEqual(result["sessions"][0]["model"], "example/model")

    def test_runner_bad_json_is_reported_as_unavailable(self):
        self.paths["QUEUE_PATH"].write_text("{")
        text = self.render()
        self.assertIn("unavailable", text.lower())
        self.assertIn("JSON", text)

    def test_runner_filesystem_error_is_reported_as_unavailable(self):
        with mock.patch.object(runner, "_read_json", side_effect=PermissionError("denied")):
            text = self.render()
        self.assertIn("unavailable", text.lower())
        self.assertIn("PermissionError", text)

    def test_lock_json_error_is_reported_as_unavailable(self):
        (self.runner_dir / "run.lock").write_text("{")
        self.assertIn("unavailable", self.render().lower())

    def test_unreadable_session_json_is_unavailable(self):
        with mock.patch.object(subprocess, "run",
                               return_value=subprocess.CompletedProcess([], 0, b"{")):
            result = activity.sessions_snapshot()
        self.assertIn("unreadable session list", result["error"])
        self.assertEqual(result["sessions"], [])

    def test_deeply_nested_session_json_is_unavailable(self):
        with mock.patch.object(subprocess, "run",
                               return_value=subprocess.CompletedProcess(
                                   [], 0, b"[" * 2000 + b"]" * 2000)):
            result = activity.sessions_snapshot()
        self.assertIn("unavailable", result["error"])
        self.assertEqual(result["sessions"], [])

    def test_session_timeout_is_unavailable(self):
        with mock.patch.object(subprocess, "run",
                               side_effect=subprocess.TimeoutExpired("opencode", 15)):
            result = activity.sessions_snapshot()
        self.assertIn("TimeoutExpired", result["error"])
        self.assertEqual(result["sessions"], [])

    def test_session_command_failure_is_unavailable(self):
        with mock.patch.object(subprocess, "run",
                               return_value=subprocess.CompletedProcess([], 3, b"")):
            result = activity.sessions_snapshot()
        self.assertIn("exit 3", result["error"])
        self.assertEqual(result["sessions"], [])

    def test_oversized_session_list_is_unavailable(self):
        with mock.patch.object(subprocess, "run",
                               return_value=subprocess.CompletedProcess(
                                   [], 0, b"x" * (activity.OPENCODE_MAX_BYTES + 1))):
            result = activity.sessions_snapshot()
        self.assertIn("too large", result["error"])
        self.assertEqual(result["sessions"], [])

    def test_turn_in_progress_is_working(self):
        # busy is the last turn start, idle the last turn end; a start with no
        # end is a turn that is still running.
        result = self.session_result({"data": [{"title": "t", "time": {"busy": 2000}}]})
        self.assertIsNone(result["error"])
        self.assertTrue(result["sessions"][0]["working"])

    def test_session_with_no_turns_is_unknown(self):
        result = self.session_result({"data": [{"title": "t", "time": {}}]})
        self.assertIsNone(result["error"])
        self.assertIsNone(result["sessions"][0]["working"])

    def test_session_with_only_an_end_time_is_idle(self):
        result = self.session_result({"data": [{"title": "t", "time": {"idle": 2000}}]})
        self.assertIsNone(result["error"])
        self.assertFalse(result["sessions"][0]["working"])

    def test_ago_accepts_seconds_and_milliseconds(self):
        now = time.time()
        self.assertRegex(activity._ago(now - 5), r"^[0-9]+s ago$")
        self.assertRegex(activity._ago((now - 300) * 1000), r"^[0-9]+m ago$")
        self.assertEqual(activity._ago(None), "unknown")
        self.assertEqual(activity._ago(0), "unknown")

    def session(self, title, working=False, created=1, updated=1, cost=0.1,
                provider="openrouter", model_id="m", variant=""):
        return {
            "id": title, "title": title, "agent": "", "child": True,
            "working": working, "cost": cost, "created": created, "updated": updated,
            "model": "/".join(filter(None, [provider, model_id]))
                     + (f"#{variant}" if variant else ""),
            "provider": provider, "model_id": model_id, "variant": variant,
        }

    def render_with_sessions(self, sessions, limit=24):
        with mock.patch.object(activity, "sessions_snapshot",
                               return_value={"error": None, "sessions": sessions}), \
             mock.patch.object(activity, "web_snapshot",
                               return_value={"port": 8787, "listening": False}):
            return activity.render(8787, limit)

    def test_working_rows_keep_creation_order_when_activity_changes(self):
        # Ordering by `updated` reshuffles on every refresh; creation does not move.
        first = self.session("older", working=True, created=100, updated=900)
        second = self.session("newer", working=True, created=200, updated=100)
        text = self.render_with_sessions([first, second])
        self.assertLess(text.index("newer"), text.index("older"))
        first["updated"], second["updated"] = 100, 900
        text = self.render_with_sessions([first, second])
        self.assertLess(text.index("newer"), text.index("older"))

    def test_limit_hides_only_recent_sessions(self):
        sessions = [self.session(f"work{i}", working=True, created=i) for i in range(3)]
        sessions += [self.session(f"rest{i}", created=i, updated=i) for i in range(5)]
        text = self.render_with_sessions(sessions, limit=5)
        for i in range(3):
            self.assertIn(f"work{i}", text)
        self.assertIn("rest4", text)
        self.assertIn("rest3", text)
        self.assertNotIn("rest2", text)
        self.assertIn("3 hidden", text)

    def test_all_shows_every_known_session(self):
        sessions = [self.session(f"s{i}", created=i, updated=i) for i in range(40)]
        text = self.render_with_sessions(sessions, limit=10**6)
        self.assertIn("s39", text)
        self.assertIn("s0", text)
        self.assertNotIn("hidden", text)

    def test_table_truncates_long_cells_to_the_cap(self):
        lines = activity._table(["A"], [["x" * 50]], caps={0: 10})
        cell = lines[2].split("|")[1].strip()
        self.assertEqual(len(cell), 10)
        self.assertTrue(cell.endswith("…"))

    def test_model_label_drops_the_common_provider_only(self):
        self.assertEqual(activity._model_label(self.session(
            "t", model_id="deepseek/deepseek-v4.1-flash-1017", variant="high")),
            "deepseek/deepseek-v4.1-flash-1017#high")
        self.assertEqual(activity._model_label(self.session(
            "t", provider="anthropic", model_id="claude", variant="fast")),
            "anthropic/claude#fast")

    def test_session_cost_total_is_shown(self):
        text = self.render_with_sessions([self.session("a", cost=1.25),
                                          self.session("b", cost=0.5)])
        self.assertIn("$1.7500", text)

    def test_web_probe_oserror_is_reported(self):
        with mock.patch.object(activity, "sessions_snapshot", return_value={"error": None, "sessions": []}), \
             mock.patch.object(activity, "web_snapshot", side_effect=PermissionError("denied")):
            text = activity.render(8787)
        self.assertIn("Development web server unavailable (PermissionError)", text)

    def test_status_write_error_returns_without_traceback(self):
        output, error = io.StringIO(), io.StringIO()
        with mock.patch.object(activity, "render", return_value="# snapshot"), \
             mock.patch.object(activity, "write", side_effect=PermissionError("denied")), \
             contextlib.redirect_stdout(output), contextlib.redirect_stderr(error):
            result = activity.main([])
        self.assertEqual(result, 1)
        self.assertIn("status file unavailable (PermissionError)", error.getvalue())
        self.assertNotIn("Traceback", error.getvalue())


if __name__ == "__main__":
    unittest.main()

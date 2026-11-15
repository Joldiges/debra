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
        # Do not use the production constant: this must catch an accidental change to it.
        self.assertEqual(run.call_args.kwargs["timeout"], 15)
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

    def test_paint_colours_state_cells_and_headers(self):
        painted = activity._paint("| State | Title |\n| --- | --- |\n| working | t |\n| idle | u |")
        self.assertIn("\033[1;32m working \033[0m", painted)
        self.assertIn("\033[2m idle \033[0m", painted)
        self.assertIn("\033[1m State \033[0m", painted)
        self.assertNotIn("\033", painted.splitlines()[1])

    def test_paint_leaves_prose_alone(self):
        prose = "working is a turn in progress, not a promise"
        self.assertEqual(activity._paint(prose), prose)

    def test_paint_bands_cost_and_age(self):
        row = "| working | t | m | $0.0500 | 30s |"
        painted = activity._paint("| State | Kind | Title | Model | Cost | Age |\n| --- | --- | --- | --- | --- | --- |\n" + row)
        self.assertIn(activity.GREEN + " $0.0500 ", painted)
        self.assertIn(activity.GREEN + " 30s ", painted)
        row = "| idle | t | m | $0.9000 | 3.0h |"
        painted = activity._paint("| State | Kind | Title | Model | Cost | Age |\n| --- | --- | --- | --- | --- | --- |\n" + row)
        self.assertIn(activity.RED + " $0.9000 ", painted)
        self.assertIn(activity.RED + " 3.0h ", painted)

    def test_paint_colours_model_by_absolute_rate(self):
        rates = {"cheap#high": 0.02, "mid#high": 0.10, "dearer#high": 0.17, "dear#high": 0.90}
        text = ("| State | Model |\n| --- | --- |\n"
                "| working | cheap#high |\n| working | mid#high |\n"
                "| working | dearer#high |\n| working | dear#high |")
        painted = activity._paint(text, rates)
        self.assertIn(activity.GREEN + " cheap#high ", painted)
        self.assertIn(activity.YELLOW + " mid#high ", painted)
        self.assertIn(activity.ORANGE + " dearer#high ", painted)
        self.assertIn(activity.RED + " dear#high ", painted)

    def test_paint_separates_two_middle_models(self):
        # Regression: terra (~$0.08) and sol (~$0.17) both fell in one yellow
        # band, so the table showed a model costing twice as much identically.
        rates = {"openai/gpt-6.1-terra#flex-high": 0.084,
                 "openai/gpt-6.1-sol#flex-high": 0.165}
        text = ("| State | Model |\n| --- | --- |\n"
                "| working | openai/gpt-6.1-terra#flex-high |\n"
                "| working | openai/gpt-6.1-sol#flex-high |")
        painted = activity._paint(text, rates)
        self.assertIn(activity.YELLOW + " openai/gpt-6.1-terra#flex-high ", painted)
        self.assertIn(activity.ORANGE + " openai/gpt-6.1-sol#flex-high ", painted)
        self.assertNotEqual(activity._paint(text, rates).count(activity.YELLOW), 2)

    def test_two_clock_helpers_do_not_shadow_each_other(self):
        # A refactor once added a second _seconds_since, which shadowed the
        # UTC-string one the runner uses; the suite stayed green while the
        # runner's elapsed time silently became None. Both names must work.
        stamp = time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime(time.time() - 90))
        self.assertIsInstance(activity._seconds_since(stamp), int)
        self.assertAlmostEqual(activity._seconds_ago(time.time() - 90), 90, places=3)

    def test_a_running_task_reports_its_elapsed_time_in_words(self):
        text = activity.render(8787, 5)
        self.assertNotIn("start time not readable (", "\n".join(text))

    def test_why_says_what_the_snapshot_can_prove(self):
        now = 1_700_000_000.0
        def row(**kw):
            base = {"id": "x", "working": False, "busy_at": None, "idle_at": None,
                    "parent": "", "child": False, "title": "t", "agent": "",
                    "model": "", "provider": "", "model_id": "", "variant": "",
                    "cost": 0.0, "created": 0, "tokens": 0, "updated": 0}
            base.update(kw)
            return base
        ms = lambda seconds_ago: (now - seconds_ago) * 1000
        self.assertEqual(activity._why(row(working=None), {}, now), "never started")
        self.assertEqual(activity._why(row(working=True, busy_at=ms(12)), {}, now), "running 12s")
        self.assertEqual(activity._why(row(working=True, busy_at=ms(900)), {}, now), "long turn 15m")
        self.assertEqual(activity._why(row(idle_at=ms(20)), {}, now), "just finished")
        self.assertEqual(activity._why(row(idle_at=ms(7200)), {}, now), "waiting for you")

        parent_busy = row(id="p", working=True, busy_at=ms(30))
        parent_idle = row(id="p", working=False, idle_at=ms(30))
        child = row(id="c", child=True, parent="p", idle_at=ms(10))
        self.assertEqual(activity._why(child, {"p": parent_busy}, now), "finished; parent busy")
        self.assertEqual(activity._why(child, {"p": parent_idle}, now), "finished")
        self.assertEqual(activity._why(child, {}, now), "parent deleted")

    def test_a_parent_hidden_by_the_limit_is_still_a_parent(self):
        # Live defect, 2026-11-15: every sub-session read "parent gone" because
        # the lookup map was built from the rows on display, and --limit hides
        # the main session. A parent off-screen is not a parent that vanished.
        now = 1_700_000_000.0
        def row(**kw):
            base = {"id": "x", "working": False, "busy_at": None, "idle_at": None,
                    "parent": "", "child": False, "title": "t", "agent": "",
                    "model": "", "provider": "", "model_id": "", "variant": "",
                    "cost": 0.0, "created": 0, "tokens": 0, "updated": 0}
            base.update(kw)
            return base
        main = row(id="main", working=False, idle_at=(now - 600) * 1000)
        child = row(id="child", child=True, parent="main", idle_at=(now - 300) * 1000)
        table = "\n".join(activity._session_table([child], by_id={"main": main}, now=now))
        self.assertIn("finished", table)
        self.assertNotIn("parent deleted", table)

    def test_why_is_in_the_table_and_never_invents_a_question(self):
        now = 1_700_000_000.0
        session = {"id": "a", "title": "Waiting", "agent": "", "model": "", "provider": "",
                   "model_id": "", "variant": "", "cost": 0.01, "created": 0, "tokens": 0,
                   "updated": 0, "child": False, "parent": "", "working": False,
                   "busy_at": (now - 400) * 1000, "idle_at": (now - 3600) * 1000}
        table = "\n".join(activity._session_table([session], now=now))
        self.assertIn("Why", table)
        self.assertIn("waiting for you", table)
        # The session list carries no message data, so the tool must not claim to
        # know about a pending question or a tool call.
        for word in ("question", "approval", "blocked on", "waiting on user"):
            self.assertNotIn(word, table)

    def test_session_rates_ignore_zero_cost_and_missing_tokens(self):
        sessions = [
            self.session("a", cost=1.0, model_id="cheap"),
            self.session("b", cost=0.0, model_id="free"),
        ]
        sessions[0]["tokens"] = 2_000_000
        sessions[1]["tokens"] = 1_000_000
        rates = activity.session_rates(sessions)
        self.assertEqual(rates, {"cheap": 0.5})

    def test_render_reports_model_rates(self):
        session = self.session("a", cost=2.0, model_id="cheap#high")
        session["tokens"] = 4_000_000
        meta = {}
        with mock.patch.object(activity, "sessions_snapshot",
                               return_value={"error": None, "sessions": [session]}), \
             mock.patch.object(activity, "web_snapshot",
                               return_value={"port": 8787, "listening": False}):
            text = activity.render(8787, 24, meta)
        self.assertEqual(meta["rates"], {"cheap#high": 0.5})
        self.assertIn("Model rate, blended cost per million tokens", text)

    def test_redirected_output_has_no_escape_codes(self):
        output = io.StringIO()
        with mock.patch.object(activity, "render", return_value="# snapshot\n| working | t |"), \
             mock.patch.object(activity, "write", return_value=Path("/tmp/opencode/x.md")), \
             contextlib.redirect_stdout(output):
            self.assertEqual(activity.main([]), 0)
        self.assertNotIn("\033", output.getvalue())

    def test_no_color_flag_is_accepted(self):
        with mock.patch.object(activity, "render", return_value="# snapshot"), \
             mock.patch.object(activity, "write", return_value=Path("/tmp/opencode/x.md")), \
             contextlib.redirect_stdout(io.StringIO()):
            self.assertEqual(activity.main(["--no-color"]), 0)

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

    def test_tui_column_sizing_at_several_widths(self):
        minimum = sum(activity.TUI_MIN_WIDTHS) + 6 * len(activity.TUI_SEPARATOR)
        self.assertIsNone(activity._tui_widths(minimum - 1))
        self.assertEqual(activity._tui_widths(minimum), activity.TUI_MIN_WIDTHS)
        for width in (minimum, 60, 80, 120, 200):
            with self.subTest(width=width):
                sizes = activity._tui_widths(width)
                self.assertEqual(len(sizes), 7)
                self.assertLessEqual(sum(sizes) + 6 * len(activity.TUI_SEPARATOR), width)
                for size, low, high in zip(sizes, activity.TUI_MIN_WIDTHS,
                                           activity.TUI_MAX_WIDTHS):
                    self.assertGreaterEqual(size, low)
                    self.assertLessEqual(size, high)

    def test_tui_fit_truncates_pads_and_removes_controls(self):
        self.assertEqual(activity._tui_fit("abcdefgh", 5), "abcd…")
        self.assertEqual(activity._tui_fit("abcdefgh", 1), "…")
        self.assertEqual(activity._tui_fit("abc", 0), "")
        self.assertEqual(activity._tui_fit("abc", 5), "abc  ")
        self.assertEqual(activity._tui_fit("a\nb\tc", 5), "a b c")
        self.assertEqual(activity._tui_fit("ab界z", 4), "ab… ")
        self.assertEqual(activity._tui_fit("a界", 3), "a界")
        self.assertEqual(activity._tui_fit("e\u0301xx", 2), "e\u0301…")

    def test_tui_tiny_terminal_decision(self):
        minimum = sum(activity.TUI_MIN_WIDTHS) + 6 * len(activity.TUI_SEPARATOR)
        self.assertTrue(activity._tui_too_small(0, 0))
        self.assertTrue(activity._tui_too_small(3, minimum))
        self.assertTrue(activity._tui_too_small(4, minimum - 1))
        self.assertFalse(activity._tui_too_small(4, minimum))
        self.assertFalse(activity._tui_too_small(24, 80))

    def test_tui_supporting_text_can_scroll_horizontally(self):
        self.assertEqual(activity._tui_text_window("abcdefghij", 5, 0), "abcd…")
        self.assertEqual(activity._tui_text_window("abcdefghij", 5, 3), "…def…")
        self.assertEqual(activity._tui_text_window("abcdefghij", 5, 7), "…hij ")
        self.assertEqual(activity._tui_text_window("a界bc", 3, 3), "…bc")

    def test_recent_session_tie_keeps_markdown_idle_before_unknown(self):
        unknown = self.session("unknown-session", working=None, updated=1)
        idle = self.session("idle-session", working=False, updated=1)
        text = self.render_with_sessions([unknown, idle])
        self.assertLess(text.index("idle-session"), text.index("unknown-session"))

    def test_tui_model_rate_band_boundaries(self):
        for rate, band in ((None, 0), (0.0, 1), (0.049, 1), (0.05, 2),
                           (0.119, 2), (0.12, 3), (0.299, 3), (0.30, 4)):
            with self.subTest(rate=rate):
                self.assertEqual(activity._rate_band(rate), band)

    def test_tui_refuses_redirected_stdout_without_rendering(self):
        out, err = io.StringIO(), io.StringIO()
        with mock.patch.object(activity, "render") as render, \
             mock.patch.object(activity.curses, "wrapper") as wrapper, \
             contextlib.redirect_stdout(out), contextlib.redirect_stderr(err):
            self.assertNotEqual(activity.main(["--tui"]), 0)
        self.assertIn("requires a terminal", err.getvalue())
        self.assertEqual(out.getvalue(), "")
        self.assertNotIn("\033", err.getvalue())
        render.assert_not_called()
        wrapper.assert_not_called()

    def test_tui_argument_and_default_markdown_path(self):
        output = io.StringIO()
        with mock.patch.object(output, "isatty", return_value=True), \
             mock.patch.object(activity.curses, "wrapper") as wrapper, \
             mock.patch.object(activity, "render", return_value="# snapshot") as render, \
             mock.patch.object(activity, "write", return_value=Path("/tmp/opencode/x.md")), \
             mock.patch.dict(os.environ, {"NO_COLOR": "1"}), \
             contextlib.redirect_stdout(output):
            self.assertEqual(activity.main(["--tui", "--interval", "0.5", "--limit", "3"]), 0)
            wrapper.assert_called_once_with(activity._tui_screen, 8787, 3, 0.5, False)
            render.assert_not_called()
            self.assertEqual(activity.main([]), 0)
            render.assert_called_once()
        self.assertIn("# snapshot", output.getvalue())
        self.assertIn("(written to /tmp/opencode/x.md)", output.getvalue())

    def test_tui_default_interval(self):
        output = io.StringIO()
        with mock.patch.object(output, "isatty", return_value=True), \
             mock.patch.object(activity.curses, "wrapper") as wrapper, \
             contextlib.redirect_stdout(output):
            self.assertEqual(activity.main(["--tui"]), 0)
        self.assertEqual(wrapper.call_args.args[3], 2.0)

    def test_invalid_tui_intervals_are_rejected(self):
        for value in ("0", "-1", "nan", "inf", "nonsense"):
            with self.subTest(value=value), contextlib.redirect_stderr(io.StringIO()):
                with self.assertRaises(SystemExit) as exc:
                    activity.main(["--interval", value])
                self.assertEqual(exc.exception.code, 2)

    def test_tui_content_preserves_order_limit_and_supporting_details(self):
        sessions = [self.session("older work", working=True, created=1, updated=100),
                    self.session("newer work", working=True, created=2, updated=1),
                    self.session("recent", updated=3), self.session("hidden", updated=2)]
        sessions[1]["tokens"] = 1_000_000
        meta = {}
        with mock.patch.object(activity, "sessions_snapshot",
                               return_value={"error": None, "sessions": sessions}), \
             mock.patch.object(activity, "web_snapshot",
                               return_value={"port": 8787, "listening": False}):
            text = activity.render(8787, 3, meta)
        content = activity._tui_content(text, meta, 3)
        rows = [(row, band) for row, band in content if isinstance(row, list)]
        self.assertEqual([row[2] for row, _ in rows], ["newer work", "older work", "recent"])
        self.assertEqual(rows[0][1], 2)
        supporting = "\n".join(row for row, _ in content if isinstance(row, str))
        self.assertIn("## Research runner", supporting)
        self.assertIn("## Agent sessions", supporting)
        self.assertIn("1 hidden", supporting)
        self.assertIn("Model rate, blended", supporting)
        self.assertIn("Not listening on port 8787", supporting)

    def test_tui_content_reports_unavailable_sessions(self):
        meta = {}
        with mock.patch.object(activity, "sessions_snapshot",
                               return_value={"error": "opencode unavailable", "sessions": []}), \
             mock.patch.object(activity, "web_snapshot",
                               return_value={"port": 8787, "listening": False}):
            text = activity.render(8787, 24, meta)
        content = activity._tui_content(text, meta, 24)
        self.assertIn(("opencode unavailable", 0), content)
        self.assertIn(("## Development web server", 0), content)


if __name__ == "__main__":
    unittest.main()

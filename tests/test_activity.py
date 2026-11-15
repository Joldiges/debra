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


class RecordingScreen:
    """The slice of a curses window the TUI uses, recording what it is told."""

    def __init__(self, height=24, width=100, keys=(-1, ord("q"))):
        self.height, self.width, self.keys = height, width, list(keys)
        self.writes, self.erases, self.frames = [], 0, 0

    def getmaxyx(self):
        return self.height, self.width

    def erase(self):
        self.erases += 1

    def addstr(self, y, x, text, attr=0):
        self.writes.append((y, x, text))

    def refresh(self):
        self.frames += 1

    def getch(self):
        return self.keys.pop(0) if self.keys else ord("q")

    def timeout(self, milliseconds):
        pass


def fake_curses():
    """A curses module with the constants and calls the screen loop touches."""
    return mock.Mock(
        error=activity.curses.error if activity.curses else Exception,
        A_BOLD=1, A_REVERSE=2, A_DIM=4, COLORS=256,
        KEY_DOWN=258, KEY_UP=259, KEY_RIGHT=261, KEY_LEFT=260,
        KEY_NPAGE=338, KEY_PPAGE=339, has_colors=lambda: False,
        color_pair=lambda number: 0, curs_set=lambda state: None)


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

    def test_needs_reads_the_work_queue_table(self):
        with tempfile.TemporaryDirectory(prefix="needs-", dir="/tmp/opencode") as temp:
            path = Path(temp) / "work-queue.md"
            path.write_text(
                "# Work queue\n\n## Needs James\n\n"
                "| Need | Blocks | What the answer changes |\n"
                "| --- | --- | --- |\n"
                "| Which speakers | The speaker bay | A measured fit |\n"
                "| a row with two cells | only one |\n"
                "\n## Unattended research\n| not | a need | at all |\n")
            needs = activity._needs(path)
        self.assertEqual(needs["error"], None)
        self.assertEqual([item["need"] for item in needs["items"]], ["Which speakers"])
        self.assertEqual(needs["items"][0]["blocks"], "The speaker bay")
        self.assertEqual(needs["skipped"], 1)
        lines = activity._needs_lines(needs)
        self.assertIn("Which speakers", "\n".join(lines))
        self.assertIn("1 further row(s) could not be read", "\n".join(lines))

    def test_needs_separates_true_blockers_from_confirmations(self):
        with tempfile.TemporaryDirectory(prefix="needs-", dir="/tmp/opencode") as temp:
            path = Path(temp) / "work-queue.md"
            path.write_text(
                "# Work queue\n\n## Needs James\n\n"
                "### True blockers\n\n"
                "| Need | Blocks | What the answer changes |\n| --- | --- | --- |\n"
                "| A real blocker | Everything | The plan |\n\n"
                "### Please confirm\n\n"
                "| Need | Blocks | What the answer changes |\n| --- | --- | --- |\n"
                "| A guess | A stated assumption | The exact fit |\n")
            needs = activity._needs(path)
        self.assertEqual([(item["need"], item["kind"]) for item in needs["items"]],
                         [("A real blocker", "blocker"), ("A guess", "confirm")])
        text = "\n".join(activity._needs_lines(needs))
        self.assertIn("### True blockers", text)
        self.assertIn("### Please confirm", text)
        self.assertIn("Working assumption: A stated assumption", text)
        self.assertNotIn("Blocks: A stated assumption", text)

    def test_needs_says_so_when_there_is_nothing_or_no_section(self):
        with tempfile.TemporaryDirectory(prefix="needs-", dir="/tmp/opencode") as temp:
            empty = Path(temp) / "empty.md"
            empty.write_text("## Needs James\n\n| Need | Blocks | What the answer changes |\n| --- | --- | --- |\n")
            self.assertEqual(activity._needs(empty)["items"], [])
            self.assertIn("Nothing is waiting on James",
                          "\n".join(activity._needs_lines(activity._needs(empty))))
            absent = Path(temp) / "absent.md"
            absent.write_text("# Work queue\n\nno table here\n")
            self.assertIn("no Needs James section", activity._needs(absent)["error"])
            self.assertIn("not readable", activity._needs(Path(temp) / "missing.md")["error"])

    def test_render_puts_the_needs_section_first(self):
        text = activity.render(8787, 3).splitlines()
        first_section = next(line for line in text if line.startswith("## "))
        self.assertTrue(first_section.startswith("## What I need from you"), first_section)

    def test_two_clock_helpers_do_not_shadow_each_other(self):
        # A refactor once added a second _seconds_since, which shadowed the
        # UTC-string one the runner uses; the suite stayed green while the
        # runner's elapsed time silently became None. Both names must work.
        stamp = time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime(time.time() - 90))
        self.assertIsInstance(activity._seconds_since(stamp), int)
        self.assertAlmostEqual(activity._seconds_ago(time.time() - 90), 90, places=3)

    def test_a_running_task_reports_its_elapsed_time_in_words(self):
        # The reviewer showed my first attempt could not fail: no running-task
        # fixture was built, and joining a string inserted newlines between its
        # characters. This renders a real snapshot instead.
        def render_with(elapsed_s):
            run = {"error": None, "running": {"task": "T1", "title": "A task",
                                              "since": "2026-11-15T15:00:00Z",
                                              "elapsed_s": elapsed_s, "model": "m"},
                   "pending": [], "done": 1, "total": 1, "cap": None,
                   "spent_today": 0.0, "recent": [], "stop_file": False}
            with mock.patch.object(activity, "runner_snapshot", return_value=run), \
                 mock.patch.object(activity, "sessions_snapshot",
                                   return_value={"error": None, "sessions": []}), \
                 mock.patch.object(activity, "web_snapshot",
                                   return_value={"port": 8787, "listening": False}):
                return activity.render(8787, 5)

        # The clock is rendered in local time, so only the elapsed part is fixed.
        self.assertIn(" local (1m 30s ago) · model `m`", render_with(90))
        unreadable = render_with(None)
        self.assertIn("(start time not readable)", unreadable)
        self.assertNotIn("unknown ago", unreadable)

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
        # Each column starts at the room a real value needs, so the floor is the
        # larger of the minimum and the useful width, not the bare minimum.
        floors = [max(low, useful) for low, useful in
                  zip(activity.TUI_MIN_WIDTHS, activity.TUI_USEFUL_WIDTHS)]
        floor_total = sum(floors) + 6 * len(activity.TUI_SEPARATOR)
        self.assertIsNone(activity._tui_widths(floor_total - 1))
        self.assertEqual(activity._tui_widths(floor_total), floors)
        # A narrower terminal cannot hold all seven at their useful widths; that
        # is what _tui_visible_columns is for, not a truncation of every column.
        for width in (floor_total, 80, 120, 200):
            with self.subTest(width=width):
                sizes = activity._tui_widths(width)
                self.assertEqual(len(sizes), 7)
                self.assertLessEqual(sum(sizes) + 6 * len(activity.TUI_SEPARATOR), width)
                for size, low, high in zip(sizes, floors, activity.TUI_MAX_WIDTHS):
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
        # The "too small" boundary is the bare minimums: below it there is no
        # honest table, above it a cramped table still beats a blank screen.
        essential = [activity.TUI_MIN_WIDTHS[index]
                     for index in activity.TUI_ESSENTIAL_COLUMNS]
        minimum = sum(essential) + (len(essential) - 1) * len(activity.TUI_SEPARATOR)
        self.assertTrue(activity._tui_too_small(0, 0))
        self.assertTrue(activity._tui_too_small(5, minimum))
        self.assertTrue(activity._tui_too_small(6, minimum - 1))
        # Two rules, a title, a tab bar and a footer leave one content row.
        self.assertFalse(activity._tui_too_small(6, minimum))
        self.assertFalse(activity._tui_too_small(24, 80))

    def test_recent_session_tie_keeps_markdown_idle_before_unknown(self):
        unknown = self.session("unknown-session", working=None, updated=1)
        idle = self.session("idle-session", working=False, updated=1)
        text = self.render_with_sessions([unknown, idle])
        self.assertLess(text.index("idle-session"), text.index("unknown-session"))

    def test_tui_paint_writes_only_the_lines_that_changed(self):
        screen = RecordingScreen()
        first = {0: [(0, "title", 1)], 3: [(0, "row a", 0), (6, "|", 0)]}
        screen.writes.clear()
        frame = activity._tui_paint(screen, first, None, 20)
        # A blanked screen needs its pieces, not a fresh blank before each line.
        self.assertEqual(sorted({y for y, _x, _text in screen.writes}), [0, 3])
        self.assertEqual(len(screen.writes), 3)
        screen.writes.clear()
        self.assertEqual(activity._tui_paint(screen, first, frame, 20), frame)
        self.assertEqual(screen.writes, [])  # an unchanged refresh writes nothing
        second = {0: [(0, "title", 1)], 3: [(0, "row b", 0), (6, "|", 0)]}
        screen.writes.clear()
        activity._tui_paint(screen, second, frame, 20)
        self.assertEqual([y for y, _x, _text in screen.writes], [3, 3, 3])
        gone = {0: [(0, "title", 1)]}
        screen.writes.clear()
        activity._tui_paint(screen, gone, second, 20)
        self.assertEqual(screen.writes, [(3, 0, " " * 20)])

    def test_tui_screen_erases_only_when_the_terminal_resizes(self):
        screen = RecordingScreen(keys=[-1] * 12 + [ord("q")])
        banner = "# What is running — now\n\n## What I need from you (0)\n"
        with mock.patch.object(activity, "render", return_value=banner), \
             mock.patch.object(activity, "write"), \
             mock.patch.object(activity, "curses", fake_curses()):
            activity._tui_screen(screen, 8787, 24, 60.0, False)
        self.assertEqual(screen.erases, 1)

    def test_tui_wrapped_bullet_keeps_its_hanging_indent(self):
        rows = activity._tui_lines(
            {"entries": [("text", "• " + "word " * 20, "bold")]}, 30)
        self.assertGreater(len(rows), 1)
        self.assertTrue(rows[0][1].startswith("• "))
        for row in rows[1:]:
            self.assertTrue(row[1].startswith("  "), row)

    def test_tui_wrapped_sublines_keep_the_report_indentation(self):
        rows = activity._tui_lines(
            {"entries": [("text", "  Blocks: " + "word " * 20, "normal")]}, 30)
        self.assertTrue(rows[0][1].startswith("  Blocks:"))
        for row in rows[1:]:
            self.assertTrue(row[1].startswith("  "), row)

    def test_tui_narrow_terminals_drop_columns_instead_of_truncating_values(self):
        self.assertEqual(activity._tui_visible_columns(140), [0, 1, 2, 3, 4, 5, 6])
        narrow = activity._tui_visible_columns(60)
        self.assertIn(2, narrow)  # Title
        self.assertIn(6, narrow)  # Why
        self.assertNotIn(3, narrow)  # Model goes before it can read "terr…"
        widths = activity._tui_widths(60, narrow)
        self.assertIsNotNone(widths)
        for width, index in zip(widths, narrow):
            self.assertGreaterEqual(width, activity.TUI_USEFUL_WIDTHS[index])

    def test_tui_model_column_fits_the_real_value_that_matters(self):
        # "terra·flex-high" is 15 cells; the variant is what distinguishes it.
        session = {"id": "a", "title": "Some session", "agent": "", "model": "",
                   "provider": "", "model_id": "openrouter/openai/gpt-6.1-terra",
                   "variant": "flex-high", "cost": 0.4,
                   "created": 1, "tokens": 0, "updated": 2, "child": True,
                   "parent": "b", "working": False, "busy_at": None, "idle_at": None}
        cells = activity._tui_session_cells(session, {"a": session}, 10.0)
        self.assertEqual(cells[3], "terra·flex-high")
        tab = {"entries": [("header", list(activity.TUI_HEADERS)),
                           ("row", cells, 0)]}
        needs = activity._tui_needs(tab)
        shown = activity._tui_visible_columns(80, needs)
        self.assertIn(3, shown)
        widths = activity._tui_widths(80, shown, needs)
        self.assertGreaterEqual(widths[shown.index(3)], len("terra·flex-high"))

    def test_tui_essential_columns_survive_a_narrow_terminal(self):
        shown = activity._tui_visible_columns(28)
        self.assertEqual(shown, activity.TUI_ESSENTIAL_COLUMNS)
        self.assertIsNone(activity._tui_widths(28, shown))
        self.assertFalse(activity._tui_too_small(10, 30))

    def test_tui_markdown_table_becomes_aligned_text(self):
        entries = activity._tui_table_entries(
            ["| Task | Status |", "| --- | --- |", "| `a` | done |", "| bbbbbb | new |"])
        self.assertEqual([entry[1] for entry in entries],
                         ["Task   | Status", "a      | done", "bbbbbb | new"])
        self.assertEqual(entries[0][2], "bold")
        self.assertEqual(entries[1][2], "normal")

    def test_tui_tabs_draw_no_markdown_table_pipes(self):
        text = ("# What is running\n\n## Research runner\n"
                "| Recent task | Status |\n| --- | --- |\n| `T1` | done |\n")
        tabs = {tab["label"]: tab for tab in activity._tui_tabs(text, {}, 5)}
        drawn = "\n".join(entry[1] for entry in tabs["Research"]["entries"])
        self.assertNotIn("---", drawn)
        self.assertNotIn("`", drawn)
        self.assertRegex(drawn, r"T1\s+\| done")  # padded under "Recent task"

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

    def test_a_terminal_gets_the_tabbed_view_unless_markdown_is_asked_for(self):
        output = io.StringIO()
        with mock.patch.object(output, "isatty", return_value=True), \
             mock.patch.object(activity.curses, "wrapper") as wrapper, \
             mock.patch.object(activity, "render", return_value="# snapshot") as render, \
             mock.patch.object(activity, "write", return_value=Path("/tmp/opencode/x.md")), \
             mock.patch.dict(os.environ, {"NO_COLOR": "1"}), \
             contextlib.redirect_stdout(output):
            self.assertEqual(activity.main(["--interval", "0.5", "--limit", "3"]), 0)
            # No flag needed: a terminal gets the view the view exists for.
            wrapper.assert_called_once_with(activity._tui_screen, 8787, 3, 0.5, False)
            render.assert_not_called()
            self.assertEqual(activity.main(["--markdown"]), 0)
            render.assert_called_once()
        self.assertIn("# snapshot", output.getvalue())
        self.assertIn("(written to /tmp/opencode/x.md)", output.getvalue())

    def test_watch_on_a_terminal_is_the_tabbed_view(self):
        output = io.StringIO()
        with mock.patch.object(output, "isatty", return_value=True), \
             mock.patch.object(activity.curses, "wrapper") as wrapper, \
             mock.patch.object(activity, "render") as render, \
             contextlib.redirect_stdout(output):
            self.assertEqual(activity.main(["--watch", "2"]), 0)
        wrapper.assert_called_once()
        render.assert_not_called()

    def test_tabs_split_the_report_and_keep_a_fixed_order(self):
        # Built from a synthetic report, not the live one: the needs list changes
        # whenever James answers a question, and a test pinned to it rots.
        report = "\n".join([
            "# What is running — 2026-11-15 16:00:00", "",
            "## What I need from you (1)",
            "- **A question only James can answer**",
            "  Blocks: something",
            "", "## Research runner", "- **Idle** — no task is running at this moment.", "",
            "## Agent sessions",
            "- 0 working · 0 idle · 0 unknown · 0 known sessions",
            "| State | Kind |", "| --- | --- |", "| idle | main |",
            "- `working` is a turn in progress.", "",
            "## Development web server", "- Not listening on port 8787", ""])
        meta = {"agents": {"error": None, "sessions": []}, "rates": {}}
        tabs = activity._tui_tabs(report, meta, 3)
        self.assertEqual([tab["label"] for tab in tabs],
                         ["Needs", "Sessions", "Research", "Status"])
        needs = "\n".join(entry[1] for entry in tabs[0]["entries"] if entry[0] == "text")
        self.assertIn("A question only James can answer", needs)
        # The section heading becomes the tab label, not a line inside it.
        self.assertNotIn("## What I need from you", needs)

    def test_tab_order_does_not_follow_the_report_order(self):
        report = ("# T\n\n## Development web server\n- web\n\n## Research runner\n- run\n\n"
                  "## What I need from you\n- need\n")
        meta = {"agents": {"error": None, "sessions": []}, "rates": {}}
        labels = [tab["label"] for tab in activity._tui_tabs(report, meta, 3)]
        self.assertEqual(labels, ["Needs", "Research", "Status"])

    def test_sessions_tab_rebuilds_the_table_instead_of_reusing_pipes(self):
        session = {"id": "a", "title": "A session", "agent": "", "model": "",
                   "provider": "", "model_id": "m", "variant": "", "cost": 0.01,
                   "created": 1, "tokens": 0, "updated": 2, "child": False,
                   "parent": "", "working": True, "busy_at": None, "idle_at": None}
        meta = {"agents": {"error": None, "sessions": [session]}, "rates": {}}
        with mock.patch.object(activity, "sessions_snapshot",
                               return_value={"error": None, "sessions": [session]}), \
             mock.patch.object(activity, "web_snapshot",
                               return_value={"port": 8787, "listening": False}):
            text = activity.render(8787, 3)
        tabs = activity._tui_tabs(text, meta, 3)
        sessions = next(tab for tab in tabs if tab["label"] == "Sessions")
        rows = [entry for entry in sessions["entries"] if entry[0] == "row"]
        self.assertEqual(len(rows), 1)
        self.assertEqual(rows[0][1][2], "A session")
        self.assertFalse(any(entry[0] == "text" and entry[1].startswith("|")
                             for entry in sessions["entries"]))

    def test_scroll_stays_inside_the_tab_and_survives_a_refresh(self):
        # The complaint this exists for: a refresh used to throw away the
        # position, so a long list meant scrolling again every two seconds.
        self.assertEqual(activity._tui_clamp(0, 100, 20), 0)
        self.assertEqual(activity._tui_clamp(500, 100, 20), 80)
        self.assertEqual(activity._tui_clamp(-5, 100, 20), 0)
        self.assertEqual(activity._tui_clamp(10, 5, 20), 0)
        # Shorter content (a finished task gone) clamps rather than blanking.
        self.assertEqual(activity._tui_clamp(80, 60, 20), 40)

    def test_keys_map_to_actions_without_a_terminal(self):
        keys = activity._tui_key_action
        self.assertEqual(keys(ord("q"), 4), ("quit", 0))
        self.assertEqual(keys(ord("j"), 4), ("scroll", 1))
        self.assertEqual(keys(ord("k"), 4), ("scroll", -1))
        self.assertEqual(keys(9, 4), ("tab", 1))
        self.assertEqual(keys(ord("h"), 4), ("tab", -1))
        self.assertEqual(keys(ord("3"), 4), ("select", 2))
        self.assertEqual(keys(ord("9"), 4), None)
        self.assertEqual(keys(ord(" "), 4), ("pause", 0))
        self.assertEqual(keys(ord("r"), 4), ("refresh", 0))
        self.assertEqual(keys(ord("x"), 4), ("check", 0))
        self.assertEqual(keys(ord("u"), 4), ("unchecked", 0))
        self.assertEqual(keys(ord("z"), 4), None)

    def test_the_six_tabs_still_fit_a_default_eighty_column_terminal(self):
        # Adding a tab is cheap until the bar silently degrades to numbers on
        # the most common terminal width, so the labels have to still fit.
        tabs = [{"label": label} for _heading, label in activity.TUI_TABS]
        bar = activity._tui_tab_bar(tabs, 0, 80)
        for label in ("Needs", "Notices", "Todos", "Sessions", "Research", "Status"):
            self.assertIn(label, bar)

    def test_tab_bar_degrades_to_numbers_when_narrow(self):
        tabs = [{"label": "Needs *", "entries": []}, {"label": "Sessions *", "entries": []}]
        wide = activity._tui_tab_bar(tabs, 0, 80)
        self.assertIn("Needs", wide)
        narrow = activity._tui_tab_bar(tabs, 1, 10)
        self.assertEqual(narrow, "1 [2]")

    def test_watch_prints_an_unchanged_page_once_even_as_the_clock_moves(self):
        # The clock on the title line must not count as a change: it moves every
        # tick, and treating it as one filled logs with identical pages.
        ticks = {"count": 0}

        def render(_port, _limit, _meta):
            ticks["count"] += 1
            return (f"# What is running — 16:00:{ticks['count']:02d}\n\n"
                    "## What I need from you (0)\n- nothing\n")

        def sleep(_seconds):
            if ticks["count"] >= 5:
                raise KeyboardInterrupt

        output = io.StringIO()
        with mock.patch.object(activity, "render", side_effect=render), \
             mock.patch.object(activity, "write"), \
             mock.patch.object(activity.time, "sleep", side_effect=sleep), \
             contextlib.redirect_stdout(output):
            with self.assertRaises(KeyboardInterrupt):
                activity.main(["--watch", "1", "--markdown"])
        self.assertEqual(output.getvalue().count("- nothing"), 1)

    def test_watch_prints_again_when_the_report_actually_changes(self):
        ticks = {"count": 0}

        def render(_port, _limit, _meta):
            ticks["count"] += 1
            body = "one" if ticks["count"] < 3 else "two"
            return f"# What is running — 16:00:{ticks['count']:02d}\n\n- {body}\n"

        def sleep(_seconds):
            if ticks["count"] >= 5:
                raise KeyboardInterrupt

        output = io.StringIO()
        with mock.patch.object(activity, "render", side_effect=render), \
             mock.patch.object(activity, "write"), \
             mock.patch.object(activity.time, "sleep", side_effect=sleep), \
             contextlib.redirect_stdout(output):
            with self.assertRaises(KeyboardInterrupt):
                activity.main(["--watch", "1", "--markdown"])
        printed = output.getvalue()
        self.assertEqual(printed.count("- one"), 1)
        self.assertEqual(printed.count("- two"), 1)

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

    def test_tui_tabs_keep_order_limit_headings_and_supporting_sections(self):
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
        tabs = activity._tui_tabs(text, meta, 3)
        # Fixed tab order, whatever order the sections appear in the report.
        self.assertEqual([tab["base"] for tab in tabs],
                         ["What I need from you", "Notices", "Todos", "Agent sessions",
                          "Research runner", "Development web server"])
        # The checklist's count comes from the work queue, so only its place and
        # its prefix are this test's business.
        self.assertTrue(tabs[1]["label"].startswith("Notices"))
        entries = tabs[3]["entries"]
        rows = [entry for entry in entries if entry[0] == "row"]
        self.assertEqual([row[1][2] for row in rows], ["newer work", "older work", "recent"])
        self.assertEqual(rows[0][2], 2)
        self.assertIn(("header", activity.TUI_HEADERS), entries)
        status = "\n".join(entry[1] for entry in tabs[5]["entries"] if entry[0] == "text")
        self.assertIn("Not listening on port 8787", status)

    def test_tui_tabs_report_unavailable_sessions(self):
        meta = {}
        with mock.patch.object(activity, "sessions_snapshot",
                               return_value={"error": "opencode unavailable", "sessions": []}), \
             mock.patch.object(activity, "web_snapshot",
                               return_value={"port": 8787, "listening": False}):
            text = activity.render(8787, 24, meta)
        tabs = {tab["label"]: tab for tab in activity._tui_tabs(text, meta, 24)}
        self.assertIn(("text", "opencode unavailable", "dim"),
                      tabs["Sessions"]["entries"])
        self.assertIn("Status", tabs)


class TodosTests(unittest.TestCase):
    """The Todos tab: what could run next, read from files that already say so."""

    def setUp(self):
        self._tmp = tempfile.TemporaryDirectory(prefix="todos-", dir="/tmp/opencode")
        self.root = Path(self._tmp.name)
        self.addCleanup(self._tmp.cleanup)

    def empty_todos(self, **overrides):
        base = {
            "chains": {"error": None, "policy": None, "claims": [], "chains": []},
            "queued": {"items": [], "skipped": 0, "error": None},
            "backlog": {"error": None, "ready": [], "unqueued": [], "not_ready": [],
                        "queued": 0, "malformed": 0},
        }
        base.update(overrides)
        return base

    def write_backlog(self, body, queue=(), state=()):
        path = self.root / "backlog.md"
        path.write_text("# Research backlog\n\n```debra-research-backlog\n"
                        + body + "\n```\n")
        (self.root / "queue.json").write_text(
            json.dumps({"tasks": [{"id": task} for task in queue]}))
        (self.root / "state.json").write_text(
            json.dumps({"tasks": {task: {"status": "done"} for task in state}}))
        return path

    def test_queued_work_reads_the_table_and_counts_what_it_cannot_read(self):
        path = self.root / "work-queue.md"
        path.write_text(
            "# Work queue\n\n## Queued\n\n"
            "| Packet | Item ids | Why it is next |\n| --- | --- | --- |\n"
            "| Acceptance review | — | must follow the contract |\n"
            "| a row with two cells | only one |\n"
            "\n## In review\n| not | queued | here |\n")
        queued = activity._queued_work(path)
        self.assertEqual([(item["packet"], item["ids"], item["why"])
                          for item in queued["items"]],
                         [("Acceptance review", "—", "must follow the contract")])
        self.assertEqual(queued["skipped"], 1)
        other = self.root / "other.md"
        other.write_text("# Work queue\n\nnothing here\n")
        self.assertIn("no Queued section", activity._queued_work(other)["error"])
        self.assertIn("not readable", activity._queued_work(self.root / "gone.md")["error"])

    def test_chain_groups_name_what_is_missing(self):
        def row(**changes):
            base = {"id": "x", "starter": "R01", "packet_state": "ready", "reason": "",
                    "packets": ["R01"], "output": "docs/x.md", "waiting_on": []}
            base.update(changes)
            return base
        self.assertEqual(activity._chain_group(row(), set())[0], "eligible")
        self.assertEqual(activity._chain_group(row(), {"x"})[0], "worked")
        self.assertEqual(activity._chain_group(row(starter=None), set())[0], "carded")
        self.assertEqual(activity._chain_group(row(packet_state="review"), set())[0], "review")
        self.assertEqual(activity._chain_group(row(packet_state="done"), set())[0], "carded")
        self.assertEqual(activity._chain_group(row(packet_state="blocked"), set())[0], "blocked")
        group, why = activity._chain_group(
            row(reason="R01: roadmap prerequisites/state do not permit dispatch"), set())
        self.assertEqual(group, "blocked")
        self.assertIn("prerequisites", why)

    def test_backlog_offers_only_new_ready_studies(self):
        path = self.write_backlog(
            "R01-OLD | ready | Already run | A scope long enough for the backlog format.\n"
            "R02-NEW | ready | Waiting to run | A scope long enough for the backlog format.\n"
            "N01-SLOW | not-ready | Needs a person | A scope long enough for the backlog format.\n"
            "R02-NEW | ready | Duplicate id | A scope long enough for the backlog format.\n"
            "this line is malformed",
            queue=("R01-OLD",))
        with mock.patch.object(runner, "BACKLOG_PATH", path), \
             mock.patch.object(runner, "QUEUE_PATH", self.root / "queue.json"), \
             mock.patch.object(runner, "STATE_PATH", self.root / "state.json"):
            snapshot = activity.backlog_snapshot()
        self.assertIsNone(snapshot["error"])
        self.assertEqual([entry["id"] for entry in snapshot["ready"]], ["R01-OLD", "R02-NEW"])
        self.assertEqual([entry["id"] for entry in snapshot["unqueued"]], ["R02-NEW"])
        self.assertEqual([entry["id"] for entry in snapshot["not_ready"]], ["N01-SLOW"])
        self.assertEqual(snapshot["queued"], 1)
        self.assertEqual(snapshot["malformed"], 1)

    def test_a_study_the_runner_already_finished_is_not_offered_again(self):
        path = self.write_backlog(
            "Z01-DONE | ready | Already studied | A scope long enough for the backlog format.",
            state=("Z01-DONE",))
        with mock.patch.object(runner, "BACKLOG_PATH", path), \
             mock.patch.object(runner, "QUEUE_PATH", self.root / "queue.json"), \
             mock.patch.object(runner, "STATE_PATH", self.root / "state.json"):
            snapshot = activity.backlog_snapshot()
        self.assertEqual(snapshot["unqueued"], [])
        self.assertEqual(snapshot["queued"], 1)

    def test_backlog_that_cannot_be_read_is_reported_not_hidden(self):
        path = self.root / "backlog.md"
        path.write_text("# no backlog block here\n")
        with mock.patch.object(runner, "BACKLOG_PATH", path):
            snapshot = activity.backlog_snapshot()
        self.assertIn("not readable", snapshot["error"])
        self.assertIn("not readable", "\n".join(activity._todos_lines(
            self.empty_todos(backlog=snapshot))))

    def test_chains_snapshot_asks_the_dispatcher_instead_of_redeciding(self):
        catalog = [
            {"id": "zero-w", "packets": ["Z01", "Z02"], "starter": "Z01",
             "output": "docs/research/Z01-armv6.md"},
            {"id": "audio", "packets": ["A01"]},
        ]
        tasks = {"Z01": ("ready", []), "Z02": ("blocked", ["Z01"]), "A01": ("blocked", [])}
        state = {"version": 1, "policy": None,
                 "claims": {"c1": {"chain": "zero-w", "packet": "Z01",
                                   "status": "active", "owner": "worker"}}}
        with mock.patch.object(activity.taskchain, "catalog", return_value=(catalog, tasks)), \
             mock.patch.object(activity.taskchain, "common_dir", return_value=self.root), \
             mock.patch.object(activity.taskchain, "read_state", return_value=state), \
             mock.patch.object(activity.taskchain, "reason",
                               side_effect=lambda chain, _tasks, _state: ""):
            snapshot = activity.chains_snapshot()
        self.assertIsNone(snapshot["error"])
        self.assertEqual([claim["owner"] for claim in snapshot["claims"]], ["worker"])
        by_id = {row["id"]: row for row in snapshot["chains"]}
        self.assertEqual(by_id["zero-w"]["packet_state"], "ready")
        self.assertIsNone(by_id["audio"]["starter"])
        lines = "\n".join(activity._todos_lines(self.empty_todos(chains=snapshot)))
        self.assertIn("Being worked on (1)", lines)
        self.assertIn("zero-w (active)", lines)
        self.assertIn("No card written yet (1)", lines)
        self.assertIn("`audio`", lines)

    def test_an_unreadable_registry_keeps_the_rest_of_the_page(self):
        with mock.patch.object(activity.taskchain, "catalog",
                               side_effect=ValueError("no roadmap packets")):
            snapshot = activity.chains_snapshot()
        self.assertIn("no roadmap packets", snapshot["error"])
        lines = "\n".join(activity._todos_lines(self.empty_todos(chains=snapshot)))
        self.assertIn("Task chains not readable", lines)
        self.assertIn("Queued work packets (0)", lines)

    def test_todos_lines_separate_the_three_channels(self):
        todos = self.empty_todos(
            chains={"error": None, "policy": None, "claims": [], "chains": [
                {"id": "zero-w", "packets": ["Z01", "Z02"], "starter": "Z01",
                 "output": "docs/research/Z01-armv6.md", "packet_state": "ready",
                 "reason": "", "waiting_on": []},
                {"id": "recovery", "packets": ["B01"], "starter": "B01",
                 "output": "docs/research/B01-recovery.md", "packet_state": "review",
                 "reason": "B01: roadmap prerequisites/state do not permit dispatch",
                 "waiting_on": []}]},
            queued={"items": [{"packet": "Device run", "ids": "N02",
                               "why": "needs a spare card"}], "skipped": 0, "error": None},
            backlog={"error": None, "ready": [{"id": "R01", "title": "Study"}],
                     "unqueued": [{"id": "R01", "title": "Study"}],
                     "not_ready": [{"id": "A03", "title": "Needs a device"}],
                     "queued": 0, "malformed": 1})
        text = "\n".join(activity._todos_lines(todos))
        self.assertIn("2 task chains; **none is being worked on right now**", text)
        self.assertIn("The claim registry is **closed**", text)
        self.assertIn("Ready to claim once dispatch opens (1)", text)
        self.assertIn("docs/work/cards/Z01.md", text)
        self.assertIn("Deliverable landed, waiting for review (1)", text)
        self.assertIn("Queued work packets (1)", text)
        self.assertIn("**Device run** (N02) — needs a spare card", text)
        self.assertIn("Unattended research (1 ready to queue)", text)
        self.assertIn("`A03`", text)
        self.assertIn("1 malformed backlog line(s) were skipped.", text)
        self.assertNotIn("### Being worked on", text)

    def test_an_open_registry_stops_claiming_it_is_closed(self):
        todos = self.empty_todos(chains={
            "error": None, "claims": [],
            "policy": {"base": "abc1234", "model": "provider/model#variant"},
            "chains": [{"id": "zero-w", "packets": ["Z01"], "starter": "Z01",
                        "output": "docs/research/Z01-armv6.md", "packet_state": "ready",
                        "reason": "", "waiting_on": []}]})
        text = "\n".join(activity._todos_lines(todos))
        self.assertIn("claim registry is open for base `abc1234`", text)
        self.assertNotIn("**closed**", text)
        self.assertIn("### Ready to claim (1)", text)

    def test_the_report_and_the_tab_share_one_todos_section(self):
        meta = {}
        with mock.patch.object(activity, "sessions_snapshot",
                               return_value={"error": None, "sessions": []}), \
             mock.patch.object(activity, "web_snapshot",
                               return_value={"port": 8787, "listening": False}), \
             mock.patch.object(activity, "todos_snapshot",
                               return_value=self.empty_todos()):
            text = activity.render(8787, 3, meta)
        self.assertIn("## Todos", text)
        tabs = {tab["base"]: tab for tab in activity._tui_tabs(text, meta, 3)}
        self.assertIn("Todos", tabs)
        self.assertIn("task chains",
                      "\n".join(entry[1] for entry in tabs["Todos"]["entries"]))

    def test_todos_flag_prints_only_that_section(self):
        with mock.patch.object(activity, "todos_snapshot",
                               return_value=self.empty_todos()), \
             contextlib.redirect_stdout(io.StringIO()) as output:
            self.assertEqual(activity.main(["--todos"]), 0)
        text = output.getvalue()
        self.assertTrue(text.startswith("## Todos"))
        self.assertNotIn("## Agent sessions", text)
        self.assertNotIn("## Research runner", text)


if __name__ == "__main__":
    unittest.main()

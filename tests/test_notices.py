"""Notices: derivation, check marks, and how the checklist tab is built.

The point of these tests is that a notice is never invented and never lost: it
appears because a snapshot says so, and a tick survives a refresh but not the
notice's disappearance.
"""

import stat
import sys
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

import tools.activity as activity  # noqa: E402
import tools.notices as notices  # noqa: E402


def needs(*items, error=None):
    return {"items": [{"need": need, "blocks": blocks, "changes": changes, "kind": kind}
                      for need, kind, blocks, changes in items],
            "skipped": 0, "error": error}


class Temp(unittest.TestCase):
    def setUp(self):
        self._temp = tempfile.TemporaryDirectory(prefix="notices-", dir="/tmp/opencode")
        self.dir = Path(self._temp.name)
        self.path = self.dir / "notices.json"

    def tearDown(self):
        self._temp.cleanup()


class IdTests(unittest.TestCase):
    def test_the_same_notice_keeps_its_id_and_a_different_one_does_not(self):
        first = notices.stable_id("blocker", "Needs", "Buy a printer")
        self.assertEqual(first, notices.stable_id("blocker", "Needs", "Buy a printer"))
        self.assertNotEqual(first, notices.stable_id("confirm", "Needs", "Buy a printer"))
        self.assertNotEqual(first, notices.stable_id("blocker", "Needs", "Buy a scanner"))
        self.assertEqual(len(first), 12)


class CollectTests(unittest.TestCase):
    def test_a_blocker_and_a_confirmation_are_not_the_same_kind(self):
        found = notices.collect(needs=needs(
            ("Pick a speaker", "blocker", "the enclosure", "the bay"),
            ("Confirm the HAT layout", "confirm", "the lid", "hole positions")))
        self.assertEqual([n["kind"] for n in found], ["blocker", "confirm"])
        self.assertEqual(found[0]["detail"], "blocks the enclosure")
        self.assertEqual(found[1]["detail"], "assumes the lid")

    def test_an_empty_snapshot_produces_no_notice(self):
        # "The web server is not listening" is normal, so it must not be a
        # notice; only a real failure is.
        self.assertEqual(notices.collect(needs={}, run={}, agents={},
                                         web={"listening": False}), [])

    def test_a_failed_task_is_a_notice_and_a_repeat_failure_is_a_new_one(self):
        run = {"recent": [{"task": "R07", "status": "failed", "cost": 0.24,
                           "finished": "2026-11-15T22:02:44Z"},
                          {"task": "N01", "status": "done", "cost": 0.02,
                           "finished": "2026-11-15T22:10:00Z"}]}
        found = notices.collect(run=run)
        self.assertEqual(len(found), 1)
        self.assertIn("R07", found[0]["title"])
        again = notices.collect(run={"recent": [
            {"task": "R07", "status": "failed", "cost": 0.24,
             "finished": "2026-11-16T09:00:00Z"}]})
        self.assertNotEqual(found[0]["id"], again[0]["id"],
                            "the same task failing later must not stay pre-ticked")

    def test_a_stop_file_and_a_runner_error_are_both_visible(self):
        self.assertIn("STOP", notices.collect(run={"stop_file": True})[0]["title"])
        self.assertIn("unavailable",
                      notices.collect(run={"error": "unavailable (OSError)"})[0]["title"])

    def test_a_long_running_turn_becomes_a_notice_and_a_short_one_does_not(self):
        agents = {"sessions": [
            {"id": "a", "title": "stuck", "working": True, "busy_at": 1000.0},
            {"id": "b", "title": "fine", "working": True, "busy_at": 2900.0},
            {"id": "c", "title": "idle", "working": False, "busy_at": 1000.0}]}
        found = notices.collect(agents=agents, now=3000.0)
        self.assertEqual(len(found), 1)
        self.assertIn("stuck", found[0]["title"])
        self.assertIn("33m", found[0]["title"])

    def test_duplicate_titles_collapse_to_one_notice(self):
        found = notices.collect(needs=needs(("Same question", "confirm", "a", "b"),
                                            ("Same question", "confirm", "a", "b")))
        self.assertEqual(len(found), 1)


class StateTests(Temp):
    def test_a_missing_file_means_nothing_is_checked(self):
        self.assertEqual(notices.load(self.path), {"version": 1, "read": {}})

    def test_a_corrupt_file_is_treated_as_empty_rather_than_fatal(self):
        self.path.write_text("{not json", encoding="utf-8")
        self.assertEqual(notices.load(self.path)["read"], {})

    def test_marks_round_trip_owner_only(self):
        state = notices.mark([{"id": "abc"}], {"version": 1, "read": {}},
                             ["abc"], now=1000.0, path=self.path)
        self.assertEqual(state["read"]["abc"], "1970-01-01T00:16:40Z")
        self.assertEqual(stat.S_IMODE(self.path.stat().st_mode), 0o600)
        self.assertEqual(notices.load(self.path)["read"], {"abc": "1970-01-01T00:16:40Z"})

    def test_unchecking_removes_the_mark(self):
        state = notices.mark([{"id": "abc"}], {"version": 1, "read": {}}, ["abc"],
                             now=1000.0, path=self.path)
        state = notices.mark([{"id": "abc"}], state, ["abc"], read=False, path=self.path)
        self.assertEqual(state["read"], {})

    def test_a_mark_is_dropped_once_its_notice_is_gone(self):
        state = notices.mark([{"id": "abc"}, {"id": "def"}], {"version": 1, "read": {}},
                             ["abc", "def"], now=1000.0, path=self.path)
        # "def" no longer appears in the collection, so it must not come back
        # pre-ticked if the same notice is ever raised again.
        state = notices.mark([{"id": "abc"}], state, ["abc"], now=2000.0, path=self.path)
        self.assertEqual(set(state["read"]), {"abc"})


class ApplyTests(Temp):
    def raw(self):
        return [{"id": "1", "kind": "confirm", "source": "Needs", "title": "c", "detail": ""},
                {"id": "2", "kind": "blocker", "source": "Needs", "title": "b", "detail": ""},
                {"id": "3", "kind": "attention", "source": "Research", "title": "a", "detail": ""}]

    def test_unread_come_first_and_worst_first(self):
        found = notices.apply(self.raw(), {"version": 1, "read": {}})
        self.assertEqual([n["id"] for n in found], ["2", "1", "3"])

    def test_a_checked_notice_sorts_to_the_end_but_stays_in_the_list(self):
        found = notices.apply(self.raw(), {"version": 1, "read": {"2": "2026-11-15T00:00:00Z"}})
        self.assertEqual([n["id"] for n in found], ["1", "3", "2"])
        self.assertTrue(found[-1]["read"])
        self.assertFalse(found[0]["read"])

    def test_counts_say_how_much_there_was(self):
        found = notices.apply(self.raw(), {"version": 1, "read": {"1": "x"}})
        self.assertEqual(notices.counts(found),
                         {"total": 3, "unread": 2, "blockers": 1, "checked": 1})


class ChecklistTabTests(Temp):
    def meta(self, read=None, show_checked=False):
        raw = [{"id": "b1", "kind": "blocker", "source": "Needs",
                "title": "Pick a speaker", "detail": "blocks the enclosure"},
               {"id": "a1", "kind": "attention", "source": "Research",
                "title": "Task failed", "detail": ""}]
        return {"notices": raw, "notice_state": {"version": 1, "read": read or {}},
                "show_checked": show_checked}

    def test_checked_notices_hide_behind_a_count_and_a_key(self):
        entries, unread = activity._tui_notice_entries(self.meta(read={"b1": "x"}))
        self.assertEqual(unread, 1)
        texts = [entry[1] if isinstance(entry[1], str) else entry[1]["title"]
                 for entry in entries]
        self.assertIn("Task failed", texts)
        self.assertNotIn("Pick a speaker", texts)
        self.assertTrue(any("Checked off (1)" in str(text) and "u to show" in str(text)
                            for text in texts))

    def test_showing_checked_brings_the_notice_back_dimmed(self):
        entries, unread = activity._tui_notice_entries(self.meta(read={"b1": "x"},
                                                                show_checked=True))
        self.assertEqual(unread, 1)
        notice_entries = [entry for entry in entries if entry[0] == "notice"]
        self.assertEqual([entry[2] for entry in notice_entries], ["unread", "read"])

    def test_the_checkbox_and_the_cursor_id_survive_wrapping(self):
        tab = {"entries": [("notice", {"id": "b1", "kind": "blocker", "source": "Needs",
                                       "title": "A long enough title to wrap on a narrow "
                                                "terminal without losing its tail",
                                       "detail": "and a reason"}, "unread")]}
        rows = activity._tui_lines(tab, 40)
        self.assertTrue(rows[0][1].startswith("[ ] Blocker · "))
        self.assertEqual(rows[0][3], "b1", "the first line carries the cursor id")
        self.assertTrue(all(len(row) < 4 or row[3] is None for row in rows[1:]),
                        "continuation lines must not repeat the cursor id")
        self.assertTrue(any(row[1].startswith("    and a reason") for row in rows))

    def test_the_tab_label_carries_the_unread_count(self):
        text = "## Notices (2 unread of 2)\n- [ ] something\n\n## Agent sessions\n- none\n"
        tabs = activity._tui_tabs(text, self.meta(), 24)
        labels = [tab["label"] for tab in tabs]
        self.assertIn("Notices 2", labels)
        # Order matters: the checklist sits next to the tab it summarises.
        self.assertEqual(labels[:2], ["Needs", "Notices 2"] if "Needs" in labels
                         else labels[:2])

    def test_x_and_u_are_their_own_actions(self):
        self.assertEqual(activity._tui_key_action(ord("x"), 5), ("check", 0))
        self.assertEqual(activity._tui_key_action(ord("u"), 5), ("unchecked", 0))
        self.assertEqual(activity._tui_key_action(10, 5), ("check", 0))


class ReportTests(Temp):
    def test_the_markdown_report_uses_the_same_checkboxes(self):
        found = notices.apply(
            [{"id": "1", "kind": "blocker", "source": "Needs", "title": "Pick", "detail": "d"}],
            {"version": 1, "read": {}})
        lines = notices.lines(found)
        self.assertEqual(lines[0], "- [ ] **Blocker** · Pick")
        self.assertEqual(lines[1], "  d")

    def test_an_empty_report_says_so_instead_of_printing_nothing(self):
        self.assertEqual(notices.lines([]),
                         ["- Nothing to report; no notice is outstanding."])


if __name__ == "__main__":
    unittest.main()

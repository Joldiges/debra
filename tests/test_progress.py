"""Offline progress-map checks: tracked sources only, no services or device access."""

import contextlib
import io
from pathlib import Path
import re
import sys
import tempfile
import unittest
from unittest import mock


ROOT = Path(__file__).resolve().parent.parent
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from tools import progress  # noqa: E402


ROADMAP = """## Foundation
| ID / state | Depends on | Deliverable |
| --- | --- | --- |
| F00 / done | — | Accepted foundation |
| F01 / ready | F00 | Ready packet |
| F02 / blocked | F01 | Not started |
| WEB01 / prototype | F01; F02 for writes | Prototype |
"""


class ProgressTests(unittest.TestCase):
    def test_all_packet_prefixes_and_qualified_dependencies(self):
        tasks = progress.parse_roadmap(ROADMAP)
        self.assertEqual(tuple(tasks), ("F00", "F01", "F02", "WEB01"))
        self.assertEqual(tasks["WEB01"].dependencies, ("F01", "F02"))
        self.assertEqual(tasks["WEB01"].conditional, {"F02"})
        self.assertEqual(tasks["WEB01"].progress, "partial")
        self.assertEqual(tasks["F01"].progress, "untouched")
        self.assertEqual(tasks["F02"].progress, "blocked")

    def test_slash_list_is_all_dependencies_unless_qualified(self):
        text = ROADMAP.replace("F01; F02 for writes", "F01/F02")
        task = progress.parse_roadmap(text)["WEB01"]
        self.assertEqual(task.dependencies, ("F01", "F02"))
        self.assertEqual(task.conditional, set())
        text = ROADMAP.replace("F01; F02 for writes", "F01/F02 for final onboarding")
        self.assertEqual(progress.parse_roadmap(text)["WEB01"].conditional, {"F01", "F02"})

    def test_invalid_graphs_fail_instead_of_disappearing(self):
        cases = (
            (ROADMAP + "| F01 / ready | F00 | Duplicate |\n", "Duplicate"),
            (ROADMAP.replace("F02 for writes", "F99 for writes"), "Undefined"),
            (ROADMAP.replace("F00 / done | —", "F00 / done | WEB01"), "cycle"),
            (ROADMAP.replace("F01 / ready", "F01 / mystery"), "Unknown roadmap state"),
            (ROADMAP + "| F99 / in_progress | F00 | New unknown state |\n", "Unknown roadmap state"),
        )
        for text, error in cases:
            with self.subTest(error=error), self.assertRaisesRegex(ValueError, error):
                progress.parse_roadmap(text)

    def test_annotation_retains_gate_and_requires_evidence_and_known_packet(self):
        annotation = """
## Visual progress annotations
| Packet | Progress | Evidence and limits |
| --- | --- | --- |
| F02 | partial | Fixture-only implementation; not accepted |
"""
        task = progress.parse_roadmap(ROADMAP + annotation)["F02"]
        self.assertEqual(task.progress, "partial")
        self.assertEqual(task.state, "blocked")
        for old, new, error in (
            ("F02 | partial", "F99 | partial", "Unknown annotated"),
            ("F02 | partial", "F00 | partial", "Finished packet"),
            ("F02 | partial", "F02 | finished", "Invalid progress"),
            ("Fixture-only implementation; not accepted", "", "Invalid progress"),
        ):
            with self.subTest(error=error), self.assertRaisesRegex(ValueError, error):
                progress.parse_roadmap(ROADMAP + annotation.replace(old, new))

    def test_fenced_sample_rows_are_not_real_tasks(self):
        text = ROADMAP + "\n```md\n## Example\n| F99 / done | — | Sample |\n```\n"
        self.assertNotIn("F99", progress.parse_roadmap(text))

    def test_active_implementation_review_and_subtask_completion_are_separate(self):
        queue = """## Running
| Packet | Item ids | Files | Notes |
| --- | --- | --- | --- |
| Repair browser errors | WEB01 | file | editing |
| Acceptance review `setup-r7` | F01 | file | frozen |
## Done this round
| Subtask | WEB01 | one test passed |
## In review
| Item | Reviewer | Outcome |
| --- | --- | --- |
| WEB01 earlier review | reviewer | changes requested |
| F02 acceptance matrix | — | not yet reviewed |
"""
        states, running = progress.queue_activity(queue, progress.parse_roadmap(ROADMAP))
        self.assertEqual(states, {"WEB01": "running", "F01": "review", "F02": "review"})
        self.assertEqual(len(running), 2)
        self.assertNotIn("finished", states.values())

    def test_stale_finished_or_unknown_active_packet_is_an_error(self):
        for key in ("F00", "F99"):
            with self.subTest(key=key), self.assertRaises(ValueError):
                progress.queue_activity(f"## Running\n| Work | {key} | file |\n",
                                        progress.parse_roadmap(ROADMAP))

    def test_overview_never_calls_mixed_or_review_work_finished(self):
        for states, expected in (
            (["finished"], "finished"), (["finished", "review"], "review"),
            (["review", "blocked"], "partial"), (["partial", "blocked"], "partial"),
            (["running", "blocked"], "running"), (["untouched"], "untouched"),
            (["blocked", "untouched"], "blocked"),
        ):
            with self.subTest(states=states):
                self.assertEqual(progress.aggregate(states), expected)

    def test_graph_includes_external_prerequisites_and_text_labels(self):
        tasks = progress.parse_roadmap(ROADMAP)
        states = {key: task.progress for key, task in tasks.items()}
        graph = progress.graph(tasks, states, ["WEB01"])
        self.assertIn("F01 --> WEB01", graph)
        self.assertIn("F02 -.-> WEB01", graph)
        self.assertNotIn("F00 --> F01", graph)
        self.assertIn("UNTOUCHED", graph)
        self.assertIn("BLOCKED", graph)
        self.assertIn("PARTIAL", graph)
        self.assertNotIn('F00["', graph)
        self.assertIn("flowchart TD", graph)

    def test_wide_fanout_uses_a_vertical_page_layout(self):
        keys = tuple(progress.TITLES)[:17]
        tasks = {key: progress.Task(key, "ready", (), frozenset(), "—", "Fixture", "untouched")
                 for key in keys[:-1]}
        tasks[keys[-1]] = progress.Task(
            keys[-1], "blocked", keys[:-1], frozenset(), ", ".join(keys[:-1]), "Fixture", "blocked")
        states = {key: task.progress for key, task in tasks.items()}
        graph = progress.graph(tasks, states, [keys[-1]])
        self.assertIn("flowchart LR", graph)
        for dependency in keys[:-1]:
            self.assertIn(f"{dependency} --> {keys[-1]}", graph)

    def test_real_sources_cover_every_packet_edge_and_status(self):
        roadmap = (ROOT / "docs/roadmap.md").read_text()
        queue = (ROOT / "docs/work-queue.md").read_text()
        page = progress.render(roadmap, queue)
        tasks = progress.parse_roadmap(roadmap)
        # Independent inventory, rather than trusting the generator to notice an
        # omitted multi-letter prefix or whole row.
        source_ids = set(re.findall(r"^\|\s*([A-Z]+\d{2}) / \w+\s*\|", roadmap, re.M))
        self.assertEqual(set(tasks), source_ids)
        activity, _ = progress.queue_activity(queue, tasks)
        for key, task in tasks.items():
            state = activity.get(key, task.progress)
            with self.subTest(packet=key):
                self.assertIn(f'    {key}["{key} · ', page)
                self.assertIn(f"| {key} · {progress.TITLES[key]} | {progress.STYLES[state][2]} |", page)
                for dep in task.dependencies:
                    arrow = "-.->" if dep in task.conditional else "-->"
                    self.assertEqual(page.count(f"    {dep} {arrow} {key}\n"), 1)

    def test_generated_page_is_current_and_deterministic(self):
        roadmap = (ROOT / "docs/roadmap.md").read_text()
        queue = (ROOT / "docs/work-queue.md").read_text()
        first = progress.render(roadmap, queue)
        self.assertEqual(first, progress.render(roadmap, queue))
        self.assertEqual((ROOT / progress.OUTPUT).read_text(), first,
                         "Run python3 tools/progress.py after updating tracked progress sources")

    def test_check_is_read_only_and_catches_both_sources_changing(self):
        with tempfile.TemporaryDirectory(prefix="progress-", dir="/tmp/opencode") as folder:
            root = Path(folder)
            (root / "docs").mkdir()
            for name in ("roadmap.md", "work-queue.md"):
                (root / "docs" / name).write_text((ROOT / "docs" / name).read_text())
            with mock.patch.object(progress, "ROOT", root), contextlib.redirect_stdout(io.StringIO()), \
                    contextlib.redirect_stderr(io.StringIO()):
                self.assertEqual(progress.main(["--check"]), 1)
                self.assertFalse((root / progress.OUTPUT).exists())
                self.assertEqual(progress.main([]), 0)
                original = (root / progress.OUTPUT).read_bytes()
                self.assertEqual(progress.main(["--check"]), 0)
                for name in ("roadmap.md", "work-queue.md"):
                    path = root / "docs" / name
                    before = path.read_text()
                    path.write_text(before + "\n")
                    self.assertEqual(progress.main(["--check"]), 1)
                    self.assertEqual((root / progress.OUTPUT).read_bytes(), original)
                    path.write_text(before)


if __name__ == "__main__":
    unittest.main()

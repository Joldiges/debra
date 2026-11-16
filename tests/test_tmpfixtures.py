"""Offline tests for tools/tmpfixtures.py.

They build their own throwaway base directory, so they never prune the real
/tmp/opencode fixtures of a running suite.
"""

import os
import sys
import tempfile
import time
import unittest
from pathlib import Path

SOURCE = Path(__file__).resolve().parent.parent
if str(SOURCE) not in sys.path:
    sys.path.insert(0, str(SOURCE))

import tools.tmpfixtures as tmpfixtures  # noqa: E402  (path set above)


class PruneTests(unittest.TestCase):
    def setUp(self):
        self.base = Path(tempfile.mkdtemp(prefix="prune-", dir="/tmp/opencode"))
        self.now = time.time()

    def make(self, name, age):
        path = self.base / name
        path.mkdir()
        (path / "f").write_text("x")
        stamp = self.now - age
        os.utime(path, (stamp, stamp))
        return path

    def test_keeps_the_newest_runs_and_removes_the_rest(self):
        runs = [self.make(f"debra-x-tests-{index:02d}", age=index * 10)
                for index in range(9)]
        removed = tmpfixtures.prune("debra-x-tests-", self.base, keep=3,
                                   grace=10_000, now=self.now)
        self.assertEqual(sorted(path.name for path in removed),
                         sorted(path.name for path in runs[3:]))
        self.assertEqual(sorted(path.name for path in self.base.iterdir()),
                         sorted(path.name for path in runs[:3]))

    def test_removes_stale_runs_even_when_few_exist(self):
        fresh = self.make("debra-x-tests-fresh", age=5)
        stale = self.make("debra-x-tests-stale", age=7_200)
        removed = tmpfixtures.prune("debra-x-tests-", self.base, grace=3_600,
                                   now=self.now)
        self.assertEqual(removed, [stale])
        self.assertTrue(fresh.exists())

    def test_ignores_other_prefixes_and_plain_files(self):
        other = self.make("someone-elses-", age=10_000)
        mine = self.make("debra-x-tests-keep", age=10_000)
        stray = self.base / "debra-x-tests-file"
        stray.write_text("not a directory")
        removed = tmpfixtures.prune("debra-x-tests-", self.base, keep=0,
                                   grace=0, now=self.now)
        self.assertEqual(removed, [mine])
        self.assertTrue(other.exists())
        self.assertTrue(stray.exists())

    def test_never_follows_a_symlink(self):
        target = Path(tempfile.mkdtemp(prefix="prune-target-", dir="/tmp/opencode"))
        (target / "keep.md").write_text("do not delete")
        link = self.base / "debra-x-tests-link"
        link.symlink_to(target, target_is_directory=True)
        removed = tmpfixtures.prune("debra-x-tests-", self.base, keep=0,
                                   grace=0, now=self.now)
        self.assertEqual(removed, [])
        self.assertTrue(link.is_symlink())
        self.assertTrue((target / "keep.md").exists())

    def test_root_prunes_then_creates_a_fresh_directory(self):
        old = self.make("debra-x-tests-old", age=10_000)
        fresh = tmpfixtures.root("debra-x-tests-", self.base, grace=3_600)
        self.assertFalse(old.exists())
        self.assertTrue(fresh.is_dir())
        self.assertTrue(fresh.name.startswith("debra-x-tests-"))
        self.assertEqual(fresh.stat().st_mode & 0o777, 0o700)

    def test_missing_base_is_created_not_fatal(self):
        base = self.base / "does" / "not" / "exist"
        fresh = tmpfixtures.root("debra-x-tests-", base)
        self.assertTrue(fresh.is_dir())
        self.assertEqual(tmpfixtures.prune("debra-x-tests-", self.base / "gone"), [])

    def test_defaults_keep_a_small_number_of_runs(self):
        self.assertGreaterEqual(tmpfixtures.KEEP, 2)
        self.assertLessEqual(tmpfixtures.KEEP, 10)
        self.assertGreaterEqual(tmpfixtures.GRACE_SECONDS, 600)


if __name__ == "__main__":
    unittest.main()

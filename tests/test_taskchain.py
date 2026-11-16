"""Offline Git fixtures only.

Fixtures live under /tmp/opencode. Each run prunes earlier runs, keeping the
newest few (tools/tmpfixtures.py) so a tmpfs cannot run out of inodes.
"""

from concurrent.futures import ThreadPoolExecutor
import json
import os
from pathlib import Path
import re
import shutil
import subprocess
import sys
import tempfile
import unittest


SOURCE = Path(__file__).resolve().parent.parent
if str(SOURCE) not in sys.path:
    sys.path.insert(0, str(SOURCE))

import tools.tmpfixtures as tmpfixtures  # noqa: E402  (path set above)
FIXTURES = tmpfixtures.root("debra-taskchain-tests-")
# cwd alone cannot isolate Git: inherited GIT_DIR/GIT_WORK_TREE/GIT_INDEX_FILE
# can redirect commands into another checkout. Drop every inherited Git override
# and ignore the host's global/system config before running fixture commands.
ENV = {
    **{key: value for key, value in os.environ.items() if not key.startswith("GIT_")},
    "GIT_CONFIG_NOSYSTEM": "1",
    "GIT_CONFIG_SYSTEM": os.devnull,
    "GIT_CONFIG_GLOBAL": os.devnull,
    "GIT_CONFIG_COUNT": "1",
    "GIT_CONFIG_KEY_0": "core.hooksPath",
    "GIT_CONFIG_VALUE_0": os.devnull,
    "GIT_TERMINAL_PROMPT": "0",
}


class DispatcherTests(unittest.TestCase):
    def setUp(self):
        self.repo = Path(tempfile.mkdtemp(prefix="repo-", dir=FIXTURES))
        inputs = [
            "tools/taskchain.py", "docs/work/chains.json", "docs/roadmap.md",
            "AGENTS.md", "docs/task-chains.md", "docs/ai-workflow.md",
            *[str(p.relative_to(SOURCE)) for p in (SOURCE / "docs/work/cards").glob("*.md")],
        ]
        for name in inputs:
            target = self.repo / name
            target.parent.mkdir(parents=True, exist_ok=True)
            shutil.copyfile(SOURCE / name, target)
        (self.repo / ".gitignore").write_text("/.local/\n")
        # The dispatcher tests need eligible starters, and packet states move as
        # work lands. Pin them in the fixture so these tests check the mechanism
        # rather than the project's live review state. R01 is the chain the tests
        # claim by name; R02 is a second one, because `--chain any` has to find a
        # chain other than the claimed one. Relying on whatever else happened to
        # be `ready` broke as soon as T01 and Z01 were accepted.
        roadmap = self.repo / "docs/roadmap.md"
        text = roadmap.read_text()
        for packet in ("R01", "R02"):
            # Set the state whatever it currently is, so accepting a packet in
            # the live roadmap cannot silently unpin the fixture. The match is
            # asserted: an unpinned R02 would leave `--chain any` passing only
            # because some unrelated chain happened to be ready, which is the
            # accident this pin exists to remove.
            text, count = re.subn(rf"^\| {packet} / \w+ \|", f"| {packet} / ready |",
                                  text, count=1, flags=re.MULTILINE)
            self.assertEqual(count, 1, f"the roadmap has no {packet} row to pin")
        roadmap.write_text(text)
        pilot = self.repo / "docs/testing/pilot-fixture.md"
        pilot.parent.mkdir(parents=True)
        pilot.write_text("SYNTHETIC TEST ONLY: not real role/permission verification.\n")
        self.git("init", "--template=")
        self.git("config", "user.name", "Fixture")
        self.git("config", "user.email", "fixture@example.invalid")
        self.git("add", "--", ".")
        self.git("commit", "-m", "isolated fixture baseline")

    def git(self, *args, cwd=None):
        result = subprocess.run(["git", *args], cwd=cwd or self.repo, env=ENV,
                                capture_output=True, text=True)
        self.assertEqual(result.returncode, 0, result.stderr)
        return result.stdout.strip()

    def run_tool(self, *args, cwd=None, ok=True):
        result = subprocess.run(
            [sys.executable, "-B", "tools/taskchain.py", *args],
            cwd=cwd or self.repo, env=ENV, capture_output=True, text=True,
        )
        if ok:
            self.assertEqual(result.returncode, 0, result.stderr)
        else:
            self.assertNotEqual(result.returncode, 0, result.stdout)
        return result

    def state(self):
        path = self.repo / ".git/debra-work/state.json"
        return json.loads(path.read_text()) if path.exists() else {"claims": {}}

    def open_dispatch(self):
        self.run_tool("open", "--coordinator", "test-coordinator", "--reviewer",
                      "test-reviewer", "--model", "test/model#fixture",
                      "--evidence", "docs/testing/pilot-fixture.md")

    def start(self, chain="hardware-value", owner="worker-one", cwd=None, ok=True):
        return self.run_tool("start", "--chain", chain, "--owner", owner,
                             "--model", "test/model#fixture", cwd=cwd, ok=ok)

    def claim(self):
        return next(iter(self.state()["claims"].values()))

    def fill_output(self, claim):
        work = Path(claim["workspace"])
        for name in (claim["output"], claim["handoff"]):
            path = work / name
            path.parent.mkdir(parents=True, exist_ok=True)
            path.write_text("# Synthetic research\n\nNo hardware/source claim tested.\n")
        return work

    def test_catalog_and_read_only_list(self):
        result = self.run_tool("check")
        self.assertIn("19 chains cover 65 packets", result.stdout)
        self.run_tool("list")
        self.assertFalse((self.repo / ".git/debra-work").exists())

    def test_dispatch_closed_and_input_changes_fail_closed(self):
        self.start(ok=False)
        self.assertEqual(self.state()["claims"], {})
        (self.repo / "docs/work/cards/R01.md").write_text("uncommitted change")
        result = self.run_tool(
            "open", "--coordinator", "x", "--reviewer", "y", "--model", "z",
            "--evidence", "docs/testing/pilot-fixture.md", ok=False,
        )
        self.assertIn("differ from committed base", result.stderr)

    def test_claim_creates_clean_unique_workspace_and_brief(self):
        self.open_dispatch()
        self.start()
        claim = self.claim()
        work = Path(claim["workspace"])
        self.assertEqual(self.git("status", "--porcelain", cwd=work), "")
        self.assertEqual(self.git("branch", "--show-current", cwd=work), claim["branch"])
        self.assertEqual(work.parent.stat().st_mode & 0o777, 0o700)
        text = (work / ".local/assignment.md").read_text()
        for expected in (claim["id"], claim["base"], claim["handoff"], "Acceptance"):
            self.assertIn(expected, text)
        self.start(chain="any", ok=False)  # same owner cannot silently take another
        self.start(chain="control-ui", owner="other", ok=False)

    def test_concurrent_same_chain_only_one_winner(self):
        self.open_dispatch()

        def attempt(owner):
            return subprocess.run(
                [sys.executable, "-B", "tools/taskchain.py", "start",
                 "--chain", "hardware-value", "--owner", owner,
                 "--model", "test/model#fixture"],
                cwd=self.repo, env=ENV, capture_output=True, text=True,
            ).returncode

        with ThreadPoolExecutor(max_workers=2) as pool:
            codes = list(pool.map(attempt, ["alpha", "beta"]))
        self.assertEqual(sorted(codes), [0, 1])
        self.assertEqual(len(self.state()["claims"]), 1)

    def test_shared_registry_and_any_selection_from_linked_worktree(self):
        self.open_dispatch()
        self.start()
        first = self.claim()
        result = self.run_tool("list", cwd=Path(first["workspace"]))
        self.assertIn(first["id"], result.stdout)
        self.start(chain="any", owner="worker-two", cwd=Path(first["workspace"]))
        claims = list(self.state()["claims"].values())
        self.assertEqual(len(claims), 2)
        # "any" must pick a different eligible chain, not necessarily a fixed one.
        self.assertNotEqual(claims[1]["chain"], first["chain"])
        self.assertNotEqual(claims[0]["workspace"], claims[1]["workspace"])

    def test_block_resume_and_no_automatic_expiry(self):
        self.open_dispatch()
        self.start()
        claim = self.claim()
        self.run_tool("block", claim["id"], "--owner", claim["owner"],
                      "--reason", "Missing primary source.")
        self.start(owner="other", ok=False)
        self.run_tool("resume", claim["id"], "--owner", "wrong", ok=False)
        self.run_tool("pause")
        self.start(chain="any", owner="other", ok=False)
        self.run_tool("resume", claim["id"], "--owner", claim["owner"])
        self.assertEqual(self.claim()["status"], "active")

    def test_submission_scope_handoff_and_frozen_candidate(self):
        self.open_dispatch()
        self.start()
        claim = self.claim()
        self.run_tool("submit", claim["id"], "--owner", claim["owner"], ok=False)
        work = self.fill_output(claim)
        (work / "README-unassigned.md").write_text("out of scope")
        self.run_tool("submit", claim["id"], "--owner", claim["owner"], ok=False)
        # Preserve the intentionally out-of-scope test artifact, do not delete it.
        private = work / ".local/README-unassigned.md"
        (work / "README-unassigned.md").rename(private)
        self.run_tool("submit", claim["id"], "--owner", claim["owner"])
        frozen = self.claim()["candidate_sha256"]
        self.assertEqual(len(frozen), 64)
        (work / claim["output"]).write_text("changed after submission")
        result = self.run_tool(
            "close", claim["id"], "--outcome", "integrated", "--evidence",
            "fixture review", "--integration", "HEAD", ok=False,
        )
        self.assertIn("Candidate changed", result.stderr)

    def test_coordinator_release_keeps_history_and_workspace(self):
        self.open_dispatch()
        self.start()
        claim = self.claim()
        self.run_tool("close", claim["id"], "--outcome", "released",
                      "--evidence", "Fixture owner stopped; no live process.")
        self.assertTrue(Path(claim["workspace"]).exists())
        self.start(owner="new-worker")
        self.assertEqual(len(self.state()["claims"]), 2)
        self.assertEqual(self.state()["claims"][claim["id"]]["status"], "released")
        self.run_tool("resume", claim["id"], "--owner", claim["owner"], ok=False)

    def test_workspace_creation_failure_reserves_claim(self):
        self.open_dispatch()
        self.git("branch", "work")  # refs/heads/work prevents work/<id> creation
        self.start(ok=False)
        self.assertEqual(self.claim()["status"], "workspace-failed")
        self.start(owner="other", ok=False)

    def test_integration_requires_actual_reviewed_files_in_commit(self):
        self.open_dispatch()
        self.start()
        claim = self.claim()
        work = self.fill_output(claim)
        self.run_tool("submit", claim["id"], "--owner", claim["owner"])
        self.run_tool("close", claim["id"], "--outcome", "integrated", "--evidence",
                      "synthetic review", "--integration", "HEAD", ok=False)
        for name in (claim["output"], claim["handoff"]):
            target = self.repo / name
            target.parent.mkdir(parents=True, exist_ok=True)
            shutil.copyfile(work / name, target)
        self.git("add", "--", claim["output"], claim["handoff"])
        self.git("commit", "-m", "synthetic coordinator integration")
        self.run_tool("close", claim["id"], "--outcome", "integrated", "--evidence",
                      "synthetic review and independently rerun fixture checks",
                      "--integration", "HEAD")
        self.assertEqual(self.claim()["status"], "integrated")
        self.start(owner="new", ok=False)  # base moved; no implicit advancement

    def test_wrong_model_and_changed_base_are_rejected(self):
        self.open_dispatch()
        self.run_tool("start", "--owner", "x", "--model", "different", ok=False)
        self.git("commit", "--allow-empty", "-m", "base moved")
        self.start(ok=False)

    def test_inherited_git_environment_cannot_mutate_sentinel(self):
        sentinel = Path(tempfile.mkdtemp(prefix="sentinel-", dir=FIXTURES))
        self.git("init", "--template=", cwd=sentinel)
        self.git("config", "user.name", "Sentinel", cwd=sentinel)
        self.git("config", "user.email", "sentinel@example.invalid", cwd=sentinel)
        (sentinel / "keep.txt").write_text("Unrelated disposable repository.\n")
        self.git("add", "--", "keep.txt", cwd=sentinel)
        self.git("commit", "-m", "sentinel baseline", cwd=sentinel)
        before = {
            name: (sentinel / name).read_bytes()
            for name in (".git/config", ".git/index", ".git/HEAD", "keep.txt")
        }
        head = self.git("rev-parse", "HEAD", cwd=sentinel)
        inherited_config = sentinel / ".local/inherited.gitconfig"
        inherited_config.parent.mkdir(mode=0o700)
        inherited_config.write_text("[user]\n\tname = Inherited config must not apply\n")
        poisoned = dict(
            os.environ,
            GIT_DIR=str(sentinel / ".git"),
            GIT_COMMON_DIR=str(sentinel / ".git"),
            GIT_WORK_TREE=str(sentinel),
            GIT_INDEX_FILE=str(sentinel / ".git/index"),
            GIT_CONFIG=str(sentinel / ".git/config"),
            GIT_CONFIG_GLOBAL=str(inherited_config),
            GIT_CONFIG_SYSTEM=str(inherited_config),
            GIT_CONFIG_COUNT="1",
            GIT_CONFIG_KEY_0="user.name",
            GIT_CONFIG_VALUE_0="Inherited command override must not apply",
        )
        script = """
import importlib.util
import os
import sys
spec = importlib.util.spec_from_file_location("isolated_tests", sys.argv[1])
module = importlib.util.module_from_spec(spec)
spec.loader.exec_module(module)
case = module.DispatcherTests("test_claim_creates_clean_unique_workspace_and_brief")
case.setUp()
case.test_claim_creates_clean_unique_workspace_and_brief()
assert all(name not in module.ENV for name in (
    "GIT_DIR", "GIT_COMMON_DIR", "GIT_WORK_TREE", "GIT_INDEX_FILE", "GIT_CONFIG"
))
assert module.ENV["GIT_CONFIG_NOSYSTEM"] == "1"
assert module.ENV["GIT_CONFIG_GLOBAL"] == os.devnull
assert module.ENV["GIT_CONFIG_SYSTEM"] == os.devnull
"""
        result = subprocess.run(
            [sys.executable, "-B", "-c", script, str(Path(__file__).resolve())],
            cwd=self.repo, env=poisoned, capture_output=True, text=True,
        )
        for name, content in before.items():
            self.assertEqual((sentinel / name).read_bytes(), content, name)
        self.assertEqual(self.git("rev-parse", "HEAD", cwd=sentinel), head)
        self.assertEqual(self.git("status", "--porcelain", cwd=sentinel), "?? .local/")
        self.assertEqual(result.returncode, 0, result.stderr)

    def test_start_rechecks_approved_baseline_after_waiting_for_lock(self):
        self.open_dispatch()
        # Pause at the lock boundary using pipes, not sleeps or a timing race.
        # The old main() parsed catalog/roadmap before reaching this boundary.
        script = """
from contextlib import contextmanager
import importlib.util
import sys
spec = importlib.util.spec_from_file_location("dispatcher", "tools/taskchain.py")
module = importlib.util.module_from_spec(spec)
spec.loader.exec_module(module)
original_locked = module.locked
@contextmanager
def delayed_lock(directory):
    print("waiting-before-lock", flush=True)
    assert sys.stdin.readline() == "continue\\n"
    with original_locked(directory) as state:
        yield state
module.locked = delayed_lock
sys.argv = ["taskchain.py", "start", "--chain", "hardware-value",
            "--owner", "delayed-worker", "--model", "test/model#fixture"]
module.main()
"""
        process = subprocess.Popen(
            [sys.executable, "-B", "-c", script], cwd=self.repo, env=ENV,
            stdin=subprocess.PIPE, stdout=subprocess.PIPE, stderr=subprocess.PIPE,
            text=True,
        )
        try:
            self.assertEqual(process.stdout.readline(), "waiting-before-lock\n")
            roadmap = self.repo / "docs/roadmap.md"
            text = roadmap.read_text()
            self.assertIn("| R01 / ready | F00 |", text)
            # Complete the starter rather than depending on a particular real
            # packet staying unfinished as the project's roadmap advances.
            roadmap.write_text(text.replace(
                "| R01 / ready | F00 |", "| R01 / done | F00 |", 1,
            ))
            self.git("add", "--", "docs/roadmap.md")
            self.git("commit", "-m", "coordinator completes R01 in replacement baseline")
            self.open_dispatch()
        finally:
            stdout, stderr = process.communicate("continue\n", timeout=30)
        self.assertNotEqual(process.returncode, 0, stdout)
        self.assertIn("No eligible unclaimed starter", stderr)
        self.assertEqual(self.state()["claims"], {})

    def test_staged_edits_and_wrong_branch_are_rejected(self):
        self.open_dispatch()
        self.start()
        claim = self.claim()
        work = self.fill_output(claim)
        self.git("add", "--", claim["output"], cwd=work)
        result = self.run_tool("submit", claim["id"], "--owner", claim["owner"], ok=False)
        self.assertIn("staging is not permitted", result.stderr)
        # Do not discard staged work: a branch change preserves those edits.
        self.git("switch", "-c", "fixture-wrong-branch", cwd=work)
        result = self.run_tool("resume", claim["id"], "--owner", claim["owner"], ok=False)
        self.assertIn("Branch changed", result.stderr)

    def test_symlink_output_and_modified_tracked_file_are_rejected(self):
        self.open_dispatch()
        self.start()
        claim = self.claim()
        work = self.fill_output(claim)
        output = work / claim["output"]
        output.rename(work / ".local/preserved-report.md")
        output.symlink_to(work / ".local/preserved-report.md")
        result = self.run_tool("submit", claim["id"], "--owner", claim["owner"], ok=False)
        self.assertIn("Unsafe/missing output", result.stderr)
        (work / "AGENTS.md").write_text("unassigned tracked change")
        result = self.run_tool("submit", claim["id"], "--owner", claim["owner"], ok=False)
        self.assertIn("Unexpected/empty changed paths", result.stderr)


if __name__ == "__main__":
    print(f"Retained offline fixtures: {FIXTURES}", flush=True)
    unittest.main()

"""Offline Git fixtures only. Retained under /tmp/opencode, never auto-deleted."""

from concurrent.futures import ThreadPoolExecutor
import json
import os
from pathlib import Path
import shutil
import subprocess
import sys
import tempfile
import unittest


SOURCE = Path(__file__).resolve().parent.parent
FIXTURES = Path(tempfile.mkdtemp(prefix="debra-taskchain-tests-", dir="/tmp/opencode"))
ENV = dict(os.environ, GIT_CONFIG_COUNT="1", GIT_CONFIG_KEY_0="core.hooksPath",
           GIT_CONFIG_VALUE_0="/dev/null", GIT_TERMINAL_PROMPT="0")


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
        self.assertIn("19 chains cover 63 packets", result.stdout)
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
        self.assertEqual(claims[1]["chain"], "complete-alternatives")
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

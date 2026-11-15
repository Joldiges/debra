"""Offline tests for tools/coord.py.

They use a throwaway Git fixture and a throwaway records directory, stub the
OpenCode API, and never start a model call, contact a device, or touch the real
.local/coord state. Fixtures are retained under /tmp/opencode.
"""

import io
import re
import json
import os
import subprocess
import sys
import tempfile
import unittest
from contextlib import redirect_stderr, redirect_stdout
from pathlib import Path
from unittest import mock

SOURCE = Path(__file__).resolve().parent.parent
if str(SOURCE) not in sys.path:
    sys.path.insert(0, str(SOURCE))

import tools.coord as coord  # noqa: E402  (path set above)

FIXTURES = Path(tempfile.mkdtemp(prefix="debra-coord-tests-", dir="/tmp/opencode"))
# cwd alone cannot isolate Git: inherited GIT_DIR/GIT_WORK_TREE/GIT_INDEX_FILE
# can redirect commands into another checkout.
ENV = {
    **{key: value for key, value in os.environ.items() if not key.startswith("GIT_")},
    "GIT_CONFIG_NOSYSTEM": "1",
    "GIT_CONFIG_SYSTEM": os.devnull,
    "GIT_CONFIG_GLOBAL": os.devnull,
    "GIT_TERMINAL_PROMPT": "0",
}

SESSION = {
    "id": "ses_fixture",
    "agent": "debra-research",
    "title": "fixture",
    "model": {"providerID": "openrouter", "id": "deepseek/deepseek-v4.1-flash-1017",
              "variant": "high"},
    "cost": 0.0125,
    "tokens": {"input": 10, "output": 20, "reasoning": 5, "cache": {"read": 0, "write": 0}},
    "directory": "/fixture",
}


class CoordTests(unittest.TestCase):
    def setUp(self):
        self.root = Path(tempfile.mkdtemp(prefix="case-", dir=FIXTURES))
        self.repo = self.root / "repo"
        self.records = self.root / "records"
        self.repo.mkdir()
        self.git("init", "--template=")
        self.git("config", "user.name", "Fixture")
        self.git("config", "user.email", "fixture@example.invalid")
        (self.repo / "docs").mkdir()
        (self.repo / "docs" / "page.md").write_text("before\n")
        self.git("add", "--", ".")
        self.git("commit", "-m", "fixture baseline")
        self.base = self.git("rev-parse", "HEAD")
        self.brief = self.root / "brief.md"
        self.brief.write_text("Read docs/page.md and report.\n")
        self.report = self.root / "report.md"
        self.report.write_text("## Report\n\nNothing surprising.\n")

    def git(self, *args):
        result = subprocess.run(["git", *args], cwd=self.repo, env=ENV,
                                capture_output=True, text=True)
        self.assertEqual(result.returncode, 0, result.stderr)
        return result.stdout.strip()

    def run_tool(self, *args, ok=True):
        out, err = io.StringIO(), io.StringIO()
        with redirect_stdout(out), redirect_stderr(err):
            code = coord.main(["--records", str(self.records), "--repo", str(self.repo),
                               *args])
        if ok:
            self.assertEqual(code, 0, err.getvalue())
        else:
            self.assertNotEqual(code, 0, out.getvalue())
        return out.getvalue() + err.getvalue()

    def launch(self, task="T01", role="research", *extra, ok=True):
        return self.run_tool("launch", "--task", task, "--role", role,
                             "--model", "openrouter/deepseek/deepseek-v4.1-flash-1017#high",
                             "--prompt-file", str(self.brief), *extra, ok=ok)

    def captured(self, task="T01"):
        self.launch(task)
        self.run_tool("capture", "--task", task, "--report", str(self.report))
        return self.records / task

    # --- launch -----------------------------------------------------------
    def test_launch_records_base_and_brief_hash(self):
        self.launch()
        record = json.loads((self.records / "T01" / "launch.json").read_text())
        self.assertEqual(record["base_commit"], self.base)
        self.assertEqual(record["brief_sha256"], coord.sha256_bytes(self.brief.read_bytes()))
        self.assertEqual(record["status"], "launched; not captured")
        self.assertEqual(record["paths"], [])
        self.assertEqual(
            (self.records / "T01" / "brief.md").read_text(), self.brief.read_text())

    def test_launch_does_not_overwrite_without_force(self):
        self.launch()
        message = self.launch(ok=False)
        self.assertIn("already recorded", message)
        self.launch("T01", "research", "--force")

    def test_launch_refuses_bad_input(self):
        self.assertIn("invalid task id", self.launch("../escape", ok=False))
        self.assertIn("at least one --path", self.launch("T02", "edit", ok=False))
        self.assertIn("read-only", self.launch("T03", "research", "--path",
                                               "docs/page.md", ok=False))
        self.assertIn("must be relative",
                      self.launch("T04", "edit", "--path", "/etc/passwd", ok=False))
        self.assertIn("climb out",
                      self.launch("T05", "edit", "--path", "../x.md", ok=False))
        self.assertIn("did not resolve", self.launch("T06", "research", "--base",
                                                     "nosuchref", ok=False))
        self.assertIn("attempt count", self.launch("T07", "research", "--budget", "99",
                                                   ok=False))

    # --- capture ----------------------------------------------------------
    def test_capture_pins_report_and_refuses_rewrite(self):
        directory = self.captured()
        metadata = json.loads((directory / "metadata.json").read_text())
        self.assertEqual(metadata["model"],
                         "openrouter/deepseek/deepseek-v4.1-flash-1017#high")
        self.assertEqual(metadata["report_sha256"],
                         coord.sha256_bytes(self.report.read_bytes()))
        self.assertEqual(metadata["status"], "captured; not reviewed")
        self.assertIsNone(metadata["cost"])
        message = self.run_tool("capture", "--task", "T01", "--report",
                                str(self.report), ok=False)
        self.assertIn("frozen report", message)

    def test_capture_without_report_or_session_is_refused(self):
        self.launch()
        self.assertIn("no report", self.run_tool("capture", "--task", "T01", ok=False))

    def test_capture_uses_session_model_and_cost(self):
        self.launch()
        with mock.patch.object(coord, "session_record", lambda sid: SESSION), \
                mock.patch.object(coord, "last_reply_text", lambda sid: "## Reply\n\nok\n"):
            self.run_tool("capture", "--task", "T01", "--session", "ses_fixture")
        metadata = json.loads((self.records / "T01" / "metadata.json").read_text())
        self.assertEqual(metadata["cost"], 0.0125)
        self.assertEqual(metadata["agent"], "debra-research")
        self.assertEqual((self.records / "T01" / "submitted.md").read_text(),
                         "## Reply\n\nok\n")

    def test_capture_records_an_unreachable_service(self):
        self.launch()
        with mock.patch.object(coord, "session_record",
                               side_effect=coord.CoordError("opencode unavailable")):
            self.run_tool("capture", "--task", "T01", "--session", "ses_fixture",
                          "--report", str(self.report))
        metadata = json.loads((self.records / "T01" / "metadata.json").read_text())
        self.assertEqual(metadata["session_error"], "opencode unavailable")
        self.assertEqual(metadata["model"],
                         "openrouter/deepseek/deepseek-v4.1-flash-1017#high")

    # --- snapshot and verdict ---------------------------------------------
    def test_snapshot_freezes_tracked_and_untracked_candidate(self):
        directory = self.captured()
        (self.repo / "docs" / "page.md").write_text("after\n")
        (self.repo / "docs" / "new.md").write_text("added\n")
        self.run_tool("snapshot", "--task", "T01", "--path", "docs")
        manifest = json.loads((directory / "review" / "manifest.json").read_text())
        patch = (directory / "review" / "candidate.patch").read_text()
        self.assertIn("after", patch)
        self.assertIn("added", patch)
        self.assertEqual(manifest["patch_sha256"],
                         coord.sha256_bytes(patch.encode()))
        self.assertIn("docs/new.md", manifest["untracked"])
        self.assertIn({"path": "docs", "kind": "directory"}, manifest["files"])
        message = self.run_tool("snapshot", "--task", "T01", "--path", "docs", ok=False)
        self.assertIn("already has a frozen candidate", message)

    def test_snapshot_refuses_an_empty_candidate(self):
        self.captured()
        self.assertIn("snapshot is empty",
                      self.run_tool("snapshot", "--task", "T01", "--path", "docs/page.md",
                                    ok=False))

    def test_verdict_requires_candidate_and_names_its_hash(self):
        directory = self.captured()
        findings = self.root / "findings.md"
        findings.write_text("One finding.\n")
        message = self.run_tool("verdict", "--task", "T01", "--reviewer", "r",
                                "--verdict", "approve", "--report", str(findings),
                                ok=False)
        self.assertIn("review manifest is missing", message)
        (self.repo / "docs" / "page.md").write_text("after\n")
        self.run_tool("snapshot", "--task", "T01", "--path", "docs/page.md")
        manifest = json.loads((directory / "review" / "manifest.json").read_text())
        self.run_tool("verdict", "--task", "T01", "--reviewer", "capable reviewer",
                      "--model", "openrouter/openai/gpt-6.1-sol#high",
                      "--verdict", "approve", "--report", str(findings))
        verdict = (directory / "review" / "verdict.md").read_text()
        self.assertIn(f"- candidate sha256: {manifest['patch_sha256']}", verdict)
        self.assertIn("- verdict: approve", verdict)
        self.assertIn("One finding.", verdict)
        message = self.run_tool("verdict", "--task", "T01", "--reviewer", "r",
                                "--verdict", "reject", "--report", str(findings),
                                ok=False)
        self.assertIn("already has a verdict", message)

    # --- profile ----------------------------------------------------------
    def test_edit_profile_allows_only_named_paths(self):
        text = self.run_tool("profile", "--task", "T01", "--role", "edit",
                             "--path", "docs/page.md", "--path", "tests/test_x.py")
        out = self.repo / ".opencode" / "agents" / "local-t01.md"
        self.assertTrue(out.exists(), text)
        body = out.read_text()
        self.assertIn('  - action: "*"\n    resource: "*"\n    effect: deny', body)
        self.assertIn('  - action: "edit"\n    resource: "docs/page.md"\n    effect: allow',
                      body)
        self.assertIn('  - action: "edit"\n    resource: "tests/test_x.py"\n    effect: allow',
                      body)
        self.assertIn("mode: subagent", body)
        self.assertEqual(body.count('action: "edit"'), 2)
        self.assertIn("local-t01", text)

    def test_profile_refuses_unsafe_or_ambiguous_input(self):
        self.assertIn("at least one --path",
                      self.run_tool("profile", "--task", "T02", "--role", "edit", ok=False))
        self.assertIn("read-only",
                      self.run_tool("profile", "--task", "T02", "--path", "docs/page.md",
                                    ok=False))
        self.assertIn("must be relative",
                      self.run_tool("profile", "--task", "T02", "--role", "edit",
                                    "--path", "/etc/passwd", ok=False))
        self.run_tool("profile", "--task", "T03", "--role", "edit",
                      "--path", "docs/page.md")
        message = self.run_tool("profile", "--task", "T03", "--role", "edit",
                                "--path", "docs/page.md", ok=False)
        self.assertIn("already exists", message)

    # --- status and check -------------------------------------------------
    def test_status_shows_stages_and_spend(self):
        self.launch()
        with mock.patch.object(coord, "session_record", lambda sid: SESSION), \
                mock.patch.object(coord, "last_reply_text", lambda sid: "ok"):
            self.run_tool("capture", "--task", "T01", "--session", "ses_fixture")
        (self.repo / "docs" / "page.md").write_text("after\n")
        self.run_tool("snapshot", "--task", "T01", "--path", "docs/page.md")
        findings = self.root / "findings.md"
        findings.write_text("fine\n")
        self.run_tool("verdict", "--task", "T01", "--reviewer", "capable reviewer",
                      "--verdict", "approve", "--report", str(findings))
        text = self.run_tool("status")
        self.assertIn("T01", text)
        self.assertIn("reviewed: approve", text)
        self.assertIn("$0.0125", text)
        self.assertIn("not acceptance", text)

    def test_check_passes_then_catches_a_tampered_report(self):
        directory = self.captured()
        (self.repo / "docs" / "page.md").write_text("after\n")
        self.run_tool("snapshot", "--task", "T01", "--path", "docs/page.md")
        findings = self.root / "findings.md"
        findings.write_text("fine\n")
        self.run_tool("verdict", "--task", "T01", "--reviewer", "capable reviewer",
                      "--verdict", "approve", "--report", str(findings))
        self.assertIn("PASS", self.run_tool("check"))
        (directory / "submitted.md").write_text("rewritten after capture\n")
        message = self.run_tool("check", ok=False)
        self.assertIn("changed after capture", message)
        self.assertIn("FAIL", message)

    def test_check_catches_a_verdict_for_the_wrong_candidate(self):
        directory = self.captured()
        findings = self.root / "findings.md"
        findings.write_text("fine\n")
        (self.repo / "docs" / "page.md").write_text("after\n")
        self.run_tool("snapshot", "--task", "T01", "--path", "docs/page.md")
        self.run_tool("verdict", "--task", "T01", "--reviewer", "r",
                      "--verdict", "approve", "--report", str(findings))
        manifest_path = directory / "review" / "manifest.json"
        manifest = json.loads(manifest_path.read_text())
        manifest["patch_sha256"] = "0" * 64
        manifest_path.write_text(json.dumps(manifest))
        self.assertIn("does not match its manifest", self.run_tool("check", ok=False))

    def test_status_and_check_are_safe_on_empty_records(self):
        self.assertIn("no delegated tasks", self.run_tool("status"))
        self.assertIn("PASS", self.run_tool("check"))

    def test_records_are_owner_only(self):
        directory = self.captured()
        for path in (directory / "launch.json", directory / "brief.md",
                     directory / "submitted.md", directory / "metadata.json"):
            self.assertEqual(path.stat().st_mode & 0o777, 0o600, path)
        self.assertEqual(directory.stat().st_mode & 0o777, 0o700)

    # --- profile rules ---------------------------------------------------
    @staticmethod
    def profile_rules(path):
        """The permission triples of one agent file, in file order."""
        rules, pending = [], {}
        for line in path.read_text().splitlines():
            match = re.match(r"\s+(?:- )?(action|resource|effect): (.*)$", line)
            if not match:
                continue
            key, value = match[1], match[2]

            def unquote(text):
                try:
                    return json.loads(text)
                except ValueError:
                    return text

            if key == "action":
                pending = {"action": unquote(value)}
            else:
                pending[key] = unquote(value)
                if key == "effect":
                    rules.append((pending["action"], pending["resource"], pending["effect"]))
        return rules

    def test_committed_profiles_match_the_generator(self):
        for role in ("research", "review"):
            committed = SOURCE / ".opencode" / "agents" / f"debra-{role}.md"
            self.assertTrue(committed.exists(), committed)
            generated = self.root / f"{role}.md"
            self.run_tool("profile", "--task", "DRIFT", "--role", role,
                          "--out", str(generated))
            self.assertEqual(self.profile_rules(committed), self.profile_rules(generated),
                             f"{committed.name} has drifted from tools/coord.py")

    def test_secret_denies_follow_the_broad_read_allow(self):
        rules = coord._permissions("research", [])
        allow = rules.index(("read", "*", "allow"))
        self.assertNotIn(("grep", "*", "allow"), rules,
                         "grep authorises a pattern, not a path, so it cannot respect read denies")
        self.assertNotIn(("glob", "*", "allow"), rules)
        secrets = [("read", "~/.ssh/*", "deny"), ("read", "~/.gnupg/*", "deny"),
                   ("read", "~/.aws/*", "deny"), ("read", "*/auth.json", "deny")]
        for rule in secrets:
            self.assertIn(rule, rules)
            self.assertGreater(rules.index(rule), allow,
                               f"{rule} must come after the read allow to keep it denied")
        self.assertEqual(rules[0], ("*", "*", "deny"))
        self.assertEqual(rules[1], ("external_directory", "*", "deny"))


if __name__ == "__main__":
    unittest.main()

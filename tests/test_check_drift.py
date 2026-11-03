import json
import os
import pathlib
import shutil
import subprocess
import sys
import tempfile
import unittest

REPO = pathlib.Path(__file__).resolve().parent.parent
CLI = REPO / "bin/kolin-skills"
PIN = json.loads((REPO / "upstream/vendor.json").read_text())["cursor-plugins"]["rev"]
REVIEWER = (REPO / "agents/senior-reviewer.md").read_text()
STALE = "df58112aaaaaaaaaaaaaaaaaaaaaaaaaaaaaaa"


class CheckDriftTests(unittest.TestCase):
    def setUp(self):
        self.root = pathlib.Path(tempfile.mkdtemp())
        self.addCleanup(shutil.rmtree, self.root)

    def write(self, relative, text):
        path = self.root / relative
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(text)
        return path

    def run_cli(self, *args):
        env = {key: value for key, value in os.environ.items() if key != "CI"}
        return subprocess.run(
            [sys.executable, str(CLI), *args],
            cwd=self.root, env=env, text=True, capture_output=True, timeout=20,
        )

    def test_stale_pstack_source_fails_and_the_pin_passes(self):
        self.write(".agents/PSTACK.SOURCE",
                   "source: https://github.com/cursor/plugins/tree/main/pstack\n"
                   f"commit: {STALE}\n")
        stale = self.run_cli("check-drift", str(self.root))
        self.assertEqual(stale.returncode, 1, stale.stderr)
        self.assertIn("PSTACK.SOURCE", stale.stderr)
        self.assertIn(STALE[:12], stale.stderr)
        self.assertIn(PIN[:12], stale.stderr)
        self.write(".agents/PSTACK.SOURCE",
                   "source: https://github.com/cursor/plugins/tree/main/pstack\n"
                   f"commit: {PIN}\n")
        matched = self.run_cli("check-drift", str(self.root))
        self.assertEqual(matched.returncode, 0, matched.stderr)
        self.assertIn("Passed:", matched.stdout)

    def test_stale_vendor_json_fails_and_the_pin_passes(self):
        self.write("upstream/vendor.json", json.dumps({
            "cursor-plugins": {"url": "https://github.com/cursor/plugins.git", "rev": STALE},
        }) + "\n")
        stale = self.run_cli("check-drift", str(self.root))
        self.assertEqual(stale.returncode, 1, stale.stderr)
        self.assertIn("cursor-plugins", stale.stderr)
        self.assertIn(STALE[:12], stale.stderr)
        self.write("upstream/vendor.json", json.dumps({
            "cursor-plugins": {"url": "https://github.com/cursor/plugins.git", "rev": PIN},
        }) + "\n")
        matched = self.run_cli("check-drift", str(self.root))
        self.assertEqual(matched.returncode, 0, matched.stderr)

    def test_drifted_senior_reviewer_fails_and_a_copy_of_the_repo_file_passes(self):
        self.write(".claude/agents/senior-reviewer.md", REVIEWER + "\nextra drifted line\n")
        stale = self.run_cli("check-drift", str(self.root))
        self.assertEqual(stale.returncode, 1, stale.stderr)
        self.assertIn("senior-reviewer.md", stale.stderr)
        self.write(".claude/agents/senior-reviewer.md", REVIEWER)
        matched = self.run_cli("check-drift", str(self.root))
        self.assertEqual(matched.returncode, 0, matched.stderr)

    def test_this_repo_and_an_empty_tree_pass(self):
        here = self.run_cli("check-drift", str(REPO))
        self.assertEqual(here.returncode, 0, here.stderr)
        self.assertIn("Passed:", here.stdout)
        empty = self.run_cli("check-drift", str(self.root))
        self.assertEqual(empty.returncode, 0, empty.stderr)

    def test_check_with_a_target_fails_on_drift_without_rerunning_tests(self):
        self.write(".agents/PSTACK.SOURCE", f"commit: {STALE}\n")
        result = self.run_cli("check", str(self.root))
        self.assertEqual(result.returncode, 1, result.stderr)
        self.assertIn("PSTACK.SOURCE", result.stderr)
        self.assertNotIn("tests failed", result.stderr)
        self.assertNotIn("Ran:", result.stderr)

    def test_reviewer_required_on_every_pr_fails_and_ask_only_language_passes(self):
        self.write("AGENTS.md",
                   "A separate reviewer is required on every PR.\n")
        stale = self.run_cli("check-drift", str(self.root))
        self.assertEqual(stale.returncode, 1, stale.stderr)
        self.assertIn("AGENTS.md", stale.stderr)
        self.assertIn("every PR", stale.stderr)
        self.write("AGENTS.md",
                   "Spawn senior-reviewer or interrogate only on high-risk work "
                   "(auth, money, data deletion) or when Kolin or the CEO asks.\n")
        matched = self.run_cli("check-drift", str(self.root))
        self.assertEqual(matched.returncode, 0, matched.stderr)
        self.assertIn("Passed:", matched.stdout)

    def test_old_150_line_pre_pr_review_fails_and_same_session_proof_passes(self):
        self.write("CLAUDE.md",
                   "A fresh review reads the diff before the PR opens when it "
                   "changes over 150 lines or touches schema, auth, access, money "
                   "or a migration: interrogate in a pstack run, else senior-reviewer.\n")
        stale = self.run_cli("check-drift", str(self.root))
        self.assertEqual(stale.returncode, 1, stale.stderr)
        self.assertIn("CLAUDE.md", stale.stderr)
        self.write("CLAUDE.md",
                   "Before the PR opens, prove the change in this same session. "
                   "Do not spawn a separate AI code reviewer.\n")
        matched = self.run_cli("check-drift", str(self.root))
        self.assertEqual(matched.returncode, 0, matched.stderr)

    def test_reviewer_required_before_every_staging_merge_fails_on_claude_policy_copy(self):
        self.write(".claude/CLAUDE.md",
                   "senior-reviewer is required before every staging merge.\n")
        stale = self.run_cli("check-drift", str(self.root))
        self.assertEqual(stale.returncode, 1, stale.stderr)
        self.assertIn(".claude/CLAUDE.md", stale.stderr)
        self.assertIn("staging merge", stale.stderr)
        self.write(".claude/CLAUDE.md",
                   "External AI code review is not a quality gate; proof of behavior is. "
                   "Reviewers are high-risk or ask-only.\n")
        matched = self.run_cli("check-drift", str(self.root))
        self.assertEqual(matched.returncode, 0, matched.stderr)

    def test_policy_agents_copy_with_every_pr_reviewer_gate_fails_then_passes(self):
        self.write("policy/AGENTS.md",
                   "Run interrogate on every pull request before it opens.\n")
        stale = self.run_cli("check-drift", str(self.root))
        self.assertEqual(stale.returncode, 1, stale.stderr)
        self.assertIn("policy/AGENTS.md", stale.stderr)
        self.write("policy/AGENTS.md",
                   "interrogate is on demand, not the pre-PR gate.\n")
        matched = self.run_cli("check-drift", str(self.root))
        self.assertEqual(matched.returncode, 0, matched.stderr)

    def assert_policy_fails_then_passes(self, relative, mandate, fixed):
        self.write(relative, mandate)
        stale = self.run_cli("check-drift", str(self.root))
        self.assertEqual(stale.returncode, 1, f"{mandate!r} passed: {stale.stdout}")
        self.assertIn(relative, stale.stderr)
        self.write(relative, fixed)
        matched = self.run_cli("check-drift", str(self.root))
        self.assertEqual(matched.returncode, 0, matched.stderr)

    def test_every_agent_pr_reviewer_pass_fails_then_passes(self):
        self.assert_policy_fails_then_passes(
            "AGENTS.md",
            "- Final diff reviewed for unrelated edits. Every agent PR gets a cheap `plm-reviewer` "
            "pass in a fresh context before human review; add pstack's `interrogate` for mutation, "
            "access, schema, or promotion diffs. The implementer does not grade itself.\n",
            "- Final diff reviewed for unrelated edits. `plm-reviewer` reads a diff only on high-risk "
            "work (mutation, access, schema, promotion) or when Kolin or the CEO asks.\n",
        )

    def test_reviewer_mandate_split_across_sentences_fails_then_passes(self):
        sentences = {
            "each PR in a sentence after the reviewer is named":
                "`senior-reviewer` is the diff reviewer. It reads each PR before the PR merges into `staging`.",
            "required Ran line for a reviewer":
                "The PR body must carry `Ran: senior-reviewer` and `Ran: interrogate`.",
            "no Not run line excuses the review":
                "`senior-reviewer` and `interrogate` review the diff. No `Not run` line excuses either review.",
        }
        for name, mandate in sentences.items():
            with self.subTest(name):
                self.assert_policy_fails_then_passes(
                    "AGENTS.md", mandate,
                    "`senior-reviewer` and `interrogate` run only on high-risk work (auth, money, data "
                    "deletion) or when Kolin asks. Same-session proof is the gate.\n",
                )

    def test_ask_only_reviewer_wording_across_sentences_passes(self):
        passing = (
            "`senior-reviewer` runs only on high-risk work. Each PR proves its behavior in the same session.\n",
            "`plm-reviewer` owns the cheap-review procedure. pstack's `interrogate` is the adversarial "
            "pass for high-risk diffs. Thermo review is ask-only.\n",
            "Each PR body lists `Ran: pnpm check` or `Not run: <check>, because <why>`.\n",
            "A reviewer reads the diff on demand. Every PR still carries same-session proof.\n",
        )
        for text in passing:
            with self.subTest(text=text):
                self.write("AGENTS.md", text)
                result = self.run_cli("check-drift", str(self.root))
                self.assertEqual(result.returncode, 0, result.stderr)


if __name__ == "__main__":
    unittest.main()

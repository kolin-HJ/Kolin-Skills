import json
import pathlib
import subprocess
import sys
import tempfile
import unittest

HOOK = pathlib.Path(__file__).resolve().parent.parent / "hooks/pr-proof.py"
GOOD = "gh pr create --title x --body '## Verification\n- Ran: `pnpm check` ok\n'"


def git(cwd, *args):
    subprocess.run(["git", *args], cwd=cwd, check=True, capture_output=True)


class PrProofTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        root = pathlib.Path(self.temp.name)
        self.repo = root / "app"
        git(root, "init", "-q", "--bare", "-b", "main", "origin.git")
        git(root, "clone", "-q", "origin.git", "app")
        for key, value in (("user.name", "Dev"), ("user.email", "dev@example.com")):
            git(self.repo, "config", key, value)
        (self.repo / "a.txt").write_text("start\n")
        git(self.repo, "add", ".")
        git(self.repo, "commit", "-qm", "start")
        git(self.repo, "push", "-q", "origin", "main")
        git(self.repo, "checkout", "-qb", "work")
        self.transcript = root / "session.jsonl"
        self.transcript.write_text("")

    def tearDown(self):
        self.temp.cleanup()

    def change(self, name, text):
        path = self.repo / name
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(text)
        git(self.repo, "add", ".")
        git(self.repo, "commit", "-qm", "change")

    def record(self, name, tool_input):
        line = {"type": "assistant", "message": {"content": [{"type": "tool_use", "name": name, "input": tool_input}]}}
        with self.transcript.open("a") as handle:
            handle.write(json.dumps(line) + "\n")

    def run_hook(self, command):
        payload = {"cwd": str(self.repo), "transcript_path": str(self.transcript), "tool_input": {"command": command}}
        return subprocess.run([sys.executable, str(HOOK)], input=json.dumps(payload), text=True, capture_output=True, timeout=120)

    def test_other_commands_pass_even_when_they_mention_a_pr(self):
        for command in ("git status", "echo 'gh pr create'", "gh pr view 3"):
            with self.subTest(command=command):
                self.assertEqual(self.run_hook(command).returncode, 0)

    def test_a_pr_with_no_verification_lines_is_blocked(self):
        self.change("a.txt", "next\n")
        for command in ("gh pr create --fill", "gh pr create --body '## Verification\nIt works.\n'"):
            with self.subTest(command=command):
                result = self.run_hook(command)
                self.assertEqual(result.returncode, 2)
                self.assertIn("## Verification", result.stderr)

    def test_a_small_pr_with_proof_passes(self):
        self.change("a.txt", "next\n")
        self.record("Bash", {"command": "pnpm check"})
        result = self.run_hook(GOOD)
        self.assertEqual((result.returncode, result.stdout), (0, ""))

    def test_a_body_file_counts_as_the_body(self):
        self.change("a.txt", "next\n")
        (self.repo.parent / "body.md").write_text("## Verification\n- Not run: `pnpm check`, because no node here\n")
        self.assertEqual(self.run_hook("gh pr create --body-file ../body.md").returncode, 0)

    def test_a_large_diff_needs_a_review_that_really_ran(self):
        self.change("big.txt", "line\n" * 200)
        self.record("Bash", {"command": "pnpm check"})
        blocked = self.run_hook(GOOD)
        self.assertEqual(blocked.returncode, 2)
        self.assertIn("200 lines", blocked.stderr)
        self.record("Agent", {"subagent_type": "senior-reviewer", "prompt": "review"})
        self.assertEqual(self.run_hook(GOOD).returncode, 0)

    def test_a_small_risky_diff_needs_a_review_and_a_stated_reason_lets_it_through(self):
        self.change("db/migrations/1.sql", "select 1;\n")
        self.record("Bash", {"command": "pnpm check"})
        self.assertIn("migrations", self.run_hook(GOOD).stderr)
        waived = "gh pr create --body '## Verification\n- Ran: `pnpm check` ok\n- Not run: review, because the file is a no-op\n'"
        self.assertEqual(self.run_hook(waived).returncode, 0)

    def test_a_lockfile_does_not_count_toward_the_review_size(self):
        self.change("pnpm-lock.yaml", "line\n" * 500)
        self.record("Bash", {"command": "pnpm check"})
        self.assertEqual(self.run_hook(GOOD).returncode, 0)

    def test_a_skipped_test_is_blocked_unless_the_body_justifies_it(self):
        self.change("a.test.ts", "it.skip('runs', () => {});\n")
        self.record("Bash", {"command": "pnpm check"})
        blocked = self.run_hook(GOOD)
        self.assertEqual(blocked.returncode, 2)
        self.assertIn("skip", blocked.stderr)
        allowed = "gh pr create --body '## Verification\n- Ran: `pnpm check` ok\n\nAllowed skip: upstream bug 12\n'"
        self.assertEqual(self.run_hook(allowed).returncode, 0)

    def test_a_ran_line_with_no_matching_command_gets_a_note_but_is_not_blocked(self):
        self.change("a.txt", "next\n")
        self.record("Bash", {"command": "git status"})
        result = self.run_hook(GOOD)
        self.assertEqual(result.returncode, 0)
        self.assertIn("pnpm check", json.loads(result.stdout)["hookSpecificOutput"]["additionalContext"])


if __name__ == "__main__":
    unittest.main()

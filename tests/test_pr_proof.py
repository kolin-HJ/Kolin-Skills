import json
import os
import pathlib
import stat
import subprocess
import sys
import tempfile
import unittest

HOOK = pathlib.Path(__file__).resolve().parent.parent / "hooks/pr-proof.py"
PROOF = "## Verification\n- Ran: `pnpm check` ok\n"
URL = "https://github.com/acme/app/pull/7"
FAKE_GH = """#!/bin/sh
if [ "$2" = "view" ]; then
  echo "$@" >> "$GH_CALLS"
  [ -f "$PR_JSON" ] && cat "$PR_JSON" && exit 0
  echo "${GH_VIEW_ERROR:-no pull requests found}" >&2
  exit 1
fi
echo "$@" >> "$GH_CALLS"
"""


def git(cwd, *args):
    return subprocess.run(["git", *args], cwd=cwd, check=True, capture_output=True, text=True).stdout.strip()


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
        self.bin = root / "bin"
        self.bin.mkdir()
        fake = self.bin / "gh"
        fake.write_text(FAKE_GH)
        fake.chmod(fake.stat().st_mode | stat.S_IEXEC)
        self.pr_json = root / "pr.json"
        self.calls = root / "calls.txt"

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

    def open_pr(self, body, **fields):
        pr = {"url": URL, "body": body, "baseRefName": "main", "headRefName": "work", "isCrossRepository": False, "headRefOid": git(self.repo, "rev-parse", "HEAD"), "isDraft": False, "state": "OPEN", **fields}
        self.pr_json.write_text(json.dumps(pr))

    def run_hook(self, command="gh pr create --fill", response=URL, **extra_env):
        payload = {"cwd": str(self.repo), "transcript_path": str(self.transcript), "tool_input": {"command": command}, "tool_response": {"stdout": response}}
        env = {**os.environ, "PATH": f"{self.bin}:{os.environ['PATH']}", "PR_JSON": str(self.pr_json), "GH_CALLS": str(self.calls), **extra_env}
        return subprocess.run([sys.executable, str(HOOK)], input=json.dumps(payload), text=True, capture_output=True, timeout=120, env=env)

    def gh_calls(self):
        return self.calls.read_text() if self.calls.exists() else ""

    def assert_trusted(self, result):
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertNotIn("--undo", self.gh_calls())

    def assert_drafted(self, result, reason):
        self.assertEqual(result.returncode, 2)
        self.assertIn(reason, result.stderr)
        self.assertIn(f"pr ready {URL} --undo", self.gh_calls())

    def test_a_release_pr_carries_the_proof_of_its_merged_prs(self):
        self.change("a.txt", "next\n")
        self.open_pr("", headRefName="staging")
        self.assert_trusted(self.run_hook())

    def test_a_base_other_than_main_is_fetched_even_in_a_single_branch_clone(self):
        git(self.repo, "push", "-q", "origin", "main:staging")
        git(self.repo, "update-ref", "-d", "refs/remotes/origin/staging")
        self.change("a.txt", "next\n")
        self.record("Bash", {"command": "pnpm check"})
        self.open_pr(PROOF, baseRefName="staging")
        result = self.run_hook()
        self.assert_trusted(result)
        self.assertEqual(result.stdout, "")

    def test_an_audit_that_cannot_run_sends_the_pr_back_with_a_visible_exit(self):
        git(self.repo, "checkout", "-q", "--orphan", "unrelated")
        self.change("a.txt", "next\n")
        self.record("Bash", {"command": "pnpm check"})
        self.open_pr(PROOF)
        self.assert_drafted(self.run_hook(), "diff-audit could not run")
        self.calls.unlink()
        self.open_pr(PROOF + "- Not run: diff-audit, because the histories are unrelated\n- Not run: review, because this is a test\n")
        self.assert_trusted(self.run_hook())

    def test_a_missing_gh_gets_a_note_not_a_crash(self):
        empty = self.bin.parent / "empty"
        empty.mkdir()
        result = self.run_hook(PATH=str(empty))
        self.assert_trusted(result)
        self.assertIn("could not read the PR", result.stdout)

    def test_a_strange_transcript_line_is_skipped(self):
        self.change("a.txt", "next\n")
        with self.transcript.open("a") as handle:
            handle.write('["tool_use"]\n{"message": {"content": [{"type": "tool_use", "name": "Agent", "input": "x"}]}}\nnot json "tool_use"\n')
        self.record("Bash", {"command": "pnpm check"})
        self.open_pr(PROOF)
        self.assert_trusted(self.run_hook())

    def test_a_pr_it_cannot_read_gets_a_note_not_silence(self):
        result = self.run_hook(GH_VIEW_ERROR="HTTP 502")
        self.assert_trusted(result)
        self.assertIn("HTTP 502", result.stdout)

    def test_a_draft_is_not_checked_until_it_is_marked_ready(self):
        self.change("a.txt", "next\n")
        self.open_pr("", isDraft=True)
        self.assert_trusted(self.run_hook("gh pr create --draft --fill"))
        self.open_pr("")
        self.assert_drafted(self.run_hook("gh pr ready"), "## Verification")

    def test_a_pr_named_in_the_command_is_the_one_checked(self):
        self.change("a.txt", "next\n")
        self.record("Bash", {"command": "pnpm check"})
        self.open_pr(PROOF)
        self.assert_trusted(self.run_hook("gh pr ready 12 --repo other/app 2>&1"))
        self.assertIn("pr view 12 --repo other/app", self.gh_calls())

    def test_plain_ran_and_not_run_lines_count_as_proof(self):
        self.change("a.txt", "next\n")
        self.record("Bash", {"command": "pnpm check"})
        for body in ("## Verification\nRan: pnpm check passed\n", "## Verification\n- Not run: browser, because there is no UI\n"):
            with self.subTest(body=body):
                self.open_pr(body)
                self.assert_trusted(self.run_hook())

    def test_a_pr_command_that_only_appears_as_text_does_nothing(self):
        self.open_pr("")
        for command in ('grep -n "gh pr create" x', "git commit -m 'after gh pr ready'", "echo gh pr ready", "gh pr edit --add-label qa", "git commit -F - <<'EOF'\ngh pr create\nEOF"):
            with self.subTest(command=command):
                self.assert_trusted(self.run_hook(command))

    def test_a_real_pr_command_is_seen_in_each_common_shape(self):
        self.change("a.txt", "next\n")
        self.open_pr("")
        for command in ("cd sub && gh pr create --fill", "URL=$(gh pr create --fill)", "GH_DEBUG=1 gh pr create --fill", "gh pr create --body \"$(cat <<'EOF'\nno proof\nEOF\n)\""):
            with self.subTest(command=command):
                self.calls.unlink(missing_ok=True)
                self.assert_drafted(self.run_hook(command), "## Verification")

    def test_the_pr_that_was_created_is_the_one_read_even_with_other_links_in_the_output(self):
        self.open_pr("", isDraft=True)
        self.run_hook("git log -1; gh pr create --fill", response=f"Reverts https://github.com/acme/app/pull/3\n{URL}")
        self.assertIn(f"pr view {URL}", self.gh_calls())
        self.assertNotIn("pull/3", self.gh_calls())

    def test_other_commands_and_a_missing_pr_do_nothing(self):
        self.open_pr("")
        self.assert_trusted(self.run_hook("gh pr view 3"))
        self.pr_json.unlink()
        self.assert_trusted(self.run_hook("gh pr create --web"))

    def test_a_pr_with_no_real_verification_lines_goes_back_to_draft(self):
        self.change("a.txt", "next\n")
        for body in ("", "## Verification\nIt works.\n", "## Verification\n- Ran: `<command>` <result>\n", "## Verification\n- Not run: nope\n", "<!--\n## Verification\n- Ran: `x` ok\n-->\n", "<!--\n## Verification\n- Ran: `x` ok\n", "## Verification\n- Ran:\nIt works.\n", "## Verification\n- Ran: TODO\n", "## Verification\n- Ran: `pnpm check`, <result>\n", "## Verification\n- Not run: <check>, because <why>\n"):
            with self.subTest(body=body):
                self.calls.unlink(missing_ok=True)
                self.open_pr(body)
                self.assert_drafted(self.run_hook(), "## Verification")

    def test_a_small_pr_with_proof_stays_ready_with_no_noise(self):
        self.change("a.txt", "next\n")
        self.record("Bash", {"command": "pnpm check"})
        self.open_pr(PROOF)
        result = self.run_hook()
        self.assert_trusted(result)
        self.assertEqual(result.stdout, "")

    def test_a_large_diff_needs_a_review_and_lockfiles_do_not_count(self):
        self.change("pnpm-lock.yaml", "line\n" * 500)
        self.record("Bash", {"command": "pnpm check"})
        self.open_pr(PROOF)
        self.assert_trusted(self.run_hook())
        self.change("big.txt", "line\n" * 200)
        self.open_pr(PROOF)
        self.assert_drafted(self.run_hook(), "200 lines")
        self.calls.unlink()
        self.record("Agent", {"subagent_type": "senior-reviewer", "prompt": "review"})
        self.assert_trusted(self.run_hook("gh pr ready"))

    def test_a_review_stated_in_verification_counts_but_a_hidden_or_unrelated_one_does_not(self):
        self.change("db/migrations/1.sql", "select 1;\n")
        self.record("Bash", {"command": "pnpm check"})
        for line in ("- Not run: review, because the file is a no-op\n", "- Ran: review by Sam in thread 12\n"):
            with self.subTest(line=line):
                self.open_pr(PROOF + line)
                self.assert_trusted(self.run_hook())
        for extra in ("<!--\n- Not run: review, because x\n-->\n", "- Not run: review-app, because deploys are off\n", "- Not run: review, because <why>\n", "- Ran: review\n", "- Ran: review app smoke test\n", "- Ran: review by <who and where>\n"):
            with self.subTest(extra=extra):
                self.calls.unlink(missing_ok=True)
                self.open_pr(PROOF + extra)
                self.assert_drafted(self.run_hook(), "migrations")

    def test_a_risky_word_inside_a_file_name_needs_a_review(self):
        self.record("Bash", {"command": "pnpm check"})
        for name in ("src/policy.ts", "src/authMiddleware.ts", "src/StripeClient.ts"):
            with self.subTest(name=name):
                self.calls.unlink(missing_ok=True)
                self.change(name, "export const a = 1;\n")
                self.open_pr(PROOF)
                self.assert_drafted(self.run_hook(), name)

    def test_a_builder_whose_name_contains_review_is_not_a_review(self):
        self.change("db/migrations/1.sql", "select 1;\n")
        self.record("Bash", {"command": "pnpm check"})
        self.record("Agent", {"subagent_type": "preview-builder"})
        self.open_pr(PROOF)
        self.assert_drafted(self.run_hook(), "migrations")

    def test_a_similar_word_is_not_a_risky_path(self):
        self.change("src/AuthorCard.tsx", "export const a = 1;\n")
        self.record("Bash", {"command": "pnpm check"})
        self.open_pr(PROOF)
        self.assert_trusted(self.run_hook())

    def test_a_skipped_test_goes_back_to_draft_unless_a_visible_line_justifies_it(self):
        self.change("a.test.ts", "it." + "skip('runs', () => {});\n")
        self.record("Bash", {"command": "pnpm check"})
        self.open_pr(PROOF)
        self.assert_drafted(self.run_hook(), "skip")
        self.calls.unlink()
        self.open_pr(PROOF + "\nAllowed skip: upstream bug 12\n")
        self.assert_trusted(self.run_hook())
        for hidden in ("<!-- Allowed skip: hidden -->", "Allowed skip: <why>"):
            with self.subTest(hidden=hidden):
                self.calls.unlink(missing_ok=True)
                self.open_pr(PROOF + f"\n{hidden}\n")
                self.assert_drafted(self.run_hook(), "skip")

    def test_an_untracked_scratch_file_is_not_part_of_the_pr(self):
        self.change("a.txt", "next\n")
        self.record("Bash", {"command": "pnpm check"})
        (self.repo / "scratch.test.ts").write_text("it." + "skip('x', () => {});\n")
        self.open_pr(PROOF)
        self.assert_trusted(self.run_hook())

    def test_a_ran_line_with_no_matching_command_gets_a_note_and_stays_ready(self):
        self.change("a.txt", "next\n")
        self.record("Bash", {"command": "git status"})
        self.open_pr(PROOF)
        result = self.run_hook()
        self.assert_trusted(result)
        self.assertIn("pnpm check", json.loads(result.stdout)["hookSpecificOutput"]["additionalContext"])

    def test_a_ran_line_with_quotes_matches_its_command_but_an_echo_of_it_does_not(self):
        self.change("a.txt", "next\n")
        self.record("Bash", {"command": 'pnpm test -t "price"'})
        self.open_pr('## Verification\n- Ran: `pnpm test -t "price"` ok\n')
        self.assertEqual(self.run_hook().stdout, "")
        self.open_pr(PROOF)
        self.record("Bash", {"command": 'echo "pnpm check"'})
        self.assertIn("pnpm check", self.run_hook().stdout)

    def test_a_pr_that_is_not_this_checkouts_head_gets_a_note(self):
        self.change("a.txt", "next\n")
        self.open_pr(PROOF, headRefOid="0" * 40)
        result = self.run_hook()
        self.assert_trusted(result)
        self.assertIn("HEAD", result.stdout)


if __name__ == "__main__":
    unittest.main()

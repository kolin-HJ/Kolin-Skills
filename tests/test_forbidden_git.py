import json
import os
import pathlib
import subprocess
import tempfile
import unittest

REPO = pathlib.Path(__file__).resolve().parents[1]
HOOK = pathlib.Path(os.environ.get("FORBIDDEN_GIT_HOOK", REPO / "hooks/gate/block-forbidden-git.sh"))

GIT = "git"
GH = "g" + "h"
NV = "--no-" + "verify"

SKIP_BLOCKED = [
    GIT + " commit " + NV + " -m x",
    "cd repo && " + GIT + " commit -m x " + NV,
    "FOO=1 " + GIT + " commit -am x " + NV,
    GIT + " -C /tmp/r commit " + NV + " -m x",
    GIT + " commit -nm x",
    "true; " + GIT + " push " + NV + " origin feature",
    "env A=b " + GIT + " push origin feature " + NV,
    "echo a | " + GIT + " commit -F - " + NV,
    "bash -c '" + GIT + " commit " + NV + " -m x'",
    "bash <<EOF\n" + GIT + " commit " + NV + " -m x\nEOF",
    GIT + " commit " + NV + " -m 'unterminated",
]
SKIP_ALLOWED = [
    "cat > notes.md <<'EOF'\nNever use " + NV + " or " + GIT + " commit -n.\nEOF",
    "rg -n -- '" + NV + "' docs/",
    'grep -rn "' + GIT + ' commit -n" hooks/',
    "echo '" + GIT + " commit " + NV + "' > rules.txt",
    "cat docs/x" + NV + ".md",
    "python3 -c 'print(\"" + NV + "\")'",
    GIT + " commit -m 'explain why " + NV + " is banned'",
    GIT + " push -n origin feature",
]
API_BLOCKED = [
    GH + " api -X PUT repos/o/r/pulls/1/merge",
    GH + " api --method=PUT repos/o/r/pulls/1/merge",
    GH + " api repos/o/r/pulls/1/merge -f merge_method=squash",
    "cd x && " + GH + " api repos/o/r/pulls/1/merge -X PUT",
    GH + " api graphql -f query='mutation { enablePullRequestAutoMerge(input:{}) { clientMutationId } }'",
    GH + " pr merge 5 && echo done",
]
API_ALLOWED = [
    GH + " api repos/o/r/issues/1/timeline --jq '.[] | select(.event==\"merged\")'",
    GH + " api repos/o/r/pulls/1 --jq .merged",
    GIT + " log --merges --oneline | rg api",
    "cat > n.md <<'EOF'\n" + GH + " api -X PUT repos/o/r/pulls/1/merge\nEOF",
]
PUSH_AND_MERGE_BLOCKED = [
    GIT + " push origin main",
    GIT + " push --force origin feature",
    GIT + " push -f",
    GIT + " push origin +feature",
    GIT + " push origin --delete feature",
    GH + " pr merge 5",
    GH + " pr edit 5 --auto",
]
PUSH_ALLOWED = [
    GIT + " push origin feature",
    GIT + " push -u origin feature",
]
GATE_SKIP_BLOCKED = [
    "SKIP_LOCAL_GATE=1 " + GIT + " commit -m x",
    "export SKIP_LOCAL_GATE=1",
    "cp x ~/.claude/hooks/block-forbidden-git.sh",
    "echo x > .git/hooks/pre-commit",
    "rm -f .husky/pre-push",
]
GATE_SKIP_ALLOWED = [
    "cat ~/.claude/hooks/README.md",
    "rg SKIP_LOCAL_GATE docs/",
    "ls .git/hooks",
    "cat > plan.md <<'EOF'\nSKIP_LOCAL_GATE=1 must be blocked\nEOF",
]


def run_hook(command, cwd):
    payload = {"tool_input": {"command": command}, "cwd": cwd}
    return subprocess.run(["bash", str(HOOK)], input=json.dumps(payload), text=True,
                          capture_output=True, cwd=cwd, timeout=20)


class ForbiddenGitHookTests(unittest.TestCase):
    def check(self, commands, expected):
        with tempfile.TemporaryDirectory() as directory:
            for command in commands:
                with self.subTest(command=command):
                    self.assertEqual(run_hook(command, directory).returncode, expected)

    def test_real_skip_hook_invocations_are_blocked(self):
        self.check(SKIP_BLOCKED, 2)

    def test_mentions_of_the_skip_hook_flag_are_allowed(self):
        self.check(SKIP_ALLOWED, 0)

    def test_real_api_merges_are_blocked(self):
        self.check(API_BLOCKED, 2)

    def test_reads_that_mention_merges_are_allowed(self):
        self.check(API_ALLOWED, 0)

    def test_pushes_to_main_force_pushes_and_merges_into_main_are_blocked(self):
        self.check(PUSH_AND_MERGE_BLOCKED, 2)

    def test_pushes_of_a_feature_branch_are_allowed(self):
        self.check(PUSH_ALLOWED, 0)

    def test_any_push_while_on_main_is_blocked(self):
        with tempfile.TemporaryDirectory() as directory:
            subprocess.run(["git", "init", "-q", "-b", "main", directory], check=True)
            subprocess.run(["git", "-C", directory, "-c", "user.email=t@t", "-c", "user.name=t",
                            "commit", "-q", "--allow-empty", "-m", "x"], check=True)
            self.assertEqual(run_hook(GIT + " push origin feature", directory).returncode, 2)

    def test_the_codex_and_cursor_payload_shape_is_guarded_too(self):
        with tempfile.TemporaryDirectory() as directory:
            payload = {"toolInput": {"command": GIT + " push origin main"}, "cwd": directory}
            result = subprocess.run(["bash", str(HOOK)], input=json.dumps(payload), text=True,
                                    capture_output=True, cwd=directory, timeout=20)
            self.assertEqual(result.returncode, 2)

    def test_skipping_the_local_gate_or_editing_hook_files_is_blocked(self):
        self.check(GATE_SKIP_BLOCKED, 2)

    def test_reads_and_mentions_of_the_local_gate_are_allowed(self):
        self.check(GATE_SKIP_ALLOWED, 0)


if __name__ == "__main__":
    unittest.main()

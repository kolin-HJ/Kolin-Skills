"""Block/allow cases for hooks/gate/block-forbidden-git.sh.

Forbidden strings are built by concatenation so this file never trips the hook when it is written or grepped.
"""
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


if __name__ == "__main__":
    unittest.main()

"""D4 cases: agents may not set SKIP_LOCAL_GATE or write hook files. Only installed with --with-d4."""
import unittest

from test_forbidden_git import GIT, ForbiddenGitHookTests

D4_BLOCKED = [
    "SKIP_LOCAL_GATE=1 " + GIT + " commit -m x",
    "export SKIP_LOCAL_GATE=1",
    "cp x ~/.claude/hooks/block-forbidden-git.sh",
    "echo x > .git/hooks/pre-commit",
    "sed -i s/a/b/ /workspace/kolin-skills/hooks/gate/gate-pass.sh",
    "rm -f .husky/pre-push",
]
D4_ALLOWED = [
    "cat ~/.claude/hooks/README.md",
    "rg SKIP_LOCAL_GATE docs/",
    "ls .git/hooks",
    "cat > plan.md <<'EOF'\nSKIP_LOCAL_GATE=1 must be blocked\nEOF",
]


class D4HookTests(ForbiddenGitHookTests):
    def test_d4_blocks_gate_skip_and_hook_edits(self):
        self.check(D4_BLOCKED, 2)

    def test_d4_allows_reads_and_mentions(self):
        self.check(D4_ALLOWED, 0)


del ForbiddenGitHookTests

if __name__ == "__main__":
    unittest.main()

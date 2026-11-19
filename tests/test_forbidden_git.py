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
    "echo $'a\\' #b'; " + GIT + " commit " + NV + " -m x",
    "echo ${x:- #}; " + GIT + " commit " + NV + " -m x",
    "echo a\r#b; " + GIT + " commit " + NV + " -m x",
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
    GIT + " -c core.hooksPath=/dev/null commit -m x",
    GIT + " -c core.hookspath=/tmp/empty push origin feature",
    "HUSKY=0 " + GIT + " commit -m x",
    "export HUSKY=0",
    "LEFTHOOK=0 " + GIT + " push origin feature",
    "env LEFTHOOK=false " + GIT + " commit -m x",
    "export LEFTHOOK=0",
    "LEFTHOOK_EXCLUDE=verify " + GIT + " push origin feature",
    "export LEFTHOOK_EXCLUDE=verify",
    "SKIP=eslint " + GIT + " commit -m x",
    "bash -c 'SKIP=eslint " + GIT + " commit -m x'",
    "export SKIP=eslint",
    GIT + " commit --no-gpg-sign -m x",
    GIT + " rebase --no-gpg-sign main",
    "LEFTHOOK=0 bash -c '" + GIT + " commit -m x'",
    "SKIP=eslint sh -c '" + GIT + " commit -m x'",
    "HUSKY=0 bash -c '" + GIT + " commit -m x'",
    "LEFTHOOK=0 eval '" + GIT + " commit -m x'",
    "export GIT_CONFIG_PARAMETERS=\"'core.hooksPath=/x'\"; " + GIT + " commit -m x",
    "export GIT_CONFIG_KEY_0=core.hooksPath",
    "LEFTHOOK=0; export LEFTHOOK; " + GIT + " commit -m x",
    "declare -x LEFTHOOK=0; " + GIT + " commit -m x",
    "LEFTHOOK_BIN=true " + GIT + " commit -m x",
    GIT + " commit --no-gpg-sig -m x",
    GIT + " commit --no-veri -m x",
    "GIT_CONFIG_PARAMETERS=\"'core.hooksPath=/dev/null'\" " + GIT + " commit -m x",
    GIT + " config set core.hooksPath /dev/null",
    GIT + " config --global core.hooksPath /dev/null",
    GIT + " config core.hooksPath /dev/null",
    "GIT_CONFIG_COUNT=1 GIT_CONFIG_KEY_0=core.hooksPath GIT_CONFIG_VALUE_0=/dev/null " + GIT + " commit -m x",
    "echo hi # note\n" + GIT + " commit " + NV + " -m x",
    'echo "$(' + GIT + " commit " + NV + ' -m x)"',
    'echo "`' + GIT + " commit " + NV + ' -m x`"',
    GIT + " commit -m x \\\n  " + NV,
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
    GIT + " -c user.name=x commit -m y",
    "rg HUSKY docs/",
    "HUSKY=0 npm install",
    "LEFTHOOK=0 npm install",
    "SKIP=1 npm install",
    "rg LEFTHOOK docs/",
    GIT + " commit --gpg-sign -m x",
    GIT + " config --get core.hooksPath",
    GIT + " config --get-all core.hooksPath",
    GIT + " config get core.hooksPath",
    GIT + " config --global --get core.hooksPath",
    GIT + " config --show-origin --get core.hooksPath",
    GIT + " config list",
    "LEFTHOOK_BIN=true npm install",
    GIT + " config user.name x",
    "GIT_CONFIG_COUNT=1 GIT_CONFIG_KEY_0=user.name GIT_CONFIG_VALUE_0=x " + GIT + " commit -m y",
]
API_BLOCKED = [
    GH + " api -X PUT repos/o/r/pulls/1/merge",
    GH + " api --method=PUT repos/o/r/pulls/1/merge",
    GH + " api repos/o/r/pulls/1/merge -f merge_method=squash",
    "cd x && " + GH + " api repos/o/r/pulls/1/merge -X PUT",
    GH + " api graphql -f query='mutation { enablePullRequestAutoMerge(input:{}) { clientMutationId } }'",
    GH + " pr merge 5 && echo done",
    "echo `" + GH + " pr merge 5`",
    "echo hi # note\n" + GH + " pr merge 5",
    'echo "$(' + GH + ' pr merge 5)"',
    'echo "`' + GH + ' pr merge 5`"',
]
REF_API_BLOCKED = [
    GH + " api -X PATCH repos/o/r/git/refs/heads/staging -f sha=abc -F force=true",
    GH + " api --method DELETE repos/o/r/git/refs/heads/main",
    GH + " api repos/o/r/git/refs/heads/sandbox -f sha=abc",
    GH + " api https://api.github.com/repos/o/r/git/refs/heads/Master --method=PATCH --input body.json",
    GH + " api graphql -f query='mutation { updateRef(input:{}) { clientMutationId } }'",
    GH + " api graphql -f query='mutation { updateRefs(input:{}) { clientMutationId } }'",
    GH + " api graphql -f query='mutation { deleteRef(input:{}) { clientMutationId } }'",
    GH + " api graphql -f query='mutation { createCommitOnBranch(input:{}) { clientMutationId } }'",
    GH + " api -X PATCH -f sha=abc -f force=true repos/o/r/git/refs/heads/main",
    GH + " api --input body.json repos/o/r/git/refs/heads/main",
    GH + " api -X DELETE repos/o/r/git/refs/heads%2Fmain",
    GH + " api -X DELETE repos/o/r/git/refs/heads/x/../%6Dain",
    GH + " api -X DELETE repos/o/r//git/refs/heads//staging/",
    GH + " api repos/o/r/git/refs/heads/main#x -XPATCH -f sha=x",
    GH + " api graphql#x -F query=@q.graphql",
    GH + " api graphql --input q.json",
    GH + " api graphql -F query=@q.graphql",
    GH + " api -X POST repos/o/r/branches/main/rename -f new_name=old",
    GH + " api -X DELETE repos/o/r/branches/staging/protection",
]
REF_API_ALLOWED = [
    GH + " api repos/o/r/git/refs -f ref=refs/heads/staging -f sha=abc",
    GH + " api repos/o/r/git/ref/heads/main --jq .object.sha",
    GH + " api repos/o/r/git/refs/heads/staging",
    GH + " api -X PATCH repos/o/r/git/refs/heads/feature -f sha=abc",
    GH + " api graphql -f query='mutation { createRef(input:{}) { clientMutationId } }'",
    GH + " api graphql -f query='query { viewer { login } }'",
    GH + " api repos/o/r/branches/main/protection",
    GH + " api -X POST repos/o/r/branches/feature/rename -f new_name=other",
]
PR_MERGE_MENTIONS_ALLOWED = [
    GIT + ' grep -nE "' + GH + ' pr merge|baseRefName" -- \':!tests\'',
    "rg '" + GH + " pr merge' hooks/ | head",
    "echo '" + GH + " pr merge 5' > notes.txt",
]
FILE_BLOCKED = [
    ".git/hooks/pre-commit",
    ".husky/pre-push",
    "lefthook.yml",
    os.path.expanduser("~/.claude/hooks/block-forbidden-git.sh"),
    "/x/.git/config",
    "/x/.githooks/pre-push",
    "/x/.GIT/hooks/pre-commit",
]
FILE_ALLOWED = [
    str(REPO / "hooks/gate/git_guard.py"),
    "src/app.py",
    "docs/husky-notes.md",
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
    GIT + " push -uf origin feature",
    GIT + " push --force-with-lease origin feature",
    GIT + " push origin :feature",
    GIT + " push -4f origin feature",
    GIT + " push --del origin feature",
    GIT + " -c a=b push --mirror",
    "env -u FOO " + GIT + " push -f origin feature",
    "timeout 60 " + GIT + " push -f origin feature",
    "{ " + GIT + " push -f origin feature; }",
    'echo "$(' + GIT + ' push -f origin feature)"',
    "echo `" + GIT + " push -f origin feature`",
    GIT + " push \\\n  -f origin feature",
    "GIT push -f origin feature",
    "echo x && " + GIT + " push origin HEAD:main",
    GIT + " push origin staging",
    GIT + " push origin HEAD:refs/heads/sandbox",
    GIT + " push origin HEAD:heads/staging",
    GIT + " push -u origin master",
    GIT + ' push origin "$(' + GIT + ' branch --show-current)" --force',
    GIT + " push origin 'HEAD:main'",
    GIT + " push origin '+feature:feature'",
    GIT + " push --m origin",
    "(" + GIT + " push origin main)",
    "(cd x && " + GIT + " push origin feature:main)",
    GIT + " push --prune origin 'refs/heads/*:refs/heads/*'",
    GH + " pr merge 5",
    GH + " pr edit 5 --auto",
]
PUSH_ALLOWED = [
    GIT + " push origin feature",
    GIT + " push -u origin feature",
    "printf msg | " + GIT + " commit -q -F - && " + GIT + " push origin HEAD:feature",
    GIT + " push origin feature && " + GH + " pr edit 5 --body-file /tmp/b -d x",
    GIT + " commit -m 'Merge main into feature' && " + GIT + " push origin feature",
    GIT + " push --dry-run -o ci.skip origin my-feature-d",
    GIT + " push origin feature/staging-copy",
    GIT + " push origin fix/main",
]
GATE_SKIP_BLOCKED = [
    "SKIP_LOCAL_GATE=1 " + GIT + " commit -m x",
    "export SKIP_LOCAL_GATE=1",
    "cp x ~/.claude/hooks/block-forbidden-git.sh",
    "echo x > .git/hooks/pre-commit",
    "rm -f .husky/pre-push",
    "echo hi # note\nrm -f .husky/pre-push",
]
GATE_SKIP_ALLOWED = [
    "cat ~/.claude/hooks/README.md",
    "rg SKIP_LOCAL_GATE docs/",
    "ls .git/hooks",
    "cat > plan.md <<'EOF'\nSKIP_LOCAL_GATE=1 must be blocked\nEOF",
]


def run_hook(command, cwd, env=None):
    payload = {"tool_input": {"command": command}, "cwd": cwd}
    return subprocess.run(["bash", str(HOOK)], input=json.dumps(payload), text=True,
                          capture_output=True, cwd=cwd, env=env, timeout=20)


def run_file_hook(path, cwd, key="tool_input"):
    payload = {key: {"file_path": path}, "cwd": cwd}
    return subprocess.run(["bash", str(HOOK)], input=json.dumps(payload), text=True,
                          capture_output=True, cwd=cwd, env={**os.environ, "HOME": cwd}, timeout=20)


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

    def test_any_push_while_on_a_protected_branch_is_blocked(self):
        for branch, expected in [("main", 2), ("master", 2), ("staging", 2), ("sandbox", 2), ("feature", 0)]:
            with self.subTest(branch=branch), tempfile.TemporaryDirectory() as directory:
                subprocess.run(["git", "init", "-q", "-b", branch, directory], check=True)
                subprocess.run(["git", "-C", directory, "-c", "user.email=t@t", "-c", "user.name=t",
                                "commit", "-q", "--allow-empty", "-m", "x"], check=True)
                self.assertEqual(run_hook(GIT + " push", directory).returncode, expected)

    def test_merging_a_pr_into_a_protected_branch_is_blocked(self):
        for base, expected in [("main", 2), ("master", 2), ("staging", 2), ("sandbox", 2), ("feature", 0)]:
            with self.subTest(base=base), tempfile.TemporaryDirectory() as directory:
                fake = pathlib.Path(directory, GH)
                fake.write_text("#!/bin/sh\necho " + base + "\n")
                fake.chmod(0o755)
                env = {**os.environ, "PATH": directory + os.pathsep + os.environ["PATH"]}
                self.assertEqual(run_hook(GH + " pr merge 5", directory, env).returncode, expected)

    def test_a_read_only_search_that_mentions_pr_merge_is_allowed(self):
        self.check(PR_MERGE_MENTIONS_ALLOWED, 0)

    def test_file_tools_cannot_edit_hook_files_but_can_edit_this_repos_hooks(self):
        with tempfile.TemporaryDirectory() as directory:
            for key in ("tool_input", "toolInput"):
                for path, expected in [(p, 2) for p in FILE_BLOCKED] + [(p, 0) for p in FILE_ALLOWED]:
                    with self.subTest(key=key, path=path):
                        self.assertEqual(run_file_hook(path, directory, key).returncode, expected)

    def test_the_codex_and_cursor_payload_shape_is_guarded_too(self):
        with tempfile.TemporaryDirectory() as directory:
            payload = {"toolInput": {"command": GIT + " push origin main"}, "cwd": directory}
            result = subprocess.run(["bash", str(HOOK)], input=json.dumps(payload), text=True,
                                    capture_output=True, cwd=directory, timeout=20)
            self.assertEqual(result.returncode, 2)

    def test_api_writes_to_a_protected_ref_are_blocked(self):
        self.check(REF_API_BLOCKED, 2)

    def test_creating_a_ref_through_the_api_and_reading_refs_are_allowed(self):
        self.check(REF_API_ALLOWED, 0)

    def test_skipping_the_local_gate_or_editing_hook_files_is_blocked(self):
        self.check(GATE_SKIP_BLOCKED, 2)

    def test_reads_and_mentions_of_the_local_gate_are_allowed(self):
        self.check(GATE_SKIP_ALLOWED, 0)


if __name__ == "__main__":
    unittest.main()

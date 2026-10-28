import json
import os
import pathlib
import shutil
import subprocess
import sys
import tempfile
import unittest

REPO = pathlib.Path(__file__).resolve().parents[1]
HOOK = REPO / "hooks/gate/block-forbidden-git.sh"
CLI = REPO / "bin/kolin-skills"
GIT = "git"


def git(cwd, *args):
    return subprocess.run([GIT, "-C", str(cwd), "-c", "user.email=t@t", "-c", "user.name=t", *args],
                          check=True, capture_output=True, text=True)


def init_repo(path):
    path.mkdir(parents=True)
    git(path, "init", "-q", "-b", "main")
    (path / "policy").mkdir()
    (path / "policy/AGENTS.md").write_text("policy\n")
    git(path, "add", "-A")
    git(path, "commit", "-qm", "init")


class InstallGuardTests(unittest.TestCase):
    def setUp(self):
        self.home = pathlib.Path(tempfile.mkdtemp()).resolve()
        self.addCleanup(shutil.rmtree, self.home)
        self.install = self.home / "Kolin-Skills"
        self.other = self.home / "other"
        init_repo(self.install)
        init_repo(self.other)
        (self.home / ".claude").mkdir()
        (self.home / ".claude/CLAUDE.md").symlink_to(self.install / "policy/AGENTS.md")

    def run_hook(self, command, cwd):
        payload = {"tool_input": {"command": command}, "cwd": str(cwd)}
        return subprocess.run(["bash", str(HOOK)], input=json.dumps(payload), text=True, capture_output=True,
                              cwd=str(cwd), env={**os.environ, "HOME": str(self.home)}, timeout=20)

    def test_changes_to_the_live_install_are_blocked_with_the_worktree_command(self):
        blocked = [
            (f"cd {self.install} && {GIT} switch -c x", self.home),
            (f"{GIT} -C {self.install} commit -m x", self.home),
            (f"{GIT} switch -c x", self.install),
            (f"{GIT} -C {self.install} branch feature", self.home),
            (f"{GIT} -C {self.install} reset --hard", self.home),
            (f"{GIT} -C {self.install} pull", self.home),
            (f"{GIT} -C {self.install} config user.name x", self.home),
            (f"{GIT} -C {self.install} stash", self.home),
            (f"{GIT} -C {self.install} branch -D feature", self.home),
        ]
        for command, cwd in blocked:
            with self.subTest(command=command):
                result = self.run_hook(command, cwd)
                self.assertEqual(result.returncode, 2)
                self.assertIn("live install every session runs from", result.stderr)
                self.assertIn(f"{GIT} -C {self.install} worktree add ~/.t3/worktrees/Kolin-Skills/<name>", result.stderr)

    def test_reads_fetch_and_worktrees_of_the_live_install_and_any_other_repo_are_allowed(self):
        allowed = [
            (f"{GIT} -C {self.install} status", self.home),
            (f"cd {self.install} && {GIT} log --oneline", self.home),
            (f"{GIT} -C {self.install} branch --show-current", self.home),
            (f"{GIT} -C {self.install} branch", self.home),
            (f"{GIT} -C {self.install} config --get remote.origin.url", self.home),
            (f"{GIT} -C {self.install} fetch", self.home),
            (f"{GIT} -C {self.install} worktree add {self.home}/wt -b x main", self.home),
            (f"{GIT} -C {self.install} rev-list --count HEAD", self.home),
            (f"{GIT} -C {self.install} merge-base HEAD main", self.home),
            (f"{GIT} -C {self.install} for-each-ref", self.home),
            (f"{GIT} -C {self.install} stash list", self.home),
            (f"{GIT} -C {self.install} ls-remote origin", self.home),
            (f"{GIT} -C {self.install} describe --always", self.home),
            (f"{GIT} -C {self.install} cat-file -p HEAD", self.home),
            (f"{GIT} -C {self.install} branch --merged main", self.home),
            (f"{GIT} -C {self.install} branch --contains HEAD", self.home),
            (f"{GIT} -C {self.install} config user.name", self.home),
            (f"{GIT} -C {self.install} worktree remove {self.home}/wt", self.home),
            (f"{GIT} switch -c x", self.other),
            (f"cd {self.other} && {GIT} commit --allow-empty -m x", self.install),
        ]
        for command, cwd in allowed:
            with self.subTest(command=command):
                self.assertEqual(self.run_hook(command, cwd).returncode, 0)

    def test_a_worktree_inside_the_install_directory_is_not_the_install(self):
        worktree = self.install / ".claude/worktrees/agent"
        git(self.install, "worktree", "add", "-q", "-b", "agent", str(worktree))
        self.assertEqual(self.run_hook(f"{GIT} switch -c y", worktree).returncode, 0)

    def test_the_rule_is_off_when_the_claude_policy_link_is_missing(self):
        (self.home / ".claude/CLAUDE.md").unlink()
        self.assertEqual(self.run_hook(f"{GIT} -C {self.install} switch -c x", self.home).returncode, 0)


    def run_file_hook(self, path, cwd):
        payload = {"tool_input": {"file_path": str(path)}, "cwd": str(cwd)}
        return subprocess.run(["bash", str(HOOK)], input=json.dumps(payload), text=True, capture_output=True,
                              cwd=str(cwd), env={**os.environ, "HOME": str(self.home)}, timeout=20)

    def test_edits_to_files_in_the_live_install_are_denied_but_not_in_worktrees_or_other_repos(self):
        worktree = self.install / ".claude/worktrees/agent"
        git(self.install, "worktree", "add", "-q", "-b", "agent", str(worktree))
        denied = [self.install / "policy/AGENTS.md", self.install / "new/dir/file.md"]
        allowed = [worktree / "policy/AGENTS.md", worktree / "new/file.md", self.other / "policy/AGENTS.md"]
        for path in denied:
            with self.subTest(path=str(path)):
                result = self.run_file_hook(path, self.home)
                self.assertEqual(result.returncode, 2)
                self.assertIn("Make the change in a Kolin-Skills worktree and ship it through a PR.", result.stderr)
        for path in allowed:
            with self.subTest(path=str(path)):
                self.assertEqual(self.run_file_hook(path, self.home).returncode, 0)

    def test_file_edits_in_the_install_are_allowed_when_the_claude_policy_link_is_missing(self):
        (self.home / ".claude/CLAUDE.md").unlink()
        self.assertEqual(self.run_file_hook(self.install / "policy/AGENTS.md", self.home).returncode, 0)


    def test_a_file_edit_is_denied_when_the_install_check_crashes(self):
        tools = self.home / "tools"
        tools.mkdir()
        for name, target in {"python3": sys.executable, "jq": shutil.which("jq"),
                             "readlink": shutil.which("readlink"), "dirname": shutil.which("dirname"),
                             "cat": shutil.which("cat")}.items():
            (tools / name).symlink_to(target)
        payload = {"tool_input": {"file_path": str(self.other / "a.md")}, "cwd": str(self.home)}
        result = subprocess.run([shutil.which("bash"), str(HOOK)], input=json.dumps(payload), text=True,
                                capture_output=True, env={"HOME": str(self.home), "PATH": str(tools)}, timeout=20)
        self.assertEqual(result.returncode, 2)
        self.assertIn("the install check could not run", result.stderr)


class StalePullTests(unittest.TestCase):
    def test_a_stale_setup_is_reported_as_session_start_json_that_the_user_sees(self):
        home = pathlib.Path(tempfile.mkdtemp()).resolve()
        self.addCleanup(shutil.rmtree, home)
        repo = home / "Kolin-Skills"
        shutil.copytree(REPO, repo, ignore=shutil.ignore_patterns(".git", "__pycache__"))
        (repo / "upstream/skills.json").write_text("{}\n")
        git(repo, "init", "-q", "-b", "main")
        git(repo, "add", "-A")
        git(repo, "commit", "-qm", "init")
        remote = home / "remote.git"
        other = home / "other-machine"
        git(home, "clone", "-q", "--bare", str(repo), str(remote))
        git(repo, "remote", "add", "origin", str(remote))
        git(home, "clone", "-q", str(remote), str(other))
        (other / "NOTE").write_text("x\n")
        git(other, "add", "-A")
        git(other, "commit", "-qm", "ahead")
        git(other, "push", "-q", "origin", "main")
        git(repo, "switch", "-q", "-c", "feature/x")
        result = subprocess.run([sys.executable, str(repo / "bin/kolin-skills"), "pull", "--quiet"],
                                env={**os.environ, "HOME": str(home)}, text=True, capture_output=True, timeout=60)
        self.assertEqual(result.returncode, 0, result.stderr)
        output = json.loads(result.stdout)
        message = output["systemMessage"]
        self.assertIn("stale setup", message)
        self.assertIn("it is on feature/x, not main", message)
        self.assertEqual(output["hookSpecificOutput"], {"hookEventName": "SessionStart", "additionalContext": message})


if __name__ == "__main__":
    unittest.main()

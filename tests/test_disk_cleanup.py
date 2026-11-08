import json
import os
import pathlib
import shutil
import subprocess
import sys
import tempfile
import time
import unittest

CLI = pathlib.Path(__file__).resolve().parent.parent / "bin/disk-cleanup"
DAY = 86400


class DiskCleanupTests(unittest.TestCase):
    def setUp(self):
        self.tmp = pathlib.Path(tempfile.mkdtemp()).resolve()
        self.home = self.tmp / "home"
        self.scan = self.tmp / "scan"
        self.origin = self.tmp / "origin.git"
        self.main = self.scan / "app"
        self.worktrees = self.home / ".t3" / "worktrees" / "app"
        self.cwds = self.tmp / "cwds.txt"
        self.home.mkdir()
        self.scan.mkdir()
        self.env = {**os.environ, "HOME": str(self.home), "PATH": f"{self.fake_tools()}:{os.environ['PATH']}",
                    "FAKE_CWDS": str(self.cwds)}
        self.build_repo()

    def fake_tools(self):
        bin_dir = self.tmp / "fake-bin"
        bin_dir.mkdir()
        scripts = {
            "gh": "echo '[]'",
            "npm": "exit 0",
            "pnpm": "exit 0",
            "docker": "exit 1",
            "lsof": '[ -f "$FAKE_CWDS" ] && cat "$FAKE_CWDS"; exit 0',
        }
        for name, body in scripts.items():
            tool = bin_dir / name
            tool.write_text(f"#!/bin/sh\n{body}\n")
            tool.chmod(0o755)
        return bin_dir

    def git(self, cwd, *args):
        done = subprocess.run(["git", "-C", str(cwd), "-c", "user.email=t@t", "-c", "user.name=t", *args],
                              check=True, capture_output=True, text=True, env=self.env)
        return done.stdout.strip()

    def commit(self, cwd, name):
        (pathlib.Path(cwd) / name).write_text(name)
        self.git(cwd, "add", "-A")
        self.git(cwd, "commit", "-qm", name)

    def gitdir(self, name):
        return self.main / ".git" / "worktrees" / name

    def age(self, name, days):
        stamp = time.time() - days * DAY
        gitdir = self.gitdir(name)
        for path in (gitdir / "HEAD", gitdir / "logs" / "HEAD"):
            os.utime(path, (stamp, stamp))

    def build_repo(self):
        subprocess.run(["git", "init", "-q", "--bare", "-b", "main", str(self.origin)], check=True, env=self.env)
        subprocess.run(["git", "init", "-q", "-b", "main", str(self.main)], check=True, env=self.env)
        self.git(self.main, "remote", "add", "origin", str(self.origin))
        self.commit(self.main, "base")
        self.git(self.main, "push", "-q", "origin", "main")
        self.worktrees.mkdir(parents=True)

        names = ["merged", "dirty", "unmerged", "detached", "active", "broken", "inuse", "recent"]
        for name in names:
            placement = ["--detach"] if name == "detached" else ["-b", name]
            self.git(self.main, "worktree", "add", "-q", str(self.worktrees / name), *placement)
        self.commit(self.worktrees / "merged", "merged-change")
        self.git(self.worktrees / "merged", "push", "-q", "origin", "HEAD:main")
        (self.worktrees / "dirty" / "base").write_text("edited")
        self.commit(self.worktrees / "unmerged", "unmerged-change")
        self.commit(self.worktrees / "detached", "detached-change")
        self.commit(self.worktrees / "active", "active-change")
        self.sha = {name: self.git(self.worktrees / name, "rev-parse", "HEAD")
                    for name in ("unmerged", "detached")}
        self.cwds.write_text(f"n{self.worktrees / 'inuse'}/src\n")
        shutil.rmtree(self.gitdir("broken"))
        for name in ("merged", "dirty", "unmerged", "detached", "inuse"):
            self.age(name, 10)

    def build_stacks(self):
        stacks = self.home / ".supabase" / "stacks"
        existing_root = self.tmp / "still-here"
        existing_root.mkdir()
        finished = subprocess.Popen(["true"])
        finished.wait()
        cases = {
            "gone": (self.tmp / "nowhere", finished.pid),
            "present": (existing_root, finished.pid),
            "running": (self.tmp / "nowhere-either", os.getpid()),
        }
        for name, (root, pid) in cases.items():
            (stacks / name).mkdir(parents=True)
            (stacks / name / "state.json").write_text(json.dumps({"identity": {"projectRoot": str(root)}}))
            (stacks / name / "owner.json").write_text(json.dumps({"pid": pid}))
        return stacks

    def cleanup(self, *args):
        done = subprocess.run([sys.executable, str(CLI), "--scan", str(self.scan), *args], env=self.env,
                              text=True, capture_output=True, timeout=120)
        self.assertEqual(done.returncode, 0, done.stdout + done.stderr)
        report = json.loads((self.home / ".kolin-skills" / "disk-cleanup.json").read_text())
        return {pathlib.Path(row["target"]).name: row for row in report}

    def test_dry_run_deletes_nothing(self):
        stacks = self.build_stacks()
        rows = self.cleanup()
        self.assertEqual(rows["merged"]["action"], "remove")
        self.assertEqual(rows["unmerged"]["action"], "archive")
        for name in ("merged", "dirty", "unmerged", "detached", "active", "inuse"):
            self.assertTrue((self.worktrees / name).exists(), name)
        self.assertTrue((stacks / "gone").exists())

    def test_apply_removes_only_what_is_safe(self):
        stacks = self.build_stacks()
        rows = self.cleanup("--apply")

        self.assertFalse((self.worktrees / "merged").exists())
        self.assertEqual(rows["merged"]["action"], "removed")

        self.assertEqual((self.worktrees / "dirty" / "base").read_text(), "edited")
        self.assertEqual(rows["dirty"]["reason"], "uncommitted changes")

        self.assertFalse((self.worktrees / "unmerged").exists())
        self.assertEqual(self.git(self.main, "rev-parse", "refs/heads/unmerged"), self.sha["unmerged"])

        self.assertFalse((self.worktrees / "detached").exists())
        self.assertEqual(self.git(self.main, "rev-parse", "refs/heads/archive/detached"), self.sha["detached"])

        self.assertTrue((self.worktrees / "active").exists())
        self.assertTrue((self.worktrees / "recent").exists())
        self.assertEqual(rows["recent"]["reason"], "used in the last 6 hours")
        self.assertTrue((self.worktrees / "inuse").exists())
        self.assertEqual(rows["inuse"]["reason"], "a running program is inside it")

        self.assertTrue((self.worktrees / "broken").exists())
        self.assertEqual(rows["broken"]["reason"], "git link missing")

        self.assertFalse((stacks / "gone").exists())
        self.assertTrue((stacks / "present").exists())
        self.assertTrue((stacks / "running").exists())
        self.assertEqual(rows["docker"]["action"], "skipped")


if __name__ == "__main__":
    unittest.main()

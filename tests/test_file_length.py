import os
import pathlib
import shutil
import subprocess
import sys
import tempfile
import unittest


REPO = pathlib.Path(__file__).resolve().parent.parent
CLI = REPO / "bin/kolin-skills"
PRE_COMMIT = REPO / ".githooks/pre-commit"
MAX_FILE_LINES = 1000


def git(cwd, *args):
    return subprocess.run(["git", "-C", str(cwd), "-c", "user.email=t@t", "-c", "user.name=t", *args],
                          check=True, capture_output=True, text=True)


class FileLengthGateTests(unittest.TestCase):
    def setUp(self):
        self.root = pathlib.Path(tempfile.mkdtemp())
        self.addCleanup(shutil.rmtree, self.root)
        git(self.root, "init", "-q", "-b", "main")
        (self.root / "bin").mkdir()
        shutil.copy(CLI, self.root / "bin/kolin-skills")

    def write_tracked(self, name, lines):
        path = self.root / name
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text("x\n" * lines)
        git(self.root, "add", name)
        return path

    def run_check(self, *args):
        env = {key: value for key, value in os.environ.items() if key != "CI"}
        return subprocess.run(
            [sys.executable, str(self.root / "bin/kolin-skills"), "check", *args],
            cwd=self.root, env=env, text=True, capture_output=True, timeout=20,
        )

    def test_a_file_over_the_limit_fails_check_and_a_file_at_the_limit_passes(self):
        self.write_tracked("hooks/ok.py", MAX_FILE_LINES)
        allowed = self.run_check("--files")
        self.assertEqual((allowed.returncode, allowed.stderr), (0, ""), allowed.stdout)
        self.write_tracked("hooks/long.py", MAX_FILE_LINES + 1)
        blocked = self.run_check("--files")
        self.assertEqual(blocked.returncode, 1, blocked.stderr)
        self.assertIn("hooks/long.py: 1001 lines", blocked.stderr)
        self.assertIn("1000-line limit", blocked.stderr)
        self.assertNotIn("hooks/ok.py", blocked.stderr)

    def test_pre_commit_blocks_the_over_limit_file_and_then_lets_the_split_through(self):
        hooks = self.root / ".githooks"
        hooks.mkdir()
        shutil.copy(PRE_COMMIT, hooks / "pre-commit")
        (hooks / "pre-commit").chmod(0o755)
        git(self.root, "config", "core.hooksPath", ".githooks")
        over = self.write_tracked("hooks/long.py", MAX_FILE_LINES + 1)
        env = {key: value for key, value in os.environ.items() if key != "CI"}
        blocked = subprocess.run(
            ["git", "-C", str(self.root), "-c", "user.email=t@t", "-c", "user.name=t", "commit", "-qm", "too long"],
            env=env, text=True, capture_output=True, timeout=20,
        )
        self.assertNotEqual(blocked.returncode, 0, blocked.stderr)
        self.assertIn("hooks/long.py: 1001 lines", blocked.stderr)
        over.write_text("x\n" * MAX_FILE_LINES)
        git(self.root, "add", "hooks/long.py")
        allowed = subprocess.run(
            ["git", "-C", str(self.root), "-c", "user.email=t@t", "-c", "user.name=t", "commit", "-qm", "split"],
            env=env, text=True, capture_output=True, timeout=20,
        )
        self.assertEqual(allowed.returncode, 0, allowed.stderr)


if __name__ == "__main__":
    unittest.main()

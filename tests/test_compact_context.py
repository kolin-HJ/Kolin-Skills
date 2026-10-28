import json
import pathlib
import subprocess
import sys
import tempfile
import unittest


HOOK = pathlib.Path(__file__).resolve().parent.parent / "hooks/compact-context.py"


def after_compact(cwd):
    result = subprocess.run(
        [sys.executable, str(HOOK), "after"],
        input=json.dumps({"cwd": str(cwd)}),
        text=True,
        capture_output=True,
        timeout=20,
    )
    assert result.returncode == 0, result.stderr
    output = json.loads(result.stdout)["hookSpecificOutput"]
    assert output["hookEventName"] == "SessionStart"
    return output["additionalContext"]


def git(cwd, *args):
    subprocess.run(["git", *args], cwd=cwd, check=True, capture_output=True)


class CompactContextTests(unittest.TestCase):
    def test_a_git_repo_reports_branch_commit_and_changed_files(self):
        with tempfile.TemporaryDirectory() as directory:
            git(directory, "init", "-b", "work")
            git(directory, "-c", "user.name=t", "-c", "user.email=t@t", "commit", "--allow-empty", "-m", "first")
            pathlib.Path(directory, "new.txt").write_text("x")
            context = after_compact(directory)
            self.assertIn("Branch: work", context)
            self.assertIn("first", context)
            self.assertIn("Changed files (1):\n?? new.txt", context)

    def test_a_directory_outside_git_says_so(self):
        with tempfile.TemporaryDirectory() as directory:
            self.assertIn("(not a git repository)", after_compact(directory))


if __name__ == "__main__":
    unittest.main()

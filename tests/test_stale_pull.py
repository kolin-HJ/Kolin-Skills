import json
import os
import pathlib
import shutil
import subprocess
import sys
import tempfile
import unittest

REPO = pathlib.Path(__file__).resolve().parents[1]
GIT = "git"


def git(cwd, *args):
    return subprocess.run([GIT, "-C", str(cwd), "-c", "user.email=t@t", "-c", "user.name=t", *args],
                          check=True, capture_output=True, text=True)


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
        git(home, "clone", "-q", "--bare", "--no-local", str(repo), str(remote))
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

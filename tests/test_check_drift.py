import json
import os
import pathlib
import shutil
import subprocess
import sys
import tempfile
import unittest

REPO = pathlib.Path(__file__).resolve().parent.parent
CLI = REPO / "bin/kolin-skills"
PIN = json.loads((REPO / "upstream/vendor.json").read_text())["cursor-plugins"]["rev"]
REVIEWER = (REPO / "agents/senior-reviewer.md").read_text()
STALE = "df58112aaaaaaaaaaaaaaaaaaaaaaaaaaaaaaa"


class CheckDriftTests(unittest.TestCase):
    def setUp(self):
        self.root = pathlib.Path(tempfile.mkdtemp())
        self.addCleanup(shutil.rmtree, self.root)

    def write(self, relative, text):
        path = self.root / relative
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(text)
        return path

    def run_cli(self, *args):
        env = {key: value for key, value in os.environ.items() if key != "CI"}
        return subprocess.run(
            [sys.executable, str(CLI), *args],
            cwd=self.root, env=env, text=True, capture_output=True, timeout=20,
        )

    def test_stale_pstack_source_fails_and_the_pin_passes(self):
        self.write(".agents/PSTACK.SOURCE",
                   "source: https://github.com/cursor/plugins/tree/main/pstack\n"
                   f"commit: {STALE}\n")
        stale = self.run_cli("check-drift", str(self.root))
        self.assertEqual(stale.returncode, 1, stale.stderr)
        self.assertIn("PSTACK.SOURCE", stale.stderr)
        self.assertIn(STALE[:12], stale.stderr)
        self.assertIn(PIN[:12], stale.stderr)
        self.write(".agents/PSTACK.SOURCE",
                   "source: https://github.com/cursor/plugins/tree/main/pstack\n"
                   f"commit: {PIN}\n")
        matched = self.run_cli("check-drift", str(self.root))
        self.assertEqual(matched.returncode, 0, matched.stderr)
        self.assertIn("Passed:", matched.stdout)

    def test_stale_vendor_json_fails_and_the_pin_passes(self):
        self.write("upstream/vendor.json", json.dumps({
            "cursor-plugins": {"url": "https://github.com/cursor/plugins.git", "rev": STALE},
        }) + "\n")
        stale = self.run_cli("check-drift", str(self.root))
        self.assertEqual(stale.returncode, 1, stale.stderr)
        self.assertIn("cursor-plugins", stale.stderr)
        self.assertIn(STALE[:12], stale.stderr)
        self.write("upstream/vendor.json", json.dumps({
            "cursor-plugins": {"url": "https://github.com/cursor/plugins.git", "rev": PIN},
        }) + "\n")
        matched = self.run_cli("check-drift", str(self.root))
        self.assertEqual(matched.returncode, 0, matched.stderr)

    def test_drifted_senior_reviewer_fails_and_a_copy_of_the_repo_file_passes(self):
        self.write(".claude/agents/senior-reviewer.md", REVIEWER + "\nextra drifted line\n")
        stale = self.run_cli("check-drift", str(self.root))
        self.assertEqual(stale.returncode, 1, stale.stderr)
        self.assertIn("senior-reviewer.md", stale.stderr)
        self.write(".claude/agents/senior-reviewer.md", REVIEWER)
        matched = self.run_cli("check-drift", str(self.root))
        self.assertEqual(matched.returncode, 0, matched.stderr)

    def test_this_repo_and_an_empty_tree_pass(self):
        here = self.run_cli("check-drift", str(REPO))
        self.assertEqual(here.returncode, 0, here.stderr)
        self.assertIn("Passed:", here.stdout)
        empty = self.run_cli("check-drift", str(self.root))
        self.assertEqual(empty.returncode, 0, empty.stderr)

    def test_check_with_a_target_fails_on_drift_without_rerunning_tests(self):
        self.write(".agents/PSTACK.SOURCE", f"commit: {STALE}\n")
        result = self.run_cli("check", str(self.root))
        self.assertEqual(result.returncode, 1, result.stderr)
        self.assertIn("PSTACK.SOURCE", result.stderr)
        self.assertNotIn("tests failed", result.stderr)
        self.assertNotIn("Ran:", result.stderr)


if __name__ == "__main__":
    unittest.main()

import json
import pathlib
import sys
import tempfile
import unittest

REPO = pathlib.Path(__file__).resolve().parent.parent
sys.path.insert(0, str(REPO / "bin"))

from kolin_skills.check import hook_command_problems


class HookCommandTests(unittest.TestCase):
    def repo_with_hook(self, command, mode):
        root = pathlib.Path(tempfile.mkdtemp())
        (root / "hooks").mkdir()
        script = root / "hooks/guard.sh"
        script.write_text("#!/bin/sh\nexit 0\n")
        script.chmod(mode)
        (root / "claude").mkdir()
        (root / "claude/settings.json").write_text(json.dumps({"hooks": {"PreToolUse": [{"hooks": [{"type": "command", "command": command}]}]}}))
        return root

    def test_a_script_run_directly_without_the_executable_bit_is_a_failure(self):
        root = self.repo_with_hook("'{{REPO}}/hooks/guard.sh'", 0o644)
        self.assertIn("not executable", hook_command_problems(root)[0])

    def test_the_same_script_run_through_bash_passes(self):
        root = self.repo_with_hook("bash '{{REPO}}/hooks/guard.sh'", 0o644)
        self.assertEqual(hook_command_problems(root), [])

    def test_a_missing_script_is_a_failure(self):
        root = self.repo_with_hook("python3 '{{REPO}}/hooks/gone.py'", 0o755)
        self.assertIn("does not exist", hook_command_problems(root)[0])

    def test_the_shipped_hooks_all_run(self):
        self.assertEqual(hook_command_problems(), [])

    def test_antigravity_missing_hook_script_is_reported(self):
        root = pathlib.Path(tempfile.mkdtemp())
        (root / "antigravity").mkdir()
        (root / "antigravity/hooks.json").write_text(json.dumps({
            "kolin-skills": {"SessionStart": [{"type": "command", "command": "python3 '{{REPO}}/bin/missing'"}]}
        }))
        self.assertIn("does not exist", hook_command_problems(root)[0])


if __name__ == "__main__":
    unittest.main()

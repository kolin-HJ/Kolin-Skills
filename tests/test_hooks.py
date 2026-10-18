import json
import pathlib
import subprocess
import sys
import tempfile
import unittest


REPO = pathlib.Path(__file__).resolve().parent.parent
LINT_HOOK = REPO / "hooks/lint-changed-lines.py"
ENV_HOOK = REPO / "hooks/block-env-reads.py"
MODE_HOOK = REPO / "skills/pstack-local/scripts/mode-reminder"


def invoke(hook, payload, cwd):
    return subprocess.run(
        [sys.executable, str(hook)],
        input=json.dumps(payload),
        text=True,
        capture_output=True,
        cwd=cwd,
        timeout=10,
    )


class NativeHookPayloadTests(unittest.TestCase):
    def test_lint_reports_the_edited_file_for_native_payloads(self):
        with tempfile.TemporaryDirectory() as directory:
            root = pathlib.Path(directory)
            (root / "package.json").write_text("{}")
            (root / "edited.ts").write_text("const value = 1;\n")
            executable = root / "node_modules/.bin/eslint"
            executable.parent.mkdir(parents=True)
            executable.write_text(
                f"#!{sys.executable}\n"
                "import json,sys\n"
                "print(json.dumps([{'messages': [{'ruleId': 'fixture/no-unused-value', "
                "'severity': 2, 'line': 1, 'column': 7, 'message': 'Unused value.'}]}]))\n"
                "sys.exit(1)\n"
            )
            executable.chmod(0o755)
            payloads = [
                {"tool_input": {"file_path": "edited.ts"}},
                {"toolInput": {"target_file": "edited.ts"}},
                {"tool_input": {"path": "edited.ts"}},
                {"tool_input": "*** Begin Patch\n*** Update File: edited.ts\n*** End Patch"},
            ]
            for payload in payloads:
                with self.subTest(payload=payload):
                    result = invoke(LINT_HOOK, {"cwd": directory, **payload}, directory)
                    self.assertEqual(result.returncode, 2, result.stderr)
                    self.assertEqual(result.stdout, "")
                    self.assertIn("Lint: 1 error on lines you changed in edited.ts", result.stderr)
                    self.assertIn("1:7  error  Unused value.  (fixture/no-unused-value)", result.stderr)

    def test_env_guard_blocks_native_commands_and_allows_safe_operands(self):
        with tempfile.TemporaryDirectory() as directory:
            for key in ["tool_input", "toolInput"]:
                with self.subTest(key=key):
                    blocked = invoke(ENV_HOOK, {key: {"command": "cat .env.production"}}, directory)
                    allowed = invoke(ENV_HOOK, {key: {"command": "cat README.md"}}, directory)
                    self.assertEqual(blocked.returncode, 2)
                    self.assertIn("Blocked: `.env.production` is a .env file.", blocked.stderr)
                    self.assertEqual((allowed.returncode, allowed.stdout, allowed.stderr), (0, "", ""))

    def test_env_guard_covers_file_tools_not_only_shell(self):
        with tempfile.TemporaryDirectory() as directory:
            for tool_input in [{"file_path": f"{directory}/.env.local"}, {"pattern": "KEY", "path": ".env"},
                               {"pattern": "KEY", "glob": ".env*"}]:
                with self.subTest(tool_input=tool_input):
                    result = invoke(ENV_HOOK, {"tool_input": tool_input}, directory)
                    self.assertEqual(result.returncode, 2, result.stderr)
            for tool_input in [{"file_path": f"{directory}/.env.example"}, {"pattern": "env", "path": "src"}]:
                with self.subTest(tool_input=tool_input):
                    self.assertEqual(invoke(ENV_HOOK, {"tool_input": tool_input}, directory).returncode, 0)

    def test_mode_reminder_routes_full_send_and_full_stop(self):
        with tempfile.TemporaryDirectory() as directory:
            for prompt, skill in [
                ("Fix the grid filter. Full send.", "full-send"),
                ("full stop on PR 812", "full-stop"),
                ("/full-send 812", "full-send"),
            ]:
                with self.subTest(prompt=prompt):
                    result = invoke(MODE_HOOK, {"prompt": prompt}, directory)
                    self.assertEqual(result.returncode, 0, result.stderr)
                    context = json.loads(result.stdout)["hookSpecificOutput"]["additionalContext"]
                    self.assertIn(f"~/.agents/skills/{skill}/SKILL.md", context)
            plain = invoke(MODE_HOOK, {"prompt": "Fix the grid filter."}, directory)
            context = json.loads(plain.stdout)["hookSpecificOutput"]["additionalContext"]
            self.assertNotIn("full-send", context)
            self.assertIn("value case", context)
            self.assertNotIn("full-stop", context)


if __name__ == "__main__":
    unittest.main()

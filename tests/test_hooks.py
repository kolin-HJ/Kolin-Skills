import json
import os
import pathlib
import subprocess
import sys
import tempfile
import time
import unittest


REPO = pathlib.Path(__file__).resolve().parent.parent
LINT_HOOK = REPO / "hooks/lint-changed-lines.py"
ENV_HOOK = REPO / "hooks/block-env-reads.py"
MODE_HOOK = REPO / "skills/pstack-local/scripts/mode-reminder"
HEAVY_HOOK = REPO / "hooks/heavy-jobs.py"
SLOT = REPO / "hooks/heavy-slot.py"


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

    def test_heavy_jobs_blocks_sleep_polling_in_the_foreground_only(self):
        with tempfile.TemporaryDirectory() as directory:
            cases = [
                ({"command": "until [ -f out.json ]; do sleep 15; done"}, 2),
                ({"command": "for i in $(seq 1 59); do [ -f s.json ] && break; sleep 10; done"}, 2),
                ({"command": "until [ -f out.json ]; do sleep 15; done", "run_in_background": True}, 0),
                ({"command": "until curl -sf localhost:3000; do sleep 1; done"}, 0),
                ({"command": "cat > poll.sh <<'EOF'\nwhile true; do sleep 30; done\nEOF\nchmod +x poll.sh"}, 0),
                ({"command": "for f in a b; do echo $f; done\nsleep 5"}, 0),
                ({"command": "echo \"wait for it to do\"; sleep 5"}, 0),
            ]
            for tool_input, code in cases:
                with self.subTest(tool_input=tool_input):
                    result = invoke(HEAVY_HOOK, {"tool_input": tool_input}, directory)
                    self.assertEqual(result.returncode, code, result.stderr)
            blocked = invoke(HEAVY_HOOK, {"tool_input": cases[0][0]}, directory)
            self.assertIn("run_in_background: true", blocked.stderr)

    def test_heavy_jobs_queues_gate_commands_behind_a_slot(self):
        with tempfile.TemporaryDirectory() as directory:
            cases = [
                ({"command": "pnpm check 2>&1 | tail -40", "description": "Run gate"}, 60, 180000),
                ({"command": "cd web && npx vitest run", "timeout": 300000}, 150, 450000),
                ({"command": "pnpm verify", "run_in_background": True}, 900, 2700000),
            ]
            for tool_input, max_wait, timeout in cases:
                with self.subTest(tool_input=tool_input):
                    result = invoke(HEAVY_HOOK, {"tool_input": tool_input}, directory)
                    updated = json.loads(result.stdout)["hookSpecificOutput"]["updatedInput"]
                    command = f"python3 {SLOT} $$ {max_wait}\n{tool_input['command']}"
                    self.assertEqual(updated, {**tool_input, "command": command, "timeout": timeout})
            for command in ["git status --short", 'git commit -m "gate: pnpm check green"',
                            "gh pr create --body 'Ran: pnpm check'", "rg tsc docs/", "cat vitest.config.ts",
                            "pnpm test --watch", "pnpm dev"]:
                with self.subTest(command=command):
                    light = invoke(HEAVY_HOOK, {"tool_input": {"command": command}}, directory)
                    self.assertEqual((light.returncode, light.stdout, light.stderr), (0, "", ""))

    def test_heavy_slot_runs_three_jobs_and_queues_the_fourth_until_one_exits(self):
        with tempfile.TemporaryDirectory() as directory:
            env = {**os.environ, "HEAVY_SLOT_DIR": directory}
            def job(max_wait, then):
                return subprocess.Popen(["sh", "-c", f"python3 '{SLOT}' $$ {max_wait}; {then}"], env=env,
                                        stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True)
            holders = [job(5, "sleep 3") for _ in range(3)]
            time.sleep(1)
            impatient = job(0, "echo ran")
            self.assertEqual(impatient.communicate(timeout=10), ("ran\n", "heavy-slot: all 3 heavy-job slots stayed busy for 0s; running anyway.\n"))
            started = time.monotonic()
            fourth = job(30, "echo ran")
            out, err = fourth.communicate(timeout=30)
            self.assertEqual(out, "ran\n")
            self.assertRegex(err, r"^heavy-slot: waited \d+s for one of 3 heavy-job slots\.\n$")
            self.assertGreaterEqual(time.monotonic() - started, 1)
            for holder in holders:
                self.assertEqual(holder.communicate(timeout=10), ("", ""))


if __name__ == "__main__":
    unittest.main()

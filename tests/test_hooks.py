import json
import os
import pathlib
import subprocess
import sys
import tempfile
import time
import unittest
from unittest import mock


REPO = pathlib.Path(__file__).resolve().parent.parent
LINT_HOOK = REPO / "hooks/lint-changed-lines.py"
ENV_HOOK = REPO / "hooks/block-env-reads.py"
MODE_HOOK = REPO / "skills/pstack-local/scripts/mode-reminder"
HEAVY_HOOK = REPO / "hooks/heavy-jobs.py"
SLOT = REPO / "hooks/heavy-slot.py"
MODEL_HOOK = REPO / "hooks/agent-default-model.py"


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

    def test_lint_fails_loudly_when_a_linter_prints_non_json_or_the_payload_is_not_json(self):
        with tempfile.TemporaryDirectory() as directory:
            root = pathlib.Path(directory)
            (root / "package.json").write_text("{}")
            (root / "edited.ts").write_text("const value = 1;\n")
            executable = root / "node_modules/.bin/eslint"
            executable.parent.mkdir(parents=True)
            executable.write_text(f"#!{sys.executable}\nprint('not json')\n")
            executable.chmod(0o755)
            garbled = invoke(LINT_HOOK, {"cwd": directory, "tool_input": {"file_path": "edited.ts"}}, directory)
            self.assertEqual(garbled.returncode, 0, garbled.stderr)
            self.assertIn("eslint exited 0 and checked nothing: not json", garbled.stdout)
            bad_payload = subprocess.run([sys.executable, str(LINT_HOOK)], input="{", text=True,
                                         capture_output=True, cwd=directory, timeout=10)
            self.assertNotEqual(bad_payload.returncode, 0)
            self.assertIn("JSONDecodeError", bad_payload.stderr)

    def test_lint_covers_files_a_shell_command_wrote(self):
        with tempfile.TemporaryDirectory() as directory:
            root = pathlib.Path(directory)
            subprocess.run(["git", "init", "-q", directory], check=True)
            (root / "package.json").write_text("{}")
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
            (root / ".gitignore").write_text("node_modules\n")
            (root / "edited.ts").write_text("const value = 1;\n")
            written = invoke(LINT_HOOK, {"cwd": directory, "tool_name": "Bash",
                                         "tool_input": {"command": "sed -i '' 's/1/2/' edited.ts"}}, directory)
            read_only = invoke(LINT_HOOK, {"cwd": directory, "tool_name": "Bash",
                                           "tool_input": {"command": "rg -n value edited.ts"}}, directory)
            self.assertEqual(written.returncode, 2, written.stderr)
            self.assertIn("Lint: 1 error on lines you changed in edited.ts", written.stderr)
            for command in ["sed -E -i '' s/1/2/ edited.ts", "printf 'const value = 2;' > edited.ts",
                            "python3 -c \"json.dump(1, open('edited.ts','w'))\""]:
                with self.subTest(command=command):
                    result = invoke(LINT_HOOK, {"cwd": directory, "tool_name": "Bash",
                                                "tool_input": {"command": command}}, directory)
                    self.assertEqual(result.returncode, 2, result.stderr)
            search = invoke(LINT_HOOK, {"cwd": directory, "tool_name": "Bash",
                                        "tool_input": {"command": "rg -n '=>' src > /tmp/out <<< x"}}, directory)
            self.assertEqual((read_only.returncode, read_only.stderr), (0, ""))
            self.assertEqual((search.returncode, search.stderr), (0, ""))
            for name in "abcde":
                (root / f"{name}.ts").write_text("const value = 1;\n")
            many = invoke(LINT_HOOK, {"cwd": directory, "tool_name": "Bash", "tool_input": {
                "command": "sed -i '' 's/1/2/' a.ts b.ts c.ts d.ts e.ts"}}, directory)
            self.assertEqual(many.returncode, 2, many.stderr)
            self.assertEqual(many.stderr.count("Lint: 1 error on lines you changed in"), 4, many.stderr)
            self.assertIn("Not linted, so run the repo's lint for: e.ts.", many.stderr)

    def test_agent_model_runs_builders_on_sonnet_and_denies_fork(self):
        with tempfile.TemporaryDirectory() as directory:
            agents = pathlib.Path(directory) / ".claude/agents"
            agents.mkdir(parents=True)
            (agents / "repo-builder.md").write_text("---\nname: repo-builder\n---\nBody with model: words.\n")
            (agents / "repo-reviewer.md").write_text("---\nname: repo-reviewer\nmodel: claude-opus-5-5\n---\n")
            (agents / "read-only.md").write_text("---\nname: read-only\ntools: Read, Grep, Bash\n---\n")
            (agents / "read-only-opus.md").write_text("---\nname: read-only-opus\ntools: Read, Grep\n---\n")
            (agents / "inherits.md").write_text("---\nname: inherits\nmodel: inherit\n---\n")
            (agents / "seat.md").write_text("---\nname: seat\nmodel: claude-sonnet-5-5\n---\n")
            sonnet = ("allow", "sonnet")
            cases = [
                ({"subagent_type": "repo-builder"}, {}, sonnet),
                ({"subagent_type": "general-purpose"}, {}, sonnet),
                ({"subagent_type": "repo-reviewer"}, {}, None),
                ({"subagent_type": "repo-builder", "model": "opus"}, {}, sonnet),
                ({"subagent_type": "seat", "model": "opus"}, {}, sonnet),
                ({"subagent_type": "general-purpose", "model": "opus"}, {}, sonnet),
                ({"subagent_type": "general-purpose", "model": "opus"}, {"KOLIN_OPUS_BUILDERS": "1"}, None),
                ({"model": "opus"}, {}, sonnet),
                ({}, {}, sonnet),
                ({"subagent_type": "fork"}, {}, ("deny", None)),
                ({"subagent_type": "Explore", "model": "opus"}, {}, None),
                ({"subagent_type": "Explore"}, {}, sonnet),
                ({"subagent_type": "read-only-opus", "model": "opus"}, {}, None),
                ({"subagent_type": "general-purpose", "model": "haiku"}, {}, None),
                ({"subagent_type": "Plan"}, {}, None),
                ({"subagent_type": "read-only"}, {}, None),
                ({"subagent_type": "inherits"}, {}, None),
                ({"subagent_type": "no-such-agent"}, {}, None),
            ]
            nested = pathlib.Path(directory, "app/src")
            nested.mkdir(parents=True)
            for tool_input, env, expected in cases:
                with self.subTest(tool_input=tool_input, env=env):
                    with mock.patch.dict(os.environ, env):
                        if not env:
                            os.environ.pop("KOLIN_OPUS_BUILDERS", None)
                        result = invoke(MODEL_HOOK, {"cwd": str(nested), "tool_input": tool_input}, directory)
                    self.assertEqual(result.returncode, 0, result.stderr)
                    output = json.loads(result.stdout)["hookSpecificOutput"] if result.stdout else None
                    got = None if output is None else (output["permissionDecision"], output.get("updatedInput", {}).get("model"))
                    self.assertEqual(got, expected)

    def test_agent_model_denies_worktree_isolation_for_editing_agents_only(self):
        with tempfile.TemporaryDirectory() as directory:
            agents = pathlib.Path(directory) / ".claude/agents"
            agents.mkdir(parents=True)
            (agents / "poteto-agent.md").write_text("---\nname: poteto-agent\n---\n")
            cases = [
                ({"subagent_type": "poteto-agent", "isolation": "worktree"}, "deny"),
                ({"subagent_type": "Explore", "isolation": "worktree"}, "allow"),
                ({"subagent_type": "poteto-agent"}, "allow"),
            ]
            for tool_input, expected in cases:
                with self.subTest(tool_input=tool_input):
                    result = invoke(MODEL_HOOK, {"cwd": directory, "tool_input": tool_input}, directory)
                    self.assertEqual(result.returncode, 0, result.stderr)
                    output = json.loads(result.stdout)["hookSpecificOutput"]
                    self.assertEqual(output["permissionDecision"], expected)
                    if expected == "deny":
                        self.assertIn("git worktree add", output["permissionDecisionReason"])

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
            notice = invoke(MODE_HOOK, {"prompt": "<task-notification>\n<status>completed</status>"}, directory)
            self.assertEqual((notice.returncode, notice.stdout), (0, ""))
            plain = invoke(MODE_HOOK, {"prompt": "Fix the grid filter."}, directory)
            context = json.loads(plain.stdout)["hookSpecificOutput"]["additionalContext"]
            self.assertNotIn("full-send", context)
            self.assertNotIn("full-stop", context)

    def test_mode_reminder_flags_a_stale_status_file(self):
        with tempfile.TemporaryDirectory() as directory:
            root = pathlib.Path(os.path.realpath(directory))
            subprocess.run(["git", "init", "-q", str(root)], check=True)
            status = root / ".pstack/status.md"
            status.parent.mkdir()
            status.write_text("Value: feature\n")
            nested = root / "src"
            nested.mkdir()
            stale = "`.pstack/status.md` was last updated 90 minutes ago."

            def context():
                result = invoke(MODE_HOOK, {"prompt": "Where are we?", "cwd": str(nested)}, directory)
                self.assertEqual(result.returncode, 0, result.stderr)
                return json.loads(result.stdout)["hookSpecificOutput"]["additionalContext"]

            ninety_minutes_ago = time.time() - 90 * 60
            os.utime(status, (ninety_minutes_ago, ninety_minutes_ago))
            self.assertIn(stale, context())
            os.utime(status)
            self.assertNotIn("status.md", context())
            status.unlink()
            self.assertNotIn("status.md", context())
            nowhere = invoke(MODE_HOOK, {"prompt": "Where are we?"}, directory)
            self.assertEqual(nowhere.returncode, 0, nowhere.stderr)
            self.assertIn("New engineering task", json.loads(nowhere.stdout)["hookSpecificOutput"]["additionalContext"])

    def test_heavy_jobs_blocks_sleep_polling_in_the_foreground_only(self):
        with tempfile.TemporaryDirectory() as directory:
            cases = [
                ({"command": "until [ -f out.json ]; do sleep 15; done"}, 2),
                ({"command": "for i in $(seq 1 59); do [ -f s.json ] && break; sleep 10; done"}, 2),
                ({"command": "until [ -f out.json ]; do sleep 15; done", "run_in_background": True}, 0),
                ({"command": "until curl -sf localhost:3000; do sleep 1; done"}, 0),
                ({"command": "cat > /tmp/poll.sh <<'EOF'\nwhile true; do sleep 30; done\nEOF\nchmod +x /tmp/poll.sh"}, 0),
                ({"command": "for f in a b; do echo $f; done\nsleep 5"}, 0),
                ({"command": "echo \"wait for it to do\"; sleep 5"}, 0),
            ]
            for tool_input, code in cases:
                with self.subTest(tool_input=tool_input):
                    result = invoke(HEAVY_HOOK, {"tool_input": tool_input}, directory)
                    self.assertEqual(result.returncode, code, result.stderr)
            blocked = invoke(HEAVY_HOOK, {"tool_input": cases[0][0]}, directory)
            self.assertIn("run_in_background: true", blocked.stderr)

    def test_heavy_jobs_blocks_a_database_run_in_docker(self):
        with tempfile.TemporaryDirectory() as directory:
            cases = [
                ("docker exec supabase_db_hj-plm psql -U postgres -c 'select 1'", 2),
                ("docker ps --format '{{.Names}}' | grep supabase_db", 2),
                ("docker compose up -d postgres", 2),
                ("docker run -d -p 5432:5432 postgres:17", 2),
                ("supabase start --runtime native --output-format json", 0),
                ("psql \"$DB_URL\" -c 'select 1'", 0),
                ("docker build -t app .", 0),
                ("echo 'never docker exec supabase_db'", 0),
            ]
            for command, code in cases:
                with self.subTest(command=command):
                    result = invoke(HEAVY_HOOK, {"tool_input": {"command": command}}, directory)
                    self.assertEqual(result.returncode, code, result.stderr)
            blocked = invoke(HEAVY_HOOK, {"tool_input": {"command": cases[0][0]}}, directory)
            self.assertIn("local-supabase", blocked.stderr)

    def test_heavy_jobs_queues_gate_commands_behind_a_slot(self):
        with tempfile.TemporaryDirectory() as directory:
            cases = [
                ({"command": "pnpm check 2>&1", "description": "Run gate"}, 60, 180000),
                ({"command": "cd web && npx vitest run", "timeout": 300000}, 150, 450000),
                ({"command": "pnpm verify", "run_in_background": True}, 900, 2700000),
                ({"command": "pnpm test", "timeout": 590000}, 10, 600000),
            ]
            for tool_input, max_wait, timeout in cases:
                with self.subTest(tool_input=tool_input):
                    result = invoke(HEAVY_HOOK, {"tool_input": tool_input}, directory)
                    updated = json.loads(result.stdout)["hookSpecificOutput"]["updatedInput"]
                    command = f"python3 {pathlib.Path.home() / '.kolin-skills/bin/heavy-slot.py'} $$ {max_wait}\n{tool_input['command']}"
                    self.assertEqual(updated, {**tool_input, "command": command, "timeout": timeout})
            for command in ["git status --short", 'git commit -m "gate: pnpm check green"',
                            "gh pr create --body 'Ran: pnpm check'", "rg tsc docs/", "cat vitest.config.ts",
                            "pnpm test --watch", "pnpm dev"]:
                with self.subTest(command=command):
                    light = invoke(HEAVY_HOOK, {"tool_input": {"command": command}}, directory)
                    self.assertEqual((light.returncode, light.stdout, light.stderr), (0, "", ""))

    def test_heavy_slot_keeps_the_machine_awake_until_the_job_exits(self):
        with tempfile.TemporaryDirectory() as directory:
            bin_dir = pathlib.Path(directory) / "bin"
            bin_dir.mkdir()
            record = pathlib.Path(directory) / "caffeinate-args"
            fake = bin_dir / "caffeinate"
            fake.write_text(f"#!/bin/sh\necho \"$@\" > '{record}'\n")
            fake.chmod(0o755)
            env = {**os.environ, "HEAVY_SLOT_DIR": directory, "PATH": f"{bin_dir}:{os.environ['PATH']}"}
            job = subprocess.run(["sh", "-c", f"python3 '{SLOT}' $$ 0; echo $$"], env=env,
                                 capture_output=True, text=True, timeout=10)
            deadline = time.monotonic() + 5
            while not record.exists() and time.monotonic() < deadline:
                time.sleep(0.05)
            self.assertEqual(record.read_text(), f"-i -w {job.stdout.strip()}\n")

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

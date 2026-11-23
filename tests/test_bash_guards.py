import json
import os
import pathlib
import re
import stat
import subprocess
import sys
import tempfile
import unittest


REPO = pathlib.Path(__file__).resolve().parent.parent
BASH_GUARD = REPO / "hooks/bash-guard.py"
ENV_HOOK = REPO / "hooks/block-env-reads.py"


def invoke(hook, tool_input, **payload):
    with tempfile.TemporaryDirectory() as directory:
        return subprocess.run(
            [sys.executable, str(hook)],
            input=json.dumps({"tool_input": tool_input, **payload}),
            text=True,
            capture_output=True,
            cwd=directory,
            timeout=10,
        )


def updated_input(result):
    return json.loads(result.stdout)["hookSpecificOutput"]["updatedInput"] if result.stdout else None


class HeavyJobsGuardTests(unittest.TestCase):
    def test_slot_prefix_names_no_git_path(self):
        command = "pnpm check"
        updated = updated_input(invoke(BASH_GUARD, {"command": command}))
        prefix = updated["command"].removesuffix(command)
        self.assertIn(".kolin-skills/bin/heavy-slot.py", prefix)
        self.assertNotIn("git", prefix.lower())

    def test_shell_file_edits_pass_on_the_main_thread(self):
        for command in ["sed -i 's/a/b/' src/app.ts", "cat > notes.md <<'EOF'\nhi\nEOF", "echo hi > src/x"]:
            with self.subTest(command=command):
                result = invoke(BASH_GUARD, {"command": command})
                self.assertEqual((result.returncode, result.stderr), (0, ""))

    def syntax_check(self, command):
        return subprocess.run(["bash", "-n"], input=command, text=True, capture_output=True).returncode

    def test_git_push_takes_a_slot_and_gate_filters_are_dropped(self):
        prefix_pattern = re.compile(r"^python3 \S+heavy-slot\.py \$\$ \d+\n")
        push = updated_input(invoke(BASH_GUARD, {"command": "git push origin feature"}))
        self.assertRegex(push["command"], prefix_pattern)
        heredoc = "cat <<'EOF'\npnpm check | tail -2\nEOF"
        cases = [
            ("git push -u origin x 2>&1 | tail -2", "git push -u origin x 2>&1", True),
            (
                'pnpm check 2>&1 | grep -E "FAIL|error" | head -20; git status',
                "pnpm check 2>&1; git status",
                True,
            ),
            ("npm run check:agents 2>&1 | tail -3; git add -A", "npm run check:agents 2>&1; git add -A", True),
            ("cd web && npm run check:all | awk '{print $1}'", "cd web && npm run check:all", True),
            ("yarn verify | head -5", "yarn verify", True),
            (heredoc, heredoc, False),
            ("pnpm vitest run | tail -20", "pnpm vitest run | tail -20", True),
            ("git push origin feature && echo done | tail -1", "git push origin feature && echo done | tail -1", True),
            ("git log | head -5", "git log | head -5", False),
            ("bun run model-check plan-writes 2>&1 | tail -5", "bun run model-check plan-writes 2>&1 | tail -5", True),
        ]
        stripped = [
            ("(npm run check 2>&1 | tail -25)", "(npm run check 2>&1)"),
            ("npm run check 2>&1 | tail -40; echo EXIT=$?", "npm run check 2>&1; echo EXIT=$?"),
            ("pnpm check 2>&1 | tail -45; echo EXIT $?", "pnpm check 2>&1; echo EXIT $?"),
            ("pnpm check 2>&1 | tail -8 && git commit -m x", "pnpm check 2>&1 && git commit -m x"),
            ('out=$(pnpm check 2>&1 | tail -5); echo "$out"', 'out=$(pnpm check 2>&1); echo "$out"'),
        ]
        for command, expected in stripped:
            with self.subTest(stripped=command):
                result = invoke(BASH_GUARD, {"command": command})
                self.assertEqual((result.returncode, result.stderr), (0, ""))
                self.assertEqual(prefix_pattern.sub("", updated_input(result)["command"]), expected)
        rewritten = [
            (
                "pnpm check 2>&1 | grep -q FAIL && echo failed",
                r"\{ pnpm check > (/tmp/gate-\w+\.log) 2>&1; cat \1 \| grep -q FAIL; \} && echo failed",
            ),
            (
                "pnpm check 2>&1 | tail -2 > /tmp/out.txt; cat /tmp/out.txt",
                r"\{ pnpm check > (/tmp/gate-\w+\.log) 2>&1; cat \1 \| tail -2 > /tmp/out.txt; \}; cat /tmp/out.txt",
            ),
            (
                "pnpm check | grep error | wc -l",
                r"\{ pnpm check > (/tmp/gate-\w+\.log) 2>&1; cat \1 \| grep error \| wc -l; \}",
            ),
            (
                "git push 2>&1 | grep -q rejected; echo $?",
                r"\{ git push > (/tmp/gate-\w+\.log) 2>&1; cat \1 \| grep -q rejected; \}; echo \$\?",
            ),
            (
                "CI=1 pnpm check | grep -q FAIL",
                r"\{ CI=1 pnpm check > (/tmp/gate-\w+\.log) 2>&1; cat \1 \| grep -q FAIL; \}",
            ),
            (
                "pnpm check | grep foo\\|bar",
                r"\{ pnpm check > (/tmp/gate-\w+\.log) 2>&1; cat \1 \| grep foo\\\|bar; \}",
            ),
        ]
        for command, expected in stripped:
            with self.subTest(syntax=command):
                result = invoke(BASH_GUARD, {"command": command})
                self.assertEqual(self.syntax_check(prefix_pattern.sub("", updated_input(result)["command"])), 0)
        for command, pattern in rewritten:
            with self.subTest(rewritten=command):
                result = invoke(BASH_GUARD, {"command": command})
                self.assertEqual((result.returncode, result.stderr), (0, ""))
                rewritten_command = updated_input(result)["command"]
                self.assertRegex(rewritten_command, prefix_pattern)
                self.assertEqual(self.syntax_check(prefix_pattern.sub("", rewritten_command)), 0)
                self.assertRegex(prefix_pattern.sub("", rewritten_command), f"^{pattern}$")
                context = json.loads(result.stdout)["hookSpecificOutput"]["additionalContext"]
                self.assertRegex(context, r"/tmp/gate-\w+\.log")
        for command, expected, takes_slot in cases:
            with self.subTest(command=command):
                result = invoke(BASH_GUARD, {"command": command})
                self.assertEqual((result.returncode, result.stderr), (0, ""))
                updated = updated_input(result)
                rewritten = updated["command"] if updated else command
                self.assertEqual(prefix_pattern.sub("", rewritten), expected)
                self.assertEqual(bool(prefix_pattern.match(rewritten)), takes_slot)

    def test_unquoted_include_globs_are_quoted_for_zsh(self):
        cases = [
            ("grep -rn foo --include=*.ts src", "grep -rn foo --include='*.ts' src"),
            ("grep -r foo --exclude-dir=node_* --exclude=*.map .", "grep -r foo --exclude-dir='node_*' --exclude='*.map' ."),
            ("echo x\ngrep -r foo --include=*.ts .", "echo x\ngrep -r foo --include='*.ts' ."),
        ]
        for command, expected in cases:
            with self.subTest(command=command):
                self.assertEqual(updated_input(invoke(BASH_GUARD, {"command": command}))["command"], expected)
        for command in ["grep -rn foo --include='*.ts' src", "grep -rn foo --include=ts src",
                        "cat > /tmp/x <<'EOF'\ngrep --include=*.ts\nEOF"]:
            with self.subTest(command=command):
                self.assertEqual(invoke(BASH_GUARD, {"command": command}).stdout, "")

    def test_glob_quoting_and_slot_prefix_arrive_in_one_updated_input(self):
        command = "pnpm test && grep -rn foo --include=*.ts src"
        updated = updated_input(invoke(BASH_GUARD, {"command": command}))
        self.assertRegex(updated["command"], r"^python3 \S+heavy-slot\.py \$\$ \d+\npnpm test && grep -rn foo --include='\*\.ts' src$")
        self.assertEqual(updated["timeout"], 180000)

    def test_docker_database_message_tells_the_agent_to_carry_on(self):
        blocked = invoke(BASH_GUARD, {"command": "docker compose up -d postgres"})
        self.assertEqual(blocked.returncode, 2)
        self.assertIn("carry on with the task", blocked.stderr)
        self.assertIn("pglite-replay", blocked.stderr)
        self.assertIn("never in Docker", blocked.stderr)


FAKE_GH = """#!/bin/sh
echo "$@" >> "$GH_CALLS"
if [ "$2" = "checks" ]; then
  case " $* " in
    *" --required "*)
      [ -n "$GH_REQUIRED_ERR" ] && echo "$GH_REQUIRED_ERR" >&2
      if [ -f "$GH_REQUIRED_OUT" ]; then
        cat "$GH_REQUIRED_OUT"
        exit "${GH_REQUIRED_EXIT:-0}"
      fi
      ;;
  esac
  [ -n "$GH_CHECKS_ERR" ] && echo "$GH_CHECKS_ERR" >&2
  [ -f "$GH_CHECKS_OUT" ] && cat "$GH_CHECKS_OUT"
  exit "${GH_CHECKS_EXIT:-0}"
fi
exit 0
"""


class MergeChecksGuardTests(unittest.TestCase):
    def run_merge(self, command, stdout="", exit_code=0, stderr="", required_stdout=None, required_exit=0):
        with tempfile.TemporaryDirectory() as directory:
            root = pathlib.Path(directory)
            bin_dir = root / "bin"
            bin_dir.mkdir()
            gh = bin_dir / "gh"
            gh.write_text(FAKE_GH)
            gh.chmod(gh.stat().st_mode | stat.S_IEXEC)
            calls = root / "calls.txt"
            out = root / "checks.json"
            out.write_text(stdout)
            env = {
                **os.environ,
                "PATH": f"{bin_dir}{os.pathsep}{os.environ['PATH']}",
                "GH_CALLS": str(calls),
                "GH_CHECKS_OUT": str(out),
                "GH_CHECKS_EXIT": str(exit_code),
                "GH_CHECKS_ERR": stderr,
            }
            if required_stdout is not None:
                required = root / "required.json"
                required.write_text(required_stdout)
                env["GH_REQUIRED_OUT"] = str(required)
                env["GH_REQUIRED_EXIT"] = str(required_exit)
            result = subprocess.run(
                [sys.executable, str(BASH_GUARD)],
                input=json.dumps({"tool_input": {"command": command}, "cwd": directory}),
                text=True,
                capture_output=True,
                cwd=directory,
                timeout=10,
                env=env,
            )
            result.gh_calls = calls.read_text() if calls.exists() else ""
            return result

    def assert_blocked(self, result, pr="12"):
        self.assertEqual(result.returncode, 2, result.stderr)
        self.assertIn(f"gh pr checks {pr} --watch --required --fail-fast", result.stderr)
        self.assertIn("then fix any red check", result.stderr)

    def test_merge_allows_when_every_required_check_passed(self):
        result = self.run_merge(
            "gh pr merge 12 --squash",
            stdout='[{"name":"ci","bucket":"pass"}]\n',
        )
        self.assertEqual((result.returncode, result.stderr), (0, ""), result.stderr)
        self.assertIn("pr checks 12 --required", result.gh_calls)
        repo = self.run_merge(
            "gh pr merge -R acme/app 12 --squash",
            stdout='[{"name":"ci","bucket":"pass"}]\n',
        )
        self.assertEqual((repo.returncode, repo.stderr), (0, ""), repo.stderr)
        self.assertIn("pr checks 12 --required", repo.gh_calls)
        self.assertRegex(repo.gh_calls, r"--repo acme/app|-R acme/app")

    def test_merge_blocks_while_required_checks_are_pending(self):
        for bucket, code in (("pending", 8), ("skipping", 0)):
            with self.subTest(bucket=bucket):
                result = self.run_merge(
                    "gh pr merge 12 --squash",
                    stdout=f'[{{"name":"ci","bucket":"{bucket}"}}]\n',
                    exit_code=code,
                )
                self.assert_blocked(result)
                self.assertIn("pr checks 12 --required", result.gh_calls)

    def test_merge_blocks_when_a_required_check_failed(self):
        result = self.run_merge(
            "gh pr merge 12 --squash",
            stdout='[{"name":"ci","bucket":"fail"}]\n',
            exit_code=1,
        )
        self.assert_blocked(result)

    def test_merge_blocks_when_no_required_checks_are_found(self):
        result = self.run_merge("gh pr merge 12 --squash", stdout="[]\n")
        self.assertEqual(result.returncode, 2, result.stderr)
        self.assertIn("no checks", result.stderr.lower())
        self.assertIn("gh pr checks 12 --watch --fail-fast", result.stderr)
        self.assertIn("then fix any red check", result.stderr)

    def test_merge_allows_when_no_required_checks_and_every_ran_check_passed(self):
        result = self.run_merge(
            "gh pr merge 12 --squash",
            stdout='[{"name":"ci","bucket":"pass"}]\n',
            required_stdout="[]\n",
        )
        self.assertEqual((result.returncode, result.stderr), (0, ""), result.stderr)
        required = [line for line in result.gh_calls.splitlines() if "pr checks" in line and "--required" in line]
        optional = [line for line in result.gh_calls.splitlines() if "pr checks" in line and "--required" not in line]
        self.assertGreater(len(required), 0, result.gh_calls)
        self.assertGreater(len(optional), 0, result.gh_calls)

    def test_merge_blocks_when_no_required_checks_and_one_is_pending(self):
        result = self.run_merge(
            "gh pr merge 12 --squash",
            stdout='[{"name":"ci","bucket":"pending"}]\n',
            exit_code=8,
            required_stdout="[]\n",
        )
        self.assertEqual(result.returncode, 2, result.stderr)
        self.assertIn("gh pr checks 12 --watch --fail-fast", result.stderr)
        self.assertIn("then fix any red check", result.stderr)
        self.assertNotIn("no checks found", result.stderr)
        self.assertGreaterEqual(result.gh_calls.count("pr checks"), 2)

    def test_merge_allows_auto_without_reading_checks(self):
        result = self.run_merge(
            "gh pr merge 12 --auto --squash",
            stdout="[]\n",
            exit_code=1,
            stderr="should not run",
        )
        self.assertEqual((result.returncode, result.stderr), (0, ""), result.stderr)
        self.assertNotIn("checks", result.gh_calls)
        flagged = self.run_merge("gh pr merge --auto 12", stdout="[]\n", exit_code=1)
        self.assertEqual((flagged.returncode, flagged.stderr), (0, ""), flagged.stderr)
        self.assertNotIn("checks", flagged.gh_calls)

    def test_merge_blocks_and_names_a_gh_error(self):
        result = self.run_merge(
            "gh pr merge 12 --squash",
            stdout="",
            exit_code=1,
            stderr="HTTP 401: Bad credentials",
        )
        self.assert_blocked(result)
        self.assertIn("HTTP 401: Bad credentials", result.stderr)


class EnvGuardEmbeddedPathTests(unittest.TestCase):
    def test_env_path_inside_a_script_argument_is_blocked(self):
        blocked = [
            """node -e 'console.log(require("fs").readFileSync("apps/web/.env.local","utf8"))'""",
            """python3 -c "print(open('.env').read())\"""",
            "awk -F= '{print $1}' apps/web/.env.local",
            """node -e "require('dotenv').config({path:'./.env.production'})\"""",
        ]
        allowed = [
            """node -e 'console.log(process.env.NODE_ENV)'""",
            """node -e "require('dotenv/config')\"""",
            "cat .envrc",
            """node -e 'read("apps/web/.env.example")'""",
            "pnpm secrets pull",
        ]
        for command in blocked:
            with self.subTest(blocked=command):
                self.assertEqual(invoke(ENV_HOOK, {"command": command}).returncode, 2, command)
        for command in allowed:
            with self.subTest(allowed=command):
                result = invoke(ENV_HOOK, {"command": command})
                self.assertEqual((result.returncode, result.stderr), (0, ""), command)


class EnvGuardExistenceCheckTests(unittest.TestCase):
    def test_env_file_may_be_named_only_by_existence_checks(self):
        blocked = ["ls .env.local && cat .env.local", "cat .env.local", "ls .env; cat .env", "ls .env.local | xargs cat", "test -f .env && source .env"]
        allowed = ["ls -la .env.local", "test -f .env.local && echo yes", "[ -f .env ] || echo none",
                   "stat .env.production", "ls .env.local | wc -l"]
        for command in blocked:
            with self.subTest(blocked=command):
                result = invoke(ENV_HOOK, {"command": command})
                self.assertEqual(result.returncode, 2, command)
        for command in allowed:
            with self.subTest(allowed=command):
                result = invoke(ENV_HOOK, {"command": command})
                self.assertEqual((result.returncode, result.stderr), (0, ""))


if __name__ == "__main__":
    unittest.main()

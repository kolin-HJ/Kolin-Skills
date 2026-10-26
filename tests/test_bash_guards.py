import json
import pathlib
import re
import subprocess
import sys
import tempfile
import unittest


REPO = pathlib.Path(__file__).resolve().parent.parent
BASH_GUARD = REPO / "hooks/bash-guard.py"
ENV_HOOK = REPO / "hooks/block-env-reads.py"
NESTED_POLL = "for i in $(seq 1 16); do p=$(for n in 874 857; do gh pr view $n; done); echo $p; sleep 30; done"


def invoke(hook, tool_input):
    with tempfile.TemporaryDirectory() as directory:
        return subprocess.run(
            [sys.executable, str(hook)],
            input=json.dumps({"tool_input": tool_input}),
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

    def test_shell_file_edits_are_denied_unless_the_target_is_scratch(self):
        blocked = [
            "sed -i 's/a/b/' src/app.ts",
            "sed -n -i.bak 's/a/b/;s/c/d/' src/app.ts",
            "perl -pi -e 's/a/b/' src/app.ts",
            "cat > notes.md",
            "cat >> notes.md <<'EOF'\nhello\nEOF",
            "echo hi | tee out.txt",
            "python3 - <<'EOF'\nimport pathlib\npathlib.Path('src/a.ts').write_text('x')\nEOF",
            "python3 - <<'EOF'\nopen(target, 'w').write('x')\nEOF",
            "node -e \"require('fs').writeFileSync('src/a.js', 'x')\"",
            "sed -i 's/a/b/' /tmp/../etc/hosts",
            "cat <<EOF > notes.md\nhi\nEOF",
            "echo hi > src/x",
            "printf 'x' > file",
            "python3 - <<'EOF'\nfrom pathlib import Path\nPath(target).write_text('x')\nEOF",
            "node -e \"require('fs').writeFileSync(process.argv[1], 'x')\"",
        ]
        allowed = [
            "sed -n 's/a/b/p' src/app.ts",
            "sed -i 's/a/b/' /tmp/work.txt",
            "perl -pi -e 's/a/b/' $TMPDIR/work.txt",
            "cat > .pstack/status.md <<'EOF'\nok\nEOF",
            "echo hi | tee -a /private/tmp/out.txt",
            "python3 - <<'EOF'\nimport pathlib\npathlib.Path('/tmp/a.txt').write_text('x')\nEOF",
            "python3 - <<'EOF'\nprint(open('src/a.ts').read())\nEOF",
            "echo 'run sed -i on it'",
            "cat README.md",
            "python3 - <<'EOF'\nimport sys\nsys.stdout.write('x')\nEOF",
            "node -e \"process.stdout.write('x')\"",
            "python3 - <<'EOF'\nopen('/tmp/out', 'w').write(open('src/a.ts').read())\nEOF",
            "perl -MList::Util=sum -e 'print sum(1,2)' src/a.ts",
            "echo hi > /dev/null 2>&1",
            "echo hi >&2",
            "echo x > /tmp/a.txt",
            "printf x > .pstack/a.txt",
            "cat <<EOF > /tmp/x\nhi\nEOF",
        ]
        for command in blocked:
            with self.subTest(blocked=command):
                result = invoke(BASH_GUARD, {"command": command})
                self.assertEqual(result.returncode, 2, result.stdout)
                self.assertIn("Edit or Write tool", result.stderr)
        for command in allowed:
            with self.subTest(allowed=command):
                result = invoke(BASH_GUARD, {"command": command})
                self.assertEqual((result.returncode, result.stderr), (0, ""))

    def test_shell_append_is_allowed_outside_any_git_work_tree_and_denied_inside(self):
        with tempfile.TemporaryDirectory() as plain, tempfile.TemporaryDirectory() as repo:
            subprocess.run(["git", "init", "-q", repo], check=True)
            pathlib.Path(plain, "linked.md").symlink_to(pathlib.Path(repo, "tracked.md"))
            allowed = [
                f"echo '- [x](x.md)' >> {plain}/MEMORY.md",
                f"echo x >> {plain}/new/dir/MEMORY.md",
            ]
            blocked = [
                f"echo '- [x](x.md)' >> {repo}/MEMORY.md",
                f"cd {repo} && printf '- x' >> MEMORY.md",
                f"echo x >> {repo}/new/dir/MEMORY.md",
                f"echo x >> {plain}/linked.md",
                f"cd {pathlib.Path(repo).parent} && echo x >> {pathlib.Path(repo).name}/a.md",
                f"cd {pathlib.Path(repo).parent} && sed -i 's/a/b/' {pathlib.Path(repo).name}/a.md",
            ]
            for command in allowed:
                with self.subTest(allowed=command):
                    result = invoke(BASH_GUARD, {"command": command})
                    self.assertEqual((result.returncode, result.stderr), (0, ""))
            for command in blocked:
                with self.subTest(blocked=command):
                    result = invoke(BASH_GUARD, {"command": command})
                    self.assertEqual(result.returncode, 2, result.stdout)

    def test_scratch_context_follows_cd_and_scratch_variables(self):
        blocked = [
            f"cd /tmp && cd {REPO} && cat > a.ts <<'EOF'\nx\nEOF",
            "X=$(pwd); cat > $X/a.ts <<'EOF'\nx\nEOF",
            "cd src && python3 - <<'EOF'\nopen(\"a.ts\",\"w\")\nEOF",
            "cat > ../.scratch/x <<'EOF'\nx\nEOF",
            "cd /tmp/x && cd - && cat > a.ts <<'EOF'\nx\nEOF",
            "cd /tmp/x && cd -P /Users/x/repo && cat > a.ts <<'EOF'\nx\nEOF",
            "cd /tmp/x && cd -- /Users/x/repo && cat > a.ts <<'EOF'\nx\nEOF",
            "cd /tmp/x && cat > `echo /Users/x/repo/a.ts` <<'EOF'\nx\nEOF",
            "cd /tmp/x && pushd /Users/x/repo && cat > a.ts <<'EOF'\nx\nEOF",
            "cd /tmp/x && (cd /Users/x/repo && cat > a.ts <<'EOF'\nx\nEOF\n)",
            "cd /tmp/x && { cd /Users/x/repo; cat > a.ts <<'EOF'\nx\nEOF\n}",
            "cd /tmp/x && FOO=1 cd /Users/x/repo && cat > a.ts <<'EOF'\nx\nEOF",
            "cd /tmp/x && builtin cd /Users/x/repo && cat > a.ts <<'EOF'\nx\nEOF",
            "B=$(mktemp -d); export B=/Users/x/repo; cat > $B/a.ts <<'EOF'\nx\nEOF",
            "B=$(mktemp -d); for B in /Users/x/repo; do cat > $B/a.ts <<'EOF'\nx\nEOF\ndone",
            "B=$(mktemp -d); read B <<< /Users/x/repo; cat > $B/a.ts <<'EOF'\nx\nEOF",
            "if cat > src/a.ts <<'EOF'\nx\nEOF\nthen true; fi",
            "if false; then true; elif cat > src/a.ts <<'EOF'\nx\nEOF\nthen true; fi",
            "while cat > src/a.ts <<'EOF'\nx\nEOF\ndo break; done",
            "until cat > src/a.ts <<'EOF'\nx\nEOF\ndo break; done",
            "time cat > src/a.ts <<'EOF'\nx\nEOF",
            "cd /tmp/nope; cat > src/a.ts <<'EOF'\nx\nEOF",
            "cd /tmp/x & cat > a.ts <<'EOF'\nx\nEOF",
            "cd /tmp/x && python3 - <<'EOF'\nimport os\nos.chdir('/Users/x/repo')\nopen('a.ts','w')\nEOF",
        ]
        allowed = [
            "cd /tmp/sp && cat > hook_orig.sql <<'EOF'\nselect 1;\nEOF",
            "B=$(mktemp -d)/body.md; cat > $B <<'EOF'\nbody\nEOF",
            "D=$(mktemp -d /tmp/f8rev.XXXX) && cat > \"$D/notes.md\" <<'EOF'\nx\nEOF",
            "T=$(mktemp -d); cd $T && printf x > out.txt",
            "cd /Users/x/repo/.scratch/supabase-audit && cat > pr-realtime.md <<'EOF'\nx\nEOF",
            "cat > .scratch/probe.sh <<'EOF'\nx\nEOF",
            "cd /tmp/ksaudit && python3 - <<'EOF'\nopen(\"mine.py\",\"w\").write(\"x\")\nEOF",
        ]
        for command in blocked:
            with self.subTest(blocked=command):
                result = invoke(BASH_GUARD, {"command": command})
                self.assertEqual(result.returncode, 2, result.stdout)
                self.assertIn("Edit or Write tool", result.stderr)
        for command in allowed:
            with self.subTest(allowed=command):
                result = invoke(BASH_GUARD, {"command": command})
                self.assertEqual((result.returncode, result.stderr), (0, ""))

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
        ]
        unsafe = [
            "pnpm check | grep -q FAIL && echo failed",
            'out=$(pnpm check 2>&1 | tail -5); echo "$out"',
            "(pnpm check | tail -5) && echo ok",
            "pnpm check 2>&1 | tail -2 > /tmp/out.txt; cat /tmp/out.txt",
            "pnpm check | grep error | wc -l",
            "pnpm check | tail -5 \\\n&& echo ok",
            "git push 2>&1 | grep -q rejected; echo $?",
            "pnpm check 2>&1 | grep -Ec 'FAIL|error'",
            "git push 2>&1 | tail -2; echo $?",
        ]
        for command in unsafe:
            with self.subTest(unsafe=command):
                result = invoke(BASH_GUARD, {"command": command})
                self.assertEqual(result.returncode, 2, result.stdout)
                self.assertIn("do not filter gate output", result.stderr)
        for command, expected, takes_slot in cases:
            with self.subTest(command=command):
                result = invoke(BASH_GUARD, {"command": command})
                self.assertEqual((result.returncode, result.stderr), (0, ""))
                updated = updated_input(result)
                rewritten = updated["command"] if updated else command
                self.assertEqual(prefix_pattern.sub("", rewritten), expected)
                self.assertEqual(bool(prefix_pattern.match(rewritten)), takes_slot)

    def test_poll_loop_nested_in_a_command_substitution_is_blocked(self):
        blocked = invoke(BASH_GUARD, {"command": NESTED_POLL})
        self.assertEqual(blocked.returncode, 2)
        self.assertIn("run_in_background: true", blocked.stderr)
        self.assertEqual(invoke(BASH_GUARD, {"command": NESTED_POLL, "run_in_background": True}).returncode, 0)
        self.assertEqual(invoke(BASH_GUARD, {"command": "p=$(for n in 1 2; do gh pr view $n; done); echo $p"}).returncode, 0)

    def test_long_foreground_curl_retry_is_blocked(self):
        cases = [
            ({"command": "curl --retry 60 --retry-connrefused localhost:3000"}, 2),
            ({"command": "curl --retry=30 localhost:3000"}, 2),
            ({"command": "curl --retry 60 localhost:3000", "run_in_background": True}, 0),
            ({"command": "curl --retry 3 localhost:3000"}, 0),
            ({"command": "curl --retry-delay 30 localhost:3000"}, 0),
        ]
        for tool_input, code in cases:
            with self.subTest(tool_input=tool_input):
                result = invoke(BASH_GUARD, tool_input)
                self.assertEqual(result.returncode, code, result.stderr)
        self.assertIn("Monitor", invoke(BASH_GUARD, cases[0][0]).stderr)

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
        self.assertIn("do not ask Kolin to exempt this hook", blocked.stderr)


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

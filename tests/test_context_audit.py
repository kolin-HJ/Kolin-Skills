import json
import os
import pathlib
import shutil
import subprocess
import sys
import tempfile
import time
import unittest

CLI = pathlib.Path(__file__).resolve().parent.parent / "bin/context-audit"


def transcript(path, *records):
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text("".join(json.dumps(record) + "\n" for record in records))


def tool_use(name, arguments):
    return {"type": "assistant", "message": {"content": [{"type": "tool_use", "name": name, "input": arguments}]}}


class ContextAuditTests(unittest.TestCase):
    def setUp(self):
        self.home = pathlib.Path(tempfile.mkdtemp())
        self.projects = self.home / ".claude/projects"

    def tearDown(self):
        shutil.rmtree(self.home)

    def run_cli(self, *args, config=".claude"):
        env = {**os.environ, "HOME": str(self.home), "CLAUDE_CONFIG_DIR": str(self.home / config)}
        return subprocess.run([sys.executable, str(CLI), *args], env=env, text=True, capture_output=True, timeout=60)

    def session_with_listing(self, idle_description):
        listing = ("The following skills are available for use with the Skill tool:\n\n"
                   f"- used-skill: {'u' * 300}\n- idle-skill: {idle_description}\n- read-skill: {'r' * 300}\n")
        tools = [{"name": "Skill", "description": ""}, {"name": "Bash", "description": "b" * 400}, {"name": "Workflow", "description": "w" * 400}]
        system = [{"type": "text", "text": "s" * 100}]
        whole = len(system[0]["text"]) + sum(len(json.dumps(tool)) for tool in tools) + len(listing)
        transcript(self.projects / "p1/s1.jsonl",
                   {"type": "api-request-shape", "shape": {"system": system, "tools": tools}},
                   {"type": "api-request-blob", "message": {"content": [{"type": "text", "text": listing}]}},
                   {"type": "assistant", "message": {"usage": {"input_tokens": whole}, "content": []}})
        transcript(self.projects / "p2/s2.jsonl",
                   tool_use("Skill", {"skill": "used-skill"}),
                   tool_use("Read", {"file_path": "/x/skills/read-skill/SKILL.md"}),
                   tool_use("Bash", {"command": "ls"}))
        bot = {"type": "api-request-shape", "shape": {"system": [{"type": "text", "text": "x"}], "tools": [{"name": "Read", "description": "r" * 900}]}}
        transcript(self.projects / "bot/s3.jsonl", bot, {"type": "assistant", "message": {"usage": {"input_tokens": 300}, "content": []}})
        os.utime(self.projects / "bot/s3.jsonl", (time.time() + 60, time.time() + 60))

    def test_lists_only_listed_items_that_went_unused(self):
        self.session_with_listing("i" * 700)
        result = self.run_cli()
        self.assertEqual(result.returncode, 0, result.stderr)
        listed = {line.split()[1] for line in result.stdout.splitlines() if line.startswith("  ")}
        self.assertEqual(listed, {"idle-skill", "Workflow"})

    def test_notice_speaks_only_when_waste_reaches_the_threshold(self):
        self.session_with_listing("i" * 700)
        self.run_cli("--refresh")
        self.assertIn("2 unused items", json.loads(self.run_cli("--notice").stdout)["systemMessage"])
        self.session_with_listing("i" * 400)
        (self.projects / "p1/s1.jsonl").write_text((self.projects / "p1/s1.jsonl").read_text().replace('"Workflow"', '"Bash"'))
        self.run_cli("--refresh")
        self.assertEqual(self.run_cli("--notice").stdout, "")

    def test_a_failed_refresh_is_reported_and_not_retried_the_same_day(self):
        state = self.home / ".kolin-skills"
        self.assertEqual(self.run_cli("--notice").stdout, "")
        for _ in range(50):
            if (state / "context-audit.log").is_file() and (state / "context-audit.log").stat().st_size:
                break
            time.sleep(0.1)
        started = (state / "context-audit.started").stat().st_mtime
        message = json.loads(self.run_cli("--notice").stdout)["systemMessage"]
        self.assertIn("refresh failed", message)
        self.assertEqual((state / "context-audit.started").stat().st_mtime, started)

    def test_deferred_names_count_only_inside_the_harness_list(self):
        self.session_with_listing("i" * 10)
        deferred = "The following deferred tools are now available via ToolSearch:\n" + "".join(f"mcp__idle__tool_{n}\n" for n in range(40)) + "\n"
        stray = "".join(f"mcp__stray__tool_{n}\n" for n in range(40))
        path = self.projects / "p1/s1.jsonl"
        lines = path.read_text().splitlines(keepends=True)
        extra = json.dumps({"type": "api-request-blob", "message": {"content": [{"type": "text", "text": deferred + stray}]}}) + "\n"
        path.write_text(lines[0] + lines[1] + lines[2] + extra)
        listed = {line.split()[1] for line in self.run_cli().stdout.splitlines() if line.startswith("  ")}
        self.assertEqual(listed, {"idle", "Workflow"})

    def test_sessions_report_counts_each_message_once_and_names_hook_blocks_and_failing_tools(self):
        def assistant(message_id, model, usage, *calls):
            content = [{"type": "tool_use", "id": call_id, "name": name, "input": {}} for call_id, name in calls]
            return {"type": "assistant", "timestamp": "2026-10-20T10:00:00Z", "message": {"id": message_id, "model": model, "usage": usage, "content": content}}

        def result(call_id, text, failed=True):
            return {"type": "user", "message": {"content": [{"type": "tool_result", "tool_use_id": call_id, "is_error": failed, "content": text}]}}

        first = assistant("m1", "claude-opus-5-5", {"input_tokens": 10, "cache_creation_input_tokens": 20, "cache_read_input_tokens": 70, "output_tokens": 5},
                          ("t1", "Bash"), ("t2", "mcp__x__query"), ("t3", "mcp__x__query"))
        second = assistant("m2", "claude-opus-5-5", {"input_tokens": 1, "cache_read_input_tokens": 199, "output_tokens": 10}, ("t4", "mcp__x__query"),
                        ("f1", "mcp__x__flaky"), ("f2", "mcp__x__flaky"), ("f3", "mcp__x__flaky"))
        block = "PreToolUse:Bash hook error: [python3 '/r/hooks/heavy-jobs.py']: Blocked: edit files with the Edit or Write tool, so the lint hook sees each change."
        pr = {"type": "pr-link", "prUrl": "https://github.com/o/r/pull/1"}
        self.projects = self.home / ".claude_personal/projects"
        transcript(self.home / ".claude/projects/other/s9.jsonl", first)
        transcript(self.projects / "proj/s1.jsonl", first, first, second, result("t1", block), result("t2", "boom"),
                   result("t3", [{"type": "text", "text": "boom"}]), result("t4", "boom"),
                   result("f1", "ok", failed=False), result("f2", "boom"), result("f3", "boom"), pr, pr,
                   {"type": "system", "subtype": "compact_boundary"})
        agent = self.projects / "proj/s1/subagents/agent-a1"
        transcript(agent.with_suffix(".jsonl"), assistant("s1", "claude-sonnet-5-5", {"input_tokens": 1000, "output_tokens": 50}, ("u1", "Read")),
                   result("u1", "ok", failed=False))
        agent.with_suffix(".meta.json").write_text(json.dumps({"agentType": "reviewer"}))
        rows = {line.split()[0]: line.split() for line in self.run_cli("--sessions", config=".claude_personal").stdout.splitlines() if line.strip()}
        self.assertEqual(rows["Sessions"][5:10], ["1", "main", "sessions,", "1", "subagents,"])
        self.assertEqual(rows["main"][1:], ["claude-opus-5-5", "1", "315", "7", "0", "200", "200"])
        self.assertNotIn("mcp__x__flaky:", rows)
        self.assertEqual(rows["reviewer"][1:], ["claude-sonnet-5-5", "1", "1,050", "1", "0", "1,000", "1,000"])
        self.assertEqual(rows["proj"][1:], ["2026-10-20", "1,365", "1", "1"])
        self.assertEqual(rows["1"][1:4], ["main", "heavy-jobs.py:", "Blocked:"])
        self.assertEqual(rows["mcp__x__query:"], ["mcp__x__query:", "3"])
        self.assertEqual(rows["Unique"][-1], "1")


if __name__ == "__main__":
    unittest.main()

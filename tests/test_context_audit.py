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

    def run_cli(self, *args, config=".claude", **extra):
        env = {**os.environ, "HOME": str(self.home), "CLAUDE_CONFIG_DIR": str(self.home / config), **extra}
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

    def test_sessions_report_reads_every_config_dir(self):
        message = {"type": "assistant", "message": {"id": "m", "model": "claude-opus-5-5", "usage": {"input_tokens": 1}, "content": []}}
        transcript(self.home / ".claude/projects/p/a.jsonl", message)
        transcript(self.home / ".claude_personal/projects/p/b.jsonl", message)
        self.assertIn("2 main sessions", self.run_cli("--sessions", config=".claude_personal").stdout)

    def spawn_fixture(self, requested):
        def assistant(model, *content):
            return {"type": "assistant", "timestamp": "2026-10-20T10:00:00Z", "message": {"id": model + str(len(content)), "model": model, "usage": {"input_tokens": 1}, "content": list(content)}}

        spawns = [{"type": "tool_use", "id": f"toolu_{n}", "name": "Agent", "input": {"model": model, "subagent_type": "general-purpose"}} for n, model in enumerate(requested)]
        transcript(self.projects / "p/s.jsonl", assistant("claude-opus-5-5", *spawns))
        for n, _ in enumerate(requested):
            agent = self.projects / f"p/s/subagents/agent-{n}"
            transcript(agent.with_suffix(".jsonl"), assistant("claude-sonnet-5-5"))
            agent.with_suffix(".meta.json").write_text(json.dumps({"agentType": "general-purpose", "toolUseId": f"toolu_{n}"}))
        output = self.run_cli("--sessions").stdout
        return output.partition("Seat mismatches: agent type, requested, ran, count\n")[2].split("Hook blocks")[0].strip().splitlines()

    def test_seat_mismatch_lists_requested_family_against_the_family_that_ran(self):
        self.assertEqual([row.split() for row in self.spawn_fixture(["opus", "sonnet", None])], [["general-purpose", "opus", "sonnet", "1"]])

    def test_seat_that_ran_as_requested_is_not_a_mismatch(self):
        self.assertEqual(self.spawn_fixture(["claude-sonnet-5-5"]), [])

    def gh_fixture(self):
        def check(name, status="COMPLETED", conclusion="SUCCESS", done="2026-10-20T09:00:00Z", started="2026-10-20T08:00:00Z"):
            return {"name": name, "status": status, "conclusion": conclusion, "startedAt": started, "completedAt": done}

        def pr(number, title, head, base, merged, checks, body=""):
            return {"number": number, "title": title, "body": body, "createdAt": "2026-10-20T07:00:00Z", "headRefName": head, "baseRefName": base, "mergedAt": merged, "state": "MERGED", "statusCheckRollup": checks}

        fixtures = self.home / "gh"
        fixtures.mkdir()
        files = {
            "pr-10": pr(10, "Release: reland of foo", "release/x", "main", "2026-10-20T10:00:00Z", [check("build")], "Includes #11 #12 #13 #14 #15 #16 #17 #18 #19 #99 and #10"),
            "pr-11": pr(11, "Fix a", "feat/a", "release/x", "2026-10-20T10:00:00Z", [check("build", conclusion="FAILURE")]),
            "pr-12": pr(12, "Revert b", "feat/b", "feat/c", "2026-10-20T11:00:00Z", [check("build")]),
            "pr-13": pr(13, "Fix d", "feat/d", "release/x", "2026-10-20T10:00:00Z", [check("test", status="IN_PROGRESS", conclusion="", done="0001-01-01T00:00:00Z")]),
            "pr-14": pr(14, "Fix e", "feat/e", "staging", "2026-10-20T11:00:00Z", [check("build")]),
            "pr-15": pr(15, "Fix f", "feat/f", "trunk", "2026-10-20T11:00:00Z", [check("build")]),
            "pr-16": pr(16, "Fix g", "feat/g", "release/x", "2026-10-20T10:00:00Z", [check("build", conclusion="FAILURE", started="2026-10-20T12:00:00Z")]),
            "pr-17": pr(17, "Fix h", "feat/h", "release/x", "2026-10-20T10:00:00Z", [{"context": "ci/x", "state": "ERROR", "createdAt": "2026-10-20T08:00:00Z"}]),
            "pr-18": pr(18, "Fix i", "feat/i", "release/x", "2026-10-20T10:00:00Z", [check("lint", conclusion="TIMED_OUT")]),
            "pr-19": pr(19, "Fix j", "feat/j", "feat/old", "2026-10-20T10:00:00Z", [check("build")]),
            "head-feat_old": [{"mergedAt": "2026-10-20T06:00:00Z"}],
            "repo": {"defaultBranchRef": {"name": "trunk"}},
            "head-main": [], "head-release_x": [], "head-feat_c": [{"mergedAt": "2026-10-20T10:30:00Z"}],
            "head-staging": [{"mergedAt": "2026-10-20T10:30:00Z"}], "head-trunk": [{"mergedAt": "2026-10-20T10:30:00Z"}],
        }
        for name, data in files.items():
            (fixtures / f"{name}.json").write_text(json.dumps(data))
        gh = self.home / "bin/gh"
        gh.parent.mkdir()
        gh.write_text('''#!/bin/sh
if [ "$1" = repo ]; then exec cat "$GH_FIXTURES/repo.json"; fi
if [ -n "$GH_AUTH_FAIL" ]; then echo "gh: To use GitHub CLI, run: gh auth login" >&2; exit 4; fi
if [ "$2" = view ]; then [ -f "$GH_FIXTURES/pr-$3.json" ] || { echo "Could not resolve to a PullRequest with the number of $3" >&2; exit 1; }; exec cat "$GH_FIXTURES/pr-$3.json"; fi
while [ $# -gt 0 ]; do [ "$1" = --head ] && base=$2; shift; done
exec cat "$GH_FIXTURES/head-$(echo "$base" | tr / _).json"
''')
        gh.chmod(0o755)
        return {"PATH": f"{gh.parent}:{os.environ['PATH']}", "GH_FIXTURES": str(fixtures)}

    def test_gh_failure_other_than_a_missing_pr_exits(self):
        result = self.run_cli("--pr", "o/r#10", GH_AUTH_FAIL="1", **self.gh_fixture())
        self.assertNotEqual(result.returncode, 0)
        self.assertIn("gh auth login", result.stderr)

    def test_pr_report_selects_sessions_and_flags_merges(self):
        def mention(text):
            return {"type": "assistant", "timestamp": "2026-10-20T10:00:00Z", "message": {"id": text, "model": "claude-opus-5-5", "usage": {"input_tokens": 5}, "content": [{"type": "text", "text": text}, {"type": "tool_use", "id": "t" + text, "name": "Bash", "input": {"command": "ls"}}]}}

        transcript(self.projects / "p/sess1111-x.jsonl", mention("see https://github.com/o/r/pull/11"))
        transcript(self.projects / "p/sess2222-x.jsonl", mention("branch feat/b"))
        transcript(self.projects / "p/sess3333-x.jsonl", mention("unrelated"))
        transcript(self.projects / "p/sess4444-x.jsonl", mention("https://github.com/o/r/pull/110 and feat/bar"))
        notool = mention("https://github.com/o/r/pull/11")
        notool["message"]["content"] = notool["message"]["content"][:1]
        transcript(self.projects / "p/sess5555-x.jsonl", notool)
        own = mention("https://github.com/o/r/pull/11")
        own["message"]["content"][1]["input"] = {"command": "bin/context-audit --pr o/r#10"}
        transcript(self.projects / "p/sess6666-x.jsonl", own)
        transcript(self.projects / "p/sess1111-x/subagents/agent-a.jsonl", mention("helper"))
        transcript(self.projects / "p/sess3333-x/subagents/agent-a.jsonl", mention("stray"))
        output = self.run_cli("--pr", "o/r#10", **self.gh_fixture()).stdout
        flags = [line for line in output.splitlines() if line.startswith("    FLAG")]
        self.assertEqual(flags, [
            "    FLAG #10 title says reland or revert",
            "    FLAG #11 merged while a check failed or had not finished: build",
            "    FLAG #12 merged into feat/c, which another PR had already merged",
            "    FLAG #12 title says reland or revert",
            "    FLAG #13 merged while a check failed or had not finished: test",
            "    FLAG #17 merged while a check failed or had not finished: ci/x",
            "    FLAG #18 merged while a check failed or had not finished: lint",
        ])
        self.assertIn("  #99 is not a pull request", output)
        found = output.split("Sessions found: session, date, tokens, subagents, compactions\n")[1].split("\n\n")[0].splitlines()
        self.assertEqual([row.split() for row in found], [["sess1111", "2026-10-20", "10", "1", "0"], ["sess2222", "2026-10-20", "5", "0", "0"]])


if __name__ == "__main__":
    unittest.main()

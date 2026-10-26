import json
import pathlib
import subprocess
import sys
import tempfile
import unittest


REPO = pathlib.Path(__file__).resolve().parent.parent
CONTEXT_BUDGET = REPO / "hooks/context-budget.py"
MCP_ACCESS = REPO / "hooks/mcp-access.py"


def run(hook, payload, env=None):
    return subprocess.run(
        [sys.executable, str(hook)],
        input=json.dumps(payload),
        text=True,
        capture_output=True,
        env=env,
        timeout=10,
    )


def assistant_line(input_tokens, created, read):
    usage = {"input_tokens": input_tokens, "cache_creation_input_tokens": created, "cache_read_input_tokens": read}
    return json.dumps({"type": "assistant", "message": {"usage": usage}})


class ContextBudgetTests(unittest.TestCase):
    def payload_for(self, directory, tokens, **extra):
        root = pathlib.Path(directory)
        (root / "s" / "subagents").mkdir(parents=True)
        lines = ["x" * 400_000, assistant_line(1, 1, 1)]
        if tokens is not None:
            lines.append(assistant_line(tokens - 3000, 1000, 2000))
        lines.append(json.dumps({"type": "user"}))
        (root / "s" / "subagents" / "agent-a1.jsonl").write_text("\n".join(lines) + "\n")
        return {"agent_id": "a1", "transcript_path": str(root / "s.jsonl"), **extra}

    def test_subagent_context_warns_then_stops(self):
        cases = [(150_000, 0, ""), (200_000, 0, "Finish the step"), (259_999, 0, "Finish the step"), (260_000, 2, "")]
        for tokens, code, note in cases:
            with self.subTest(tokens=tokens), tempfile.TemporaryDirectory() as directory:
                result = run(CONTEXT_BUDGET, self.payload_for(directory, tokens))
                self.assertEqual(result.returncode, code)
                if code == 2:
                    self.assertIn("Call no more tools", result.stderr)
                    self.assertEqual(result.stdout, "")
                elif note:
                    context = json.loads(result.stdout)["hookSpecificOutput"]["additionalContext"]
                    self.assertIn(note, context)
                else:
                    self.assertEqual((result.stdout, result.stderr), ("", ""))

    def test_main_thread_and_missing_transcripts_pass_silently(self):
        with tempfile.TemporaryDirectory() as directory:
            payload = self.payload_for(directory, 300_000)
            main = run(CONTEXT_BUDGET, {k: v for k, v in payload.items() if k != "agent_id"})
            self.assertEqual((main.returncode, main.stdout), (0, ""))
            missing = run(CONTEXT_BUDGET, {**payload, "agent_id": "gone"})
            self.assertEqual((missing.returncode, missing.stdout), (0, ""))

    def test_transcript_path_that_is_the_agent_file_is_used_directly(self):
        with tempfile.TemporaryDirectory() as directory:
            payload = self.payload_for(directory, 270_000)
            direct = str(pathlib.Path(directory) / "s" / "subagents" / "agent-a1.jsonl")
            self.assertEqual(run(CONTEXT_BUDGET, {**payload, "transcript_path": direct}).returncode, 2)


class McpAccessTests(unittest.TestCase):
    def test_access_errors_get_a_note_and_other_errors_get_nothing(self):
        env = {"CLAUDE_CONFIG_DIR": "/accounts/work", "PATH": "/usr/bin"}
        cases = [
            ("MCP error -32600: You do not have permission to perform this action", True),
            ("401 Unauthorized", True),
            ("HTTP 403", True),
            ("relation \"x\" does not exist", False),
            ("timeout after 30s", False),
        ]
        for error, flagged in cases:
            with self.subTest(error=error):
                payload = {"tool_name": "mcp__claude_ai_Supabase__execute_sql", "tool_input": {}, "error": error}
                result = run(MCP_ACCESS, payload, env)
                self.assertEqual((result.returncode, result.stderr), (0, ""))
                if not flagged:
                    self.assertEqual(result.stdout, "")
                    continue
                output = json.loads(result.stdout)["hookSpecificOutput"]
                self.assertEqual(output["hookEventName"], "PostToolUseFailure")
                self.assertIn("claude_ai_Supabase connector in this Claude account (/accounts/work)", output["additionalContext"])
                self.assertIn("mcp__claude_ai_Supabase__*", output["additionalContext"])


if __name__ == "__main__":
    unittest.main()

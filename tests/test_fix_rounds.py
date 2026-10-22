import json
import os
import pathlib
import subprocess
import sys
import tempfile
import unittest


HOOK = pathlib.Path(__file__).resolve().parent.parent / "hooks/fix-rounds.py"
DENIED = "Two fix rounds went to builder-1."


class FixRoundsTests(unittest.TestCase):
    def send(self, home, to, session="s1", agent_id=None, cwd=None):
        payload = {"session_id": session, "tool_name": "SendMessage", "tool_input": {"to": to}, "agent_id": agent_id}
        if cwd:
            payload["cwd"] = str(cwd)
        return subprocess.run(
            [sys.executable, str(HOOK)],
            input=json.dumps(payload),
            text=True,
            capture_output=True,
            env={**os.environ, "HOME": str(home)},
            timeout=10,
        )

    def test_third_send_to_the_same_recipient_is_denied(self):
        with tempfile.TemporaryDirectory() as home:
            codes = [self.send(home, "builder-1").returncode for _ in range(2)]
            third = self.send(home, "builder-1")
            fourth = self.send(home, "builder-1")
            self.assertEqual(codes, [0, 0])
            self.assertEqual(third.returncode, 2, third.stderr)
            self.assertIn(DENIED, third.stderr)
            self.assertEqual(fourth.returncode, 2, fourth.stderr)

    def test_other_recipients_and_sessions_count_separately(self):
        with tempfile.TemporaryDirectory() as home:
            for _ in range(2):
                self.send(home, "builder-1")
            self.assertEqual(self.send(home, "builder-2").returncode, 0)
            self.assertEqual(self.send(home, "builder-1", session="s2").returncode, 0)

    def test_subagent_messages_never_count(self):
        with tempfile.TemporaryDirectory() as home:
            codes = [self.send(home, "builder-1", agent_id="a1").returncode for _ in range(4)]
            self.assertEqual(codes, [0, 0, 0, 0])
            self.assertEqual(self.send(home, "builder-1").returncode, 0)


    def test_status_line_lifts_the_cap_for_that_recipient_only(self):
        with tempfile.TemporaryDirectory() as home, tempfile.TemporaryDirectory() as work:
            subprocess.run(["git", "init", "-q", work], check=True)
            status = pathlib.Path(work, ".pstack/status.md")
            status.parent.mkdir()
            status.write_text("Value: feature\nfix-rounds: builder-1 answering its question\n")
            codes = [self.send(home, "builder-1", cwd=work).returncode for _ in range(4)]
            other = [self.send(home, "builder-2", cwd=work).returncode for _ in range(3)]
            self.assertEqual(codes, [0, 0, 0, 0])
            self.assertEqual(other, [0, 0, 2])

    def test_corrupt_state_counts_from_zero(self):
        with tempfile.TemporaryDirectory() as home:
            state = pathlib.Path(home, ".kolin-skills/state/fix-rounds-s1.json")
            state.parent.mkdir(parents=True)
            state.write_text("{not json")
            self.assertEqual(self.send(home, "builder-1").returncode, 0)
            self.assertEqual(json.loads(state.read_text()), {"builder-1": 1})
            self.assertEqual([p.name for p in state.parent.iterdir()], [state.name])


if __name__ == "__main__":
    unittest.main()

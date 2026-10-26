import json
import pathlib
import re
import subprocess
import tempfile
import unittest


SCRIPT = pathlib.Path(__file__).resolve().parent.parent / "claude/statusline.sh"
BASE = "session -- · week -- · context --"

CASES = [
    ("no status file", None, BASE),
    ("blocked and asks", "Next: build\nBlocked: waiting on keys\nAsks: may I deploy?\n",
     f"{BASE} · blocked waiting on keys · asks may I deploy?"),
    ("next only when blocked and asks are empty", "Next: build\nBlocked:\nAsks:\n",
     f"{BASE} · next build"),
    ("none, none., dash and n/a are empty",
     "Next: build\nBlocked: none.\nAsks: -\n", f"{BASE} · next build"),
    ("n/a in any case is empty", "Next: go\nBlocked: N/A\n", f"{BASE} · next go"),
    ("none with a trailing clause is empty",
     "Next: cherry-pick\nBlocked: none.\nAsks: none until the draft PR.\n",
     f"{BASE} · next cherry-pick"),
    ("bullet prefix and Kolin asks key", "- Next: a\n- Blocked: stack down\n- Kolin asks: stop stacks?\n",
     f"{BASE} · blocked stack down · asks stop stacks?"),
    ("last non-empty entry wins", "Blocked: old\n## Update\nBlocked: new\nBlocked:\n",
     f"{BASE} · blocked new"),
    ("headings are ignored", "## Next: not a line\nNext: real\n", f"{BASE} · next real"),
    ("long value is cut to 60 characters", "Blocked: " + "x" * 80 + "\n",
     f"{BASE} · blocked " + "x" * 59 + "…"),
]


def run(directory):
    result = subprocess.run(["bash", str(SCRIPT)], input=json.dumps({"workspace": {"current_dir": str(directory)}}),
                            capture_output=True, text=True, check=True)
    return re.sub(r"\x1b\[[0-9;]*m", "", result.stdout).strip()


class StatuslineTests(unittest.TestCase):
    def test_status_segments(self):
        for name, status, expected in CASES:
            with self.subTest(name), tempfile.TemporaryDirectory() as tmp:
                repo = pathlib.Path(tmp)
                subprocess.run(["git", "-C", tmp, "init", "-q"], check=True)
                if status is not None:
                    (repo / ".pstack").mkdir()
                    (repo / ".pstack/status.md").write_text(status)
                self.assertEqual(run(repo), expected)

    def test_subdirectory_finds_top_level_status(self):
        with tempfile.TemporaryDirectory() as tmp:
            repo = pathlib.Path(tmp)
            subprocess.run(["git", "-C", tmp, "init", "-q"], check=True)
            (repo / ".pstack").mkdir()
            (repo / ".pstack/status.md").write_text("Blocked: x\n")
            (repo / "sub").mkdir()
            self.assertEqual(run(repo / "sub"), f"{BASE} · blocked x")


if __name__ == "__main__":
    unittest.main()

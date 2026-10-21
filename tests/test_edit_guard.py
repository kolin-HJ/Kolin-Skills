import json
import os
import pathlib
import subprocess
import sys
import tempfile
import unittest


HOOK = pathlib.Path(__file__).resolve().parent.parent / "hooks/edit-guard.py"
VALUE = "Value: feature\n"
VALUE_DENIED = "write the value case"
ORCHESTRATOR_DENIED = "The orchestrator has edited 2 files here"

CASES = {
    "no status file is denied": dict(edits=["a.txt"], rc=2, fragment=VALUE_DENIED),
    "status without a Value line is denied": dict(status="notes\n", edits=["a.txt"], rc=2, fragment=VALUE_DENIED),
    "Value line allows the edit": dict(status=VALUE, edits=["a.txt"], rc=0),
    "second distinct file is allowed": dict(status=VALUE, edits=["a.txt", "b.txt"], rc=0),
    "third distinct file is denied": dict(
        status=VALUE, edits=["a.txt", "b.txt", "c.txt"], rc=2, fragment=ORCHESTRATOR_DENIED
    ),
    "re-editing a counted file is allowed": dict(status=VALUE, edits=["a.txt", "b.txt", "a.txt"], rc=0),
    "orchestrator-builds allows a third file": dict(
        status=VALUE + "orchestrator-builds: three-line rename\n", edits=["a.txt", "b.txt", "c.txt"], rc=0
    ),
    "counts are per session": dict(
        status=VALUE, edits=["a.txt", "b.txt"], sessions=["s1", "s1", "s2"], rc=0, last="c.txt"
    ),
    "subagent edit is allowed without status": dict(edits=["a.txt"], agent_id="a1", rc=0),
    "file outside git is allowed and never counted": dict(
        status=VALUE, edits=["outside/a.txt", "outside/b.txt", "outside/c.txt"], rc=0
    ),
    "the status file itself is allowed": dict(edits=[".pstack/status.md"], rc=0),
    "git-ignored file is allowed": dict(ignore="ignored.log\n", edits=["ignored.log"], rc=0),
}


class EditGuardTests(unittest.TestCase):
    def make_repo(self, root):
        home = root / "home"
        work = root / "work"
        home.mkdir()
        work.mkdir()
        (root / "outside").mkdir()
        subprocess.run(["git", "init", "-q", str(work)], check=True)
        return home, work

    def edit(self, home, work, name, agent_id=None, session="s1"):
        base = work.parent if name.startswith("outside/") else work
        payload = {
            "session_id": session,
            "cwd": str(work),
            "tool_name": "Edit",
            "tool_input": {"file_path": str(base / name)},
            "agent_id": agent_id,
        }
        return subprocess.run(
            [sys.executable, str(HOOK)],
            input=json.dumps(payload),
            text=True,
            capture_output=True,
            env={**os.environ, "HOME": str(home)},
            timeout=20,
        )

    def test_decisions(self):
        for label, case in CASES.items():
            with self.subTest(label), tempfile.TemporaryDirectory() as directory:
                root = pathlib.Path(os.path.realpath(directory))
                home, work = self.make_repo(root)
                if "status" in case:
                    (work / ".pstack").mkdir()
                    (work / ".pstack/status.md").write_text(case["status"])
                if "ignore" in case:
                    (work / ".gitignore").write_text(case["ignore"])
                names = [*case["edits"], case["last"]] if "last" in case else case["edits"]
                sessions = case.get("sessions", ["s1"] * len(names))
                for name, session in zip(names[:-1], sessions):
                    self.edit(home, work, name, case.get("agent_id"), session)
                result = self.edit(home, work, names[-1], case.get("agent_id"), sessions[len(names) - 1])
                self.assertEqual(result.returncode, case["rc"], result.stderr)
                self.assertIn(case.get("fragment", ""), result.stderr)

    def test_value_denial_excludes_pstack_once(self):
        with tempfile.TemporaryDirectory() as directory:
            root = pathlib.Path(os.path.realpath(directory))
            home, work = self.make_repo(root)
            first = self.edit(home, work, "a.txt")
            self.edit(home, work, "a.txt")
            self.assertIn(str(work / ".pstack/status.md"), first.stderr)
            exclude = (work / ".git/info/exclude").read_text().splitlines()
            self.assertEqual(exclude.count(".pstack/"), 1)


if __name__ == "__main__":
    unittest.main()

import importlib.machinery
import importlib.util
import json
import os
import pathlib
import shutil
import subprocess
import tempfile
import unittest

REPO = pathlib.Path(__file__).resolve().parent.parent
GATE = REPO / "hooks/gate"


def load_cli():
    loader = importlib.machinery.SourceFileLoader("kolin_skills_cli", str(REPO / "bin/kolin-skills"))
    spec = importlib.util.spec_from_loader(loader.name, loader)
    module = importlib.util.module_from_spec(spec)
    loader.exec_module(module)
    return module


class CloneAndItWorksTests(unittest.TestCase):
    def setUp(self):
        self.tmp = pathlib.Path(tempfile.mkdtemp())

    def tearDown(self):
        shutil.rmtree(self.tmp, ignore_errors=True)

    def fake_node(self, version):
        node = self.tmp / "bin/node"
        node.parent.mkdir(exist_ok=True)
        node.write_text(f"#!/bin/sh\necho {version}\n")
        node.chmod(0o755)
        return node

    def test_node_version_gate(self):
        cli = load_cli()
        old_path = os.environ["PATH"]
        try:
            self.fake_node("v20.19.0")
            os.environ["PATH"] = f"{self.tmp / 'bin'}:{old_path}"
            self.assertIn("too old", cli.node_problem())
            self.fake_node("v22.20.0")
            self.assertIsNone(cli.node_problem())
        finally:
            os.environ["PATH"] = old_path

    def test_gate_scripts_do_not_depend_on_workspace(self):
        for name in ("stop-require-skill-and-gate.sh", "gate-pass.sh"):
            self.assertNotIn("/workspace/", (GATE / name).read_text(), name)
        self.assertTrue(os.access(GATE / "check-skill-use.sh", os.X_OK))

    def test_stop_hook_noop_when_gate_not_set_up(self):
        copy = self.tmp / "gate"
        copy.mkdir()
        shutil.copy(GATE / "stop-require-skill-and-gate.sh", copy)
        result = subprocess.run(["bash", str(copy / "stop-require-skill-and-gate.sh")], input="{}",
                                text=True, capture_output=True, timeout=10)
        self.assertEqual((result.returncode, result.stdout), (0, ""))

    def test_check_skill_use_finds_tool_use(self):
        transcript = self.tmp / "t.jsonl"
        transcript.write_text(json.dumps({"type": "assistant", "message": {"content": [
            {"type": "tool_use", "name": "Skill", "input": {"skill": "poteto-mode"}}]}}) + "\n")
        ok = subprocess.run([str(GATE / "check-skill-use.sh"), str(transcript)], capture_output=True, text=True)
        self.assertEqual(ok.returncode, 0, ok.stdout)

    def test_session_start_pulls_in_claude_and_codex(self):
        for name in ("claude/settings.json", "codex/hooks.json"):
            starts = json.loads((REPO / name).read_text())["hooks"]["SessionStart"]
            commands = [hook["command"] for entry in starts if entry.get("matcher") == "startup" for hook in entry["hooks"]]
            self.assertTrue(any("kolin-skills' pull --quiet" in c for c in commands), name)


if __name__ == "__main__":
    unittest.main()

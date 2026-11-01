import json
import os
import pathlib
import shutil
import subprocess
import sys
import tempfile
import unittest
from unittest import mock

REPO = pathlib.Path(__file__).resolve().parent.parent
sys.path.insert(0, str(REPO / "bin"))
import third_party


class PinnedCliTests(unittest.TestCase):
    def setUp(self):
        self.root = pathlib.Path(tempfile.mkdtemp())
        self.repo = self.root / "repo"
        (self.repo / "upstream").mkdir(parents=True)
        (self.repo / "upstream/tools.json").write_text(json.dumps({"npm": {"agent-browser": "0.41.0"}}))
        self.global_root = self.root / "global"
        self.global_root.mkdir()
        fake_bin = self.root / "bin"
        fake_bin.mkdir()
        self.calls = self.root / "npm-calls"
        self.root_exit = self.root / "root-exit"
        self.install_exit = self.root / "install-exit"
        (fake_bin / "npm").write_text(
            "#!/bin/sh\n"
            f"echo \"$@\" >> {self.calls}\n"
            f"if [ \"$1\" = root ]; then [ -f {self.root_exit} ] && {{ echo 'npm ERR! prefix broken' >&2; exit 2; }}; echo {self.global_root}; exit 0; fi\n"
            f"[ -f {self.install_exit} ] && exit 1\n"
            "exit 0\n")
        (fake_bin / "npm").chmod(0o755)
        self.path = mock.patch.dict(os.environ, {"PATH": f"{fake_bin}{os.pathsep}{os.environ['PATH']}"})
        self.path.start()

    def tearDown(self):
        self.path.stop()
        shutil.rmtree(self.root)

    def install(self, version):
        package = self.global_root / "agent-browser"
        package.mkdir(exist_ok=True)
        (package / "package.json").write_text(json.dumps({"name": "agent-browser", "version": version}))

    def test_missing_cli_names_the_pin_and_the_fix(self):
        self.assertEqual(third_party.npm_tool_problems(self.repo),
                         ["agent-browser is not installed, pinned at 0.41.0 in upstream/tools.json; run kolin-skills upstream"])

    def test_other_version_is_a_problem(self):
        self.install("0.40.0")
        self.assertEqual(third_party.npm_tool_problems(self.repo),
                         ["agent-browser is 0.40.0 installed, pinned at 0.41.0 in upstream/tools.json; run kolin-skills upstream"])

    def test_pinned_version_passes(self):
        self.install("0.41.0")
        self.assertEqual(third_party.npm_tool_problems(self.repo), [])

    def installs(self):
        lines = self.calls.read_text().splitlines() if self.calls.exists() else []
        return [line for line in lines if line.startswith("install")]

    def test_npm_root_failure_shows_npm_error(self):
        self.root_exit.touch()
        self.assertEqual(third_party.npm_tool_problems(self.repo),
                         ["pinned CLIs in upstream/tools.json not checked: npm root --global failed (exit 2): npm ERR! prefix broken"])

    def test_install_skips_a_cli_at_its_pin(self):
        self.install("0.41.0")
        self.assertEqual(third_party.install_npm_tools(self.repo), [])
        self.assertEqual(self.installs(), [])

    def test_install_moves_a_cli_to_its_pin_with_its_script_allowed(self):
        self.install("0.40.0")
        self.assertEqual(third_party.install_npm_tools(self.repo), [])
        self.assertEqual(self.installs(), ["install --global --allow-scripts=agent-browser agent-browser@0.41.0"])

    def test_failed_install_is_reported(self):
        self.install_exit.touch()
        self.assertEqual(third_party.install_npm_tools(self.repo), ["agent-browser"])

    def test_repo_manifest_pins_exact_versions(self):
        pins = third_party.npm_tool_pins(REPO)
        self.assertEqual(set(pins), {"agent-browser", "agent-desktop"})
        for version in pins.values():
            self.assertRegex(version, r"^\d+\.\d+\.\d+$")


@unittest.skipIf(shutil.which("codex") is None, "codex is not installed")
class CodexRuleTests(unittest.TestCase):
    def decision(self, *command):
        result = subprocess.run(["codex", "execpolicy", "check", "--rules", str(REPO / "codex/rules/agent-tools.rules"), *command],
                                text=True, capture_output=True, timeout=30, check=True)
        return json.loads(result.stdout).get("decision")

    def test_only_the_browser_guard_runs_outside_the_sandbox(self):
        self.assertEqual(self.decision("agent-browser-guard", "open", "https://example.com"), "allow")
        self.assertIsNone(self.decision("agent-browser", "--executable-path", "./x.sh", "open", "about:blank"))

    def test_agent_desktop_asks_each_time(self):
        self.assertEqual(self.decision("agent-desktop", "snapshot", "-i"), "prompt")

    def test_other_commands_keep_the_sandbox(self):
        self.assertIsNone(self.decision("npx", "agent-browser", "open"))
        self.assertIsNone(self.decision("rm", "-rf", "/"))


if __name__ == "__main__":
    unittest.main()

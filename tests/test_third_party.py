import json
import os
import pathlib
import shutil
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
        (fake_bin / "npm").write_text(f"#!/bin/sh\necho {self.global_root}\n")
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

    def test_repo_manifest_pins_exact_versions(self):
        pins = third_party.npm_tool_pins(REPO)
        self.assertEqual(set(pins), {"agent-browser", "agent-desktop"})
        for version in pins.values():
            self.assertRegex(version, r"^\d+\.\d+\.\d+$")


if __name__ == "__main__":
    unittest.main()

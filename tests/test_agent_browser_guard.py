import json
import os
import pathlib
import shutil
import subprocess
import sys
import tempfile
import unittest

REPO = pathlib.Path(__file__).resolve().parent.parent
GUARD = REPO / "bin/agent-browser-guard"


class AgentBrowserGuardTests(unittest.TestCase):
    def setUp(self):
        self.home = pathlib.Path(tempfile.mkdtemp()).resolve()
        self.addCleanup(shutil.rmtree, self.home)
        self.root = self.home / ".agent-browser-evidence"
        self.record = self.home / "record.json"
        fake_bin = self.home / "bin"
        fake_bin.mkdir()
        fake = fake_bin / "agent-browser"
        fake.write_text(
            f"#!{sys.executable}\n"
            "import json, os, sys\n"
            f"json.dump({{'args': sys.argv[1:], 'cwd': os.getcwd(), 'env': {{k: v for k, v in os.environ.items() if k.startswith('AGENT_BROWSER_')}}}}, open({str(self.record)!r}, 'w'))\n")
        fake.chmod(0o755)
        self.outside = self.home / "fixture.txt"
        self.outside.write_text("x")
        self.env = {"HOME": str(self.home), "PATH": f"{fake_bin}{os.pathsep}{os.environ['PATH']}",
                    "AGENT_BROWSER_EXECUTABLE_PATH": "/bin/sh", "AGENT_BROWSER_CONFIG": "/tmp/c.json",
                    "AGENT_BROWSER_SESSION": "work"}

    def run_guard(self, *args):
        self.record.unlink(missing_ok=True)
        return subprocess.run([sys.executable, str(GUARD), *args], env=self.env, cwd=self.home,
                              text=True, capture_output=True, timeout=30)

    def assert_refused(self, *args):
        result = self.run_guard(*args)
        self.assertEqual(result.returncode, 2, (args, result.stdout, result.stderr))
        self.assertIn("agent-browser-guard: refused:", result.stderr)
        self.assertFalse(self.record.exists(), args)

    def assert_passed(self, *args):
        result = self.run_guard(*args)
        self.assertEqual(result.returncode, 0, (args, result.stderr))
        recorded = json.loads(self.record.read_text())
        self.assertEqual(recorded["args"], ["--namespace", "codex-guard", *args])
        return recorded

    def test_flags_that_run_a_program_or_reuse_logins_are_refused(self):
        for args in [("--executable-path", "./x.sh", "open", "about:blank"), ("--executable-path=./x.sh", "open", "a"),
                     ("--args", "--renderer-cmd-prefix=/bin/sh", "open", "a"), ("--extension", "ext", "open", "a"),
                     ("--config", "c.json", "open", "a"), ("--profile", "Default", "open", "a"), ("-p", "ios", "open", "a"),
                     ("--cdp", "9222", "snapshot"), ("--auto-connect", "snapshot"), ("--engine", "x", "open", "a"),
                     ("open", "a", "--executable-path", "./x.sh"), ("open", "a", "--profile=Default")]:
            self.assert_refused(*args)

    def test_commands_that_change_the_install_or_run_code_are_refused(self):
        for args in [("install",), ("upgrade",), ("doctor", "--fix"), ("connect", "9222"), ("auth", "login", "x"),
                     ("plugin", "run", "x", "y"), ("chat", "hi"), ("mcp",), ("dashboard",), ("batch", "open x", "screenshot /etc/x"),
                     ("stream", "enable"), ("--session", "upgrade"), ()]:
            self.assert_refused(*args)

    def test_writes_outside_the_evidence_root_are_refused(self):
        self.root.mkdir(mode=0o700)
        (self.root / "link").symlink_to(self.home)
        for args in [("screenshot", "~/.zshrc"), ("screenshot", str(self.home / "a.png")), ("download", "@e1", "../x"),
                     ("screenshot", "sub/../../x.png"), ("--screenshot-dir", str(self.home), "screenshot"),
                     ("--screenshot-dir=/tmp/x", "screenshot"), ("screenshot", "link/x.png"), ("state", "save", str(self.outside)),
                     ("upload", "@e1", str(self.home / "missing.txt")),
                     ("--session", "upload", "download", "@e1", str(self.outside)), ("--session", "upload", "screenshot", str(self.outside)),
                     ("--namespace", "upload", "state", "save", str(self.outside)), ("upload", str(self.outside), "@e1"),
                     ("network", "har", "stop", "load", str(self.outside)), ("pdf", str(self.outside))]:
            self.assert_refused(*args)

    def test_normal_use_passes_with_a_clean_env_in_the_evidence_root(self):
        recorded = self.assert_passed("open", "https://example.com")
        self.assertEqual(recorded["cwd"], str(self.root))
        self.assertEqual(recorded["env"], {"AGENT_BROWSER_SESSION": "work"})
        for args in [("snapshot", "-i"), ("open", "localhost:3000/a/b"), ("screenshot", "shot.png"),
                     ("screenshot", str(self.root / "a.png")), ("fill", "@e1", "hello world"),
                     ("upload", "@e1", str(self.outside)), ("state", "load", str(self.outside)),
                     ("open", "a", "--state", str(self.outside)), ("diff", "screenshot", "--baseline", str(self.outside))]:
            self.assert_passed(*args)

    def test_caller_cannot_pick_another_namespace_or_restore_state(self):
        for args in [("--namespace", "default", "snapshot"), ("snapshot", "--namespace=default"), ("open", "a", "--restore", "x"),
                     ("open", "a", "--session-name", "x"), ("open", "a", "--restore-save", "always")]:
            self.assert_refused(*args)
        recorded = self.assert_passed("--session", "default", "cookies", "get")
        self.assertEqual(recorded["args"][:2], ["--namespace", "codex-guard"])

    def test_a_symlinked_evidence_root_is_refused(self):
        self.root.symlink_to(self.home)
        self.assert_refused("open", "https://example.com")


if __name__ == "__main__":
    unittest.main()

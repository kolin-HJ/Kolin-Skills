import json
import os
import pathlib
import signal
import subprocess
import sys
import tempfile
import time
import unittest


HOOK = pathlib.Path(__file__).resolve().parent.parent / "hooks/keep-awake.py"
FAKE_CAFFEINATE = '#!/bin/sh\necho "$$ $@" >> "$FAKE_ARGV_LOG"\nexec sleep 60\n'


class KeepAwakeTests(unittest.TestCase):
    def setUp(self):
        directory = tempfile.TemporaryDirectory()
        self.addCleanup(directory.cleanup)
        self.root = pathlib.Path(directory.name)
        self.bin = self.root / "bin"
        self.bin.mkdir()
        self.log = self.root / "argv.log"
        self.addCleanup(self.stop_all)

    def stop_all(self):
        if self.log.is_file():
            for line in self.log.read_text().splitlines():
                try:
                    os.kill(int(line.split()[0]), signal.SIGKILL)
                except ProcessLookupError:
                    pass

    def run_hook(self, path):
        env = {**os.environ, "PATH": path, "FAKE_ARGV_LOG": str(self.log)}
        return subprocess.run(
            [sys.executable, str(HOOK)],
            input=json.dumps({"session_id": "s1", "hook_event_name": "UserPromptSubmit"}),
            text=True,
            capture_output=True,
            env=env,
            timeout=20,
        )

    def test_starts_caffeinate_tied_to_the_claude_process(self):
        fake = self.bin / "caffeinate"
        fake.write_text(FAKE_CAFFEINATE)
        fake.chmod(0o755)
        result = self.run_hook(f"{self.bin}:{os.environ['PATH']}")
        self.assertEqual((result.returncode, result.stdout), (0, ""), result.stderr)
        deadline = time.time() + 5
        while time.time() < deadline and not self.log.is_file():
            time.sleep(0.05)
        self.assertEqual(self.log.read_text().split()[1:], ["-i", "-t", "3600", "-w", str(os.getpid())])

    def test_without_caffeinate_exits_silently(self):
        empty = self.root / "empty"
        empty.mkdir()
        result = self.run_hook(str(empty))
        self.assertEqual((result.returncode, result.stdout, result.stderr), (0, "", ""))
        self.assertFalse(self.log.exists())


if __name__ == "__main__":
    unittest.main()

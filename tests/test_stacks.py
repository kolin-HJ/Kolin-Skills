import datetime
import json
import os
import pathlib
import shutil
import stat
import subprocess
import sys
import tempfile
import unittest

CLI = pathlib.Path(__file__).resolve().parent.parent / "bin/kolin-skills"


class StacksTests(unittest.TestCase):
    def setUp(self):
        self.home = pathlib.Path(tempfile.mkdtemp())
        self.bin = self.home / "fakebin"
        self.bin.mkdir()
        self.stops = self.home / "stops.log"
        self.ps_lines = []
        self.checkout = (self.home / "checkout").resolve()
        (self.checkout / "node_modules/.bin").mkdir(parents=True)
        self.executable(self.checkout / "node_modules/.bin/supabase", f'echo "$PWD $@" >> {self.stops}')

    def tearDown(self):
        shutil.rmtree(self.home)

    def executable(self, path, body):
        path.write_text(f"#!/bin/sh\n{body}\n")
        path.chmod(path.stat().st_mode | stat.S_IXUSR)

    def stack(self, name, hours_started, root=None, transcript_hours=None, running=True):
        directory = self.home / ".supabase/stacks" / name
        directory.mkdir(parents=True)
        root = root or str(self.checkout)
        (directory / "state.json").write_text(json.dumps({"identity": {"projectRoot": root}, "runtime": "native"}))
        started = datetime.datetime.now(datetime.timezone.utc) - datetime.timedelta(hours=hours_started)
        (directory / "owner.json").write_text(json.dumps({"startedAt": started.isoformat().replace("+00:00", "Z"), "pid": 1}))
        if running:
            self.ps_lines.append(f"/cache/bin/.postgres-wrapped -D {directory}/data/x")
        if transcript_hours is not None:
            transcript = self.home / ".claude_personal/projects" / root.replace("/", "-").replace(".", "-") / "s.jsonl"
            transcript.parent.mkdir(parents=True, exist_ok=True)
            transcript.write_text("{}")
            when = datetime.datetime.now().timestamp() - transcript_hours * 3600
            os.utime(transcript, (when, when))

    def run_cli(self, *args):
        (self.home / "ps.out").write_text("\n".join(self.ps_lines) + "\n")
        self.executable(self.bin / "ps", f"cat {self.home / 'ps.out'}")
        env = {**os.environ, "HOME": str(self.home), "PATH": f"{self.bin}:{os.environ['PATH']}", "CLAUDE_CONFIG_DIR": str(self.home / ".claude")}
        return subprocess.run([sys.executable, str(CLI), "stacks", *args], env=env, text=True, capture_output=True, timeout=30)

    def test_idle_stack_is_listed_and_stopped(self):
        self.stack("a1", 30)
        listed = self.run_cli()
        self.assertIn(f"idle  {self.checkout}", listed.stdout)
        self.assertFalse(self.stops.exists())
        stopped = self.run_cli("--stop")
        self.assertEqual(stopped.returncode, 0)
        self.assertIn("stop exit 0", stopped.stdout)
        self.assertEqual(self.stops.read_text().strip(), f"{self.checkout} stop")

    def test_stack_with_fresh_transcript_is_kept(self):
        self.stack("a1", 30, transcript_hours=0.5)
        result = self.run_cli("--stop")
        self.assertIn(f"keep  {self.checkout}", result.stdout)
        self.assertFalse(self.stops.exists())

    def test_stack_with_old_transcript_is_stopped(self):
        self.stack("a1", 30, transcript_hours=5)
        self.run_cli("--stop")
        self.assertTrue(self.stops.exists())

    def test_recently_started_stack_is_kept(self):
        self.stack("a1", 3)
        result = self.run_cli("--stop")
        self.assertIn("keep", result.stdout)
        self.assertFalse(self.stops.exists())
        self.run_cli("--stop", "--idle-hours", "1")
        self.assertTrue(self.stops.exists())

    def test_stack_without_running_postgres_is_ignored(self):
        self.stack("a1", 30, running=False)
        self.assertIn("0 running, 0 idle", self.run_cli("--stop").stdout)

    def test_root_without_cli_is_reported(self):
        self.stack("a1", 30, root="/work/gone")
        result = self.run_cli("--stop")
        self.assertIn("no CLI", result.stdout)
        self.assertEqual(result.returncode, 1)

    def test_notice_prints_one_line_or_nothing(self):
        self.stack("a1", 30)
        self.stack("a2", 30)
        result = self.run_cli("--notice")
        self.assertEqual(len(result.stdout.splitlines()), 1)
        message = json.loads(result.stdout)["systemMessage"]
        self.assertIn("2 idle", message)
        self.assertIn("kolin-skills stacks --stop", message)
        self.assertFalse(self.stops.exists())

    def test_notice_is_silent_without_idle_stacks(self):
        self.stack("a1", 1)
        self.assertEqual(self.run_cli("--notice").stdout, "")


if __name__ == "__main__":
    unittest.main()

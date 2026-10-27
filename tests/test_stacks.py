import datetime
import json
import os
import pathlib
import re
import shutil
import stat
import subprocess
import sys
import tempfile
import threading
import unittest

CLI = pathlib.Path(__file__).resolve().parent.parent / "bin/kolin-skills"
SLEEP = "import time; time.sleep(300)"
SLOW_EXIT = "import signal, sys, time; signal.signal(signal.SIGTERM, lambda *_: (time.sleep(1.5), sys.exit(0))); time.sleep(300)"
FAKE_PS = """if [ "$1" = "-p" ]; then exec /bin/ps "$@"; fi
while IFS=: read -r pid line; do
  kill -0 "$pid" 2>/dev/null && echo "$line"
done < PS_OUT
exit 0
"""


class StacksTests(unittest.TestCase):
    def setUp(self):
        self.home = pathlib.Path(tempfile.mkdtemp())
        self.bin = self.home / "fakebin"
        self.bin.mkdir()
        self.ps_lines = []
        self.owners = {}
        self.checkout = (self.home / "checkout").resolve()
        self.checkout.mkdir()
        self.lsof_out = ""

    def tearDown(self):
        for owner in self.owners.values():
            owner.kill()
            owner.wait()
        shutil.rmtree(self.home)

    def executable(self, path, body):
        path.write_text(f"#!/bin/sh\n{body}\n")
        path.chmod(path.stat().st_mode | stat.S_IXUSR)

    def stack(self, name, hours_started, root=None, transcript_hours=None, running=True, owner_argv0="supabase", owner_code=SLEEP):
        directory = self.home / ".supabase/stacks" / name
        directory.mkdir(parents=True)
        root = root or str(self.checkout)
        owner = subprocess.Popen([sys.executable, "-c", owner_code, owner_argv0])
        threading.Thread(target=owner.wait, daemon=True).start()
        self.owners[name] = owner
        (directory / "state.json").write_text(json.dumps({"identity": {"projectRoot": root}, "runtime": "native"}))
        started = datetime.datetime.now(datetime.timezone.utc) - datetime.timedelta(hours=hours_started)
        (directory / "owner.json").write_text(json.dumps({"startedAt": started.isoformat().replace("+00:00", "Z"), "pid": owner.pid}))
        if running:
            self.ps_lines.append(f"{owner.pid}:/cache/bin/.postgres-wrapped -D {directory}/data/x")
        if transcript_hours is not None:
            transcript = self.home / ".claude_personal/projects" / re.sub(r"[^A-Za-z0-9]", "-", root) / "s.jsonl"
            transcript.parent.mkdir(parents=True, exist_ok=True)
            transcript.write_text("{}")
            when = datetime.datetime.now().timestamp() - transcript_hours * 3600
            os.utime(transcript, (when, when))

    def signalled(self, name):
        try:
            self.owners[name].wait(timeout=1)
        except subprocess.TimeoutExpired:
            return False
        return True

    def run_cli(self, *args):
        (self.home / "ps.out").write_text("\n".join(self.ps_lines) + "\n")
        self.executable(self.bin / "ps", FAKE_PS.replace("PS_OUT", str(self.home / "ps.out")))
        (self.home / "lsof.out").write_text(self.lsof_out)
        self.executable(self.bin / "lsof", f"cat {self.home / 'lsof.out'}")
        env = {**os.environ, "HOME": str(self.home), "PATH": f"{self.bin}:{os.environ['PATH']}", "CLAUDE_CONFIG_DIR": str(self.home / ".claude")}
        return subprocess.run([sys.executable, str(CLI), "stacks", *args], env=env, text=True, capture_output=True, timeout=60)

    def test_idle_stack_is_listed_then_stopped_by_signalling_its_owner(self):
        self.stack("a1", 30)
        listed = self.run_cli()
        self.assertIn(f"idle  {self.checkout}", listed.stdout)
        self.assertIsNone(self.owners["a1"].poll())
        stopped = self.run_cli("--stop")
        self.assertEqual(stopped.returncode, 0)
        self.assertIn(f"{self.checkout}: stopped", stopped.stdout)
        self.assertTrue(self.signalled("a1"))
        self.assertEqual(self.owners["a1"].returncode, -15)

    def test_stop_waits_until_postgres_is_gone(self):
        self.stack("a1", 30, owner_code=SLOW_EXIT)
        result = self.run_cli("--stop")
        self.assertIn(f"{self.checkout}: stopped", result.stdout)
        self.assertEqual(result.returncode, 0)

    def test_stack_with_fresh_transcript_is_kept(self):
        self.stack("a1", 30, transcript_hours=0.5)
        result = self.run_cli("--stop")
        self.assertIn(f"keep  {self.checkout}", result.stdout)
        self.assertFalse(self.signalled("a1"))

    def test_stack_with_old_transcript_is_stopped(self):
        self.stack("a1", 30, transcript_hours=5)
        self.run_cli("--stop")
        self.assertTrue(self.signalled("a1"))

    def test_recently_started_stack_is_kept(self):
        self.stack("a1", 3)
        result = self.run_cli("--stop")
        self.assertIn("keep", result.stdout)
        self.assertFalse(self.signalled("a1"))
        self.run_cli("--stop", "--idle-hours", "1")
        self.assertTrue(self.signalled("a1"))

    def test_stack_without_running_postgres_is_ignored(self):
        self.stack("a1", 30, running=False)
        self.assertIn("0 running, 0 idle", self.run_cli("--stop").stdout)
        self.assertFalse(self.signalled("a1"))

    def test_owner_pid_that_is_not_supabase_is_never_signalled(self):
        self.stack("a1", 30, owner_argv0="reused")
        result = self.run_cli("--stop")
        self.assertIn("is not a supabase process", result.stdout)
        self.assertEqual(result.returncode, 1)
        self.assertFalse(self.signalled("a1"))

    def test_root_with_a_working_process_is_skipped(self):
        self.stack("a1", 30)
        self.stack("a2", 30, root="/work/other")
        self.lsof_out = f"p10\ncnode\nn{self.checkout}/src\np11\ncsupabase\nn/work/other\n"
        result = self.run_cli("--stop")
        self.assertIn("skipped", result.stdout)
        self.assertFalse(self.signalled("a1"))
        self.assertTrue(self.signalled("a2"))

    def test_transcript_folder_name_replaces_every_symbol(self):
        self.stack("a1", 30, root="/work/my_app.v2", transcript_hours=0.5)
        self.assertIn("keep  /work/my_app.v2", self.run_cli().stdout)

    def test_notice_prints_one_line_or_nothing(self):
        self.stack("a1", 30)
        self.stack("a2", 30)
        result = self.run_cli("--notice")
        self.assertEqual(len(result.stdout.splitlines()), 1)
        message = json.loads(result.stdout)["systemMessage"]
        self.assertIn("2 idle", message)
        self.assertIn("kolin-skills stacks --stop", message)
        self.assertFalse(self.signalled("a1"))

    def test_notice_is_silent_without_idle_stacks(self):
        self.stack("a1", 1)
        self.assertEqual(self.run_cli("--notice").stdout, "")


if __name__ == "__main__":
    unittest.main()

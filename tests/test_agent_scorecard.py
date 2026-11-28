import json
import os
import pathlib
import shutil
import subprocess
import sys
import tempfile
import time
import unittest

REPO = pathlib.Path(__file__).resolve().parent.parent
CLI = REPO / "bin/agent-scorecard"


def git(cwd, *args, env=None):
    merged = {**os.environ, **(env or {})}
    return subprocess.run(
        ["git", "-C", str(cwd), "-c", "user.email=t@t", "-c", "user.name=t", *args],
        check=True, text=True, capture_output=True, env=merged,
    )


def write_transcript(path, *records):
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text("".join(json.dumps(record) + "\n" for record in records))


class AgentScorecardTests(unittest.TestCase):
    def setUp(self):
        self.home = pathlib.Path(tempfile.mkdtemp()).resolve()
        self.addCleanup(shutil.rmtree, self.home)

    def run_cli(self, *args):
        env = {**os.environ, "HOME": str(self.home), "CLAUDE_CONFIG_DIR": str(self.home / ".claude")}
        return subprocess.run([sys.executable, str(CLI), *args], env=env, text=True, capture_output=True, timeout=60)

    def test_scorecard_measures_rework_thrash_and_baseline_comparison(self):
        repo = self.home / "app"
        repo.mkdir()
        git(repo, "init", "-q", "-b", "main")
        now = int(time.time())
        t1 = str(now - 3 * 86400)
        t2 = str(now - 2 * 86400)
        t3 = str(now - 1 * 86400)
        (repo / "a.py").write_text("x = 1\n")
        git(repo, "add", "-A")
        git(repo, "commit", "-qm", "feat: add a", env={"GIT_AUTHOR_DATE": f"{t1} +0000", "GIT_COMMITTER_DATE": f"{t1} +0000"})
        (repo / "b.py").write_text("y = 2\n")
        git(repo, "add", "-A")
        git(repo, "commit", "-qm", "feat: add b", env={"GIT_AUTHOR_DATE": f"{t2} +0000", "GIT_COMMITTER_DATE": f"{t2} +0000"})
        (repo / "a.py").write_text("x = 2\n")
        git(repo, "add", "-A")
        git(repo, "commit", "-qm", "fix(a): repair a", env={"GIT_AUTHOR_DATE": f"{t3} +0000", "GIT_COMMITTER_DATE": f"{t3} +0000"})

        projects = self.home / ".claude/projects/p"
        write_transcript(
            projects / "s1.jsonl",
            {
                "type": "assistant",
                "message": {
                    "id": "m1",
                    "model": "claude-opus-5-5",
                    "usage": {"input_tokens": 1_000_000, "output_tokens": 0},
                    "content": [
                        {"type": "tool_use", "id": "t1", "name": "Bash", "input": {}},
                        {"type": "tool_use", "id": "t2", "name": "Read", "input": {}},
                    ],
                },
            },
            {
                "type": "user",
                "message": {
                    "content": [
                        {"type": "tool_result", "tool_use_id": "t1", "is_error": True,
                         "content": "PreToolUse:Bash hook error: [python3 '/r/hooks/bash-guard.py']: Blocked: polling"},
                        {"type": "tool_result", "tool_use_id": "t2", "is_error": False, "content": "ok"},
                    ]
                },
            },
            {"type": "pr-link", "prUrl": "https://github.com/o/r/pull/1"},
            {"type": "system", "subtype": "compact_boundary"},
        )
        baseline_path = self.home / "baseline.json"
        first = self.run_cli("--days", "14", "--repo", str(repo), "--save", str(baseline_path), "--json")
        self.assertEqual(first.returncode, 0, first.stderr)
        data = json.loads(first.stdout)
        summary = data["summary"]
        self.assertEqual(summary["rework_rate"], 0.5)
        self.assertEqual(summary["thrash_rate"], 0.5)
        self.assertEqual(summary["hook_block_rate"], 0.5)
        self.assertEqual(summary["compactions_per_session"], 1.0)
        self.assertEqual(summary["cost_per_pr"], 4.0)
        self.assertEqual(summary["effective_cost_per_clean_pr"], 8.0)

        better_baseline = json.loads(baseline_path.read_text())
        better_baseline["summary"]["rework_rate"] = 0.8
        better_baseline["summary"]["thrash_rate"] = 0.2
        baseline_path.write_text(json.dumps(better_baseline))
        compared = self.run_cli("--days", "14", "--repo", str(repo), "--compare", str(baseline_path), "--json")
        self.assertEqual(compared.returncode, 0, compared.stderr)
        verdicts = {row["metric"]: row["verdict"] for row in json.loads(compared.stdout)["comparison"]}
        self.assertEqual(verdicts["rework_rate"], "BETTER")
        self.assertEqual(verdicts["thrash_rate"], "WORSE")

    def test_seed_benchmark_reference_solutions_all_pass(self):
        result = self.run_cli("--bench", "--json")
        self.assertEqual(result.returncode, 0, result.stderr + result.stdout)
        data = json.loads(result.stdout)
        self.assertEqual(data["mode"], "reference")
        self.assertGreaterEqual(data["total"], 4)
        self.assertEqual(data["passed"], data["total"], data["tasks"])

    def test_benchmark_runner_fails_when_diff_adds_comments_or_breaks_tests(self):
        suite = self.home / "suite.json"
        suite.write_text(json.dumps({
            "version": 1,
            "tasks": [{
                "id": "no-slop",
                "title": "no comments",
                "prompt": "edit a.py",
                "files": {"a.py": "def f():\n    return 1\n"},
                "checks": {"diff_audit_clean": True, "test_cmd": "python3 -c 'import a; assert a.f() == 2'"},
            }],
        }))
        bad_runner = "python3 -c 'open(\"a.py\",\"w\").write(\"# comment\\ndef f():\\n    return 2\\n\")'"
        bad = self.run_cli("--bench", str(suite), "--runner", bad_runner, "--json")
        self.assertEqual(bad.returncode, 1)
        bad_data = json.loads(bad.stdout)
        self.assertEqual(bad_data["passed"], 0)
        self.assertIn("diff-audit", bad_data["tasks"][0]["failures"][0])

        good_runner = "python3 -c 'open(\"a.py\",\"w\").write(\"def f():\\n    return 2\\n\")'"
        good = self.run_cli("--bench", str(suite), "--runner", good_runner, "--json")
        self.assertEqual(good.returncode, 0, good.stderr + good.stdout)
        self.assertEqual(json.loads(good.stdout)["passed"], 1)


if __name__ == "__main__":
    unittest.main()

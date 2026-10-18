import json
import os
import pathlib
import shutil
import subprocess
import sys
import tempfile
import unittest

REPO = pathlib.Path(__file__).resolve().parent.parent
CLI = REPO / "bin/kolin-skills"


class ApplyTests(unittest.TestCase):
    def setUp(self):
        self.home = pathlib.Path(tempfile.mkdtemp())
        self.repo = self.home / "Kolin-Skills"
        shutil.copytree(REPO, self.repo, ignore=shutil.ignore_patterns(".git", "evals", "mods", "__pycache__"))
        (self.repo / "mods/usage-band").mkdir(parents=True)
        (self.repo / "mods/savvy-progress").mkdir(parents=True)
        (self.repo / "evals").mkdir()

    def tearDown(self):
        shutil.rmtree(self.home)

    def run_cli(self, *args):
        env = {**os.environ, "HOME": str(self.home)}
        return subprocess.run(
            [sys.executable, str(self.repo / "bin/kolin-skills"), *args],
            env=env, text=True, capture_output=True, timeout=60,
        )

    def test_edits_in_the_repo_are_live_through_links(self):
        self.assertEqual(self.run_cli("apply").returncode, 0)
        policy = self.repo / "policy/AGENTS.md"
        policy.write_text("edited in the repo\n")
        for relative in [".codex/AGENTS.md", ".claude/CLAUDE.md", ".grok/AGENTS.md"]:
            self.assertEqual((self.home / relative).read_text(), "edited in the repo\n", relative)
        skill = self.home / ".claude/skills/full-send/SKILL.md"
        self.assertEqual(skill.resolve(), (self.repo / "skills/full-send/SKILL.md").resolve())

    def test_second_apply_changes_nothing_and_check_passes(self):
        self.assertEqual(self.run_cli("apply").returncode, 0)
        again = self.run_cli("apply")
        self.assertEqual((again.returncode, again.stdout), (0, "already in sync\n"))
        self.assertEqual(self.run_cli("apply", "--check").returncode, 0)

    def test_foreign_hooks_and_settings_survive_while_managed_ones_are_replaced(self):
        settings = self.home / ".claude/settings.json"
        settings.parent.mkdir(parents=True)
        legacy = str(self.home / ".codex/hooks/lint-changed-lines.py")
        settings.write_text(json.dumps({
            "permissions": {"allow": ["Bash(ls)"]},
            "env": {"MINE": "1"},
            "hooks": {
                "SessionStart": [{"matcher": "*", "hooks": [{"type": "command", "command": "bash herdr.sh session"}]}],
                "PostToolUse": [{"matcher": "Write|Edit", "hooks": [{"type": "command", "command": f"python3 '{legacy}'"}]}],
            },
        }))
        self.assertEqual(self.run_cli("apply").returncode, 0)
        merged = json.loads(settings.read_text())
        self.assertEqual(merged["permissions"], {"allow": ["Bash(ls)"]})
        self.assertEqual(merged["env"]["MINE"], "1")
        self.assertEqual(merged["env"]["CLAUDE_CODE_SUBAGENT_MODEL"], "claude-sonnet-5-5")
        self.assertIn("herdr.sh", json.dumps(merged["hooks"]["SessionStart"]))
        post = json.dumps(merged["hooks"]["PostToolUse"])
        self.assertNotIn(legacy, post)
        self.assertEqual(post.count("lint-changed-lines.py"), 1)
        self.assertIn(str(self.repo), post)

    def test_a_real_file_in_the_way_is_backed_up_not_lost(self):
        target = self.home / ".codex/AGENTS.md"
        target.parent.mkdir(parents=True)
        target.write_text("old policy\n")
        self.assertEqual(self.run_cli("apply").returncode, 0)
        self.assertTrue(target.is_symlink())
        backups = list((self.home / ".kolin-skills/backup").rglob("AGENTS.md"))
        self.assertEqual([path.read_text() for path in backups], ["old policy\n"])

    def test_removing_a_skill_or_agent_from_the_repo_removes_it_everywhere(self):
        self.assertEqual(self.run_cli("apply").returncode, 0)
        self.assertTrue((self.home / ".codex/agents/haiku-worker.toml").is_file())
        shutil.rmtree(self.repo / "skills/explainer")
        (self.repo / "agents/haiku-worker.md").unlink()
        self.assertEqual(self.run_cli("apply").returncode, 0)
        for relative in [".agents/skills/explainer", ".claude/skills/explainer", ".cursor/skills/explainer",
                         ".claude/agents/haiku-worker.md", ".codex/agents/haiku-worker.toml"]:
            path = self.home / relative
            self.assertFalse(path.exists() or path.is_symlink(), relative)

    def test_a_second_checkout_cannot_take_over_home_unless_it_adopts_it(self):
        self.assertEqual(self.run_cli("apply").returncode, 0)
        first = self.repo
        self.repo = self.home / "copy-of-Kolin-Skills"
        shutil.copytree(first, self.repo)
        refused = self.run_cli("apply")
        self.assertEqual(refused.returncode, 1)
        self.assertIn(str(first), refused.stderr)
        self.assertEqual((self.home / ".codex/AGENTS.md").resolve(), (first / "policy/AGENTS.md").resolve())
        self.assertEqual(self.run_cli("apply", "--adopt").returncode, 0)
        self.assertEqual((self.home / ".codex/AGENTS.md").resolve(), (self.repo / "policy/AGENTS.md").resolve())
        hooks = (self.home / ".claude/settings.json").read_text()
        self.assertNotIn(f"{first}/", hooks)
        self.assertEqual(hooks.count("block-env-reads.py"), 1)

    def git(self, cwd, *args):
        subprocess.run(["git", "-C", str(cwd), "-c", "user.email=t@t", "-c", "user.name=t", *args],
                       check=True, capture_output=True)

    def test_pull_brings_a_skill_pushed_from_another_machine_into_home(self):
        remote = self.home / "remote.git"
        other = self.home / "other-machine"
        self.git(self.repo, "init", "-q", "-b", "main")
        self.git(self.repo, "add", "-A")
        self.git(self.repo, "commit", "-qm", "init")
        self.git(self.home, "clone", "-q", "--bare", str(self.repo), str(remote))
        self.git(self.repo, "remote", "add", "origin", str(remote))
        self.git(self.repo, "fetch", "-q", "origin")
        self.git(self.repo, "branch", "-q", "--set-upstream-to=origin/main")
        self.assertEqual(self.run_cli("apply").returncode, 0)
        self.git(self.home, "clone", "-q", str(remote), str(other))
        (other / "skills/pushed-skill").mkdir()
        (other / "skills/pushed-skill/SKILL.md").write_text("---\nname: pushed-skill\ndescription: x\n---\nx\n")
        self.git(other, "add", "-A")
        self.git(other, "commit", "-qm", "add pushed-skill")
        self.git(other, "push", "-q", "origin", "main")
        result = self.run_cli("pull", "--quiet")
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertIn("add pushed-skill", result.stdout)
        self.assertTrue((self.home / ".claude/skills/pushed-skill/SKILL.md").is_file())

    def test_pull_with_local_edits_applies_the_working_tree_without_pulling(self):
        self.git(self.repo, "init", "-q", "-b", "main")
        (self.repo / "skills/local-only").mkdir()
        (self.repo / "skills/local-only/SKILL.md").write_text("---\nname: local-only\ndescription: x\n---\nx\n")
        result = self.run_cli("pull")
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertIn("skipped pull", result.stdout)
        self.assertTrue((self.home / ".claude/skills/local-only").is_symlink())

    @unittest.skipUnless(shutil.which("python3.14"), "needs a python with tomllib")
    def test_codex_agent_mirror_is_valid_toml_that_keeps_backslashes_and_quotes(self):
        body = 'Match \\d+ in C:\\path and say "hi" """ twice.'
        (self.repo / "agents/escape-probe.md").write_text(
            f"---\nname: escape-probe\ndescription: probe\ntools: Read, Grep\n---\n\n{body}\n")
        self.assertEqual(self.run_cli("apply").returncode, 0)
        toml = self.home / ".codex/agents/escape-probe.toml"
        parsed = subprocess.run(
            ["python3.14", "-c", "import json,sys,tomllib;print(json.dumps(tomllib.load(open(sys.argv[1],'rb'))))", str(toml)],
            text=True, capture_output=True, check=True)
        data = json.loads(parsed.stdout)
        self.assertEqual(data["developer_instructions"].strip(), body)
        self.assertEqual(data["sandbox_mode"], "read-only")

    def test_check_reports_drift_without_touching_home(self):
        result = self.run_cli("apply", "--check")
        self.assertEqual(result.returncode, 1)
        self.assertIn(".codex/AGENTS.md", result.stdout)
        self.assertFalse((self.home / ".codex").exists())


if __name__ == "__main__":
    unittest.main()

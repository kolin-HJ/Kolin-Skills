import fcntl
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
CLI = REPO / "bin/kolin-skills"


class ApplyTests(unittest.TestCase):
    def setUp(self):
        self.home = pathlib.Path(tempfile.mkdtemp())
        self.repo = self.home / "Kolin-Skills"
        shutil.copytree(REPO, self.repo, ignore=shutil.ignore_patterns(".git", "__pycache__"))
        (self.repo / "upstream/skills.json").write_text("{}\n")

    def tearDown(self):
        shutil.rmtree(self.home)

    def run_cli(self, *args, path_prefix=None, extra_env=None):
        env = {key: value for key, value in os.environ.items() if key != "CI"}
        env["HOME"] = str(self.home)
        if path_prefix:
            env["PATH"] = f"{path_prefix}{os.pathsep}{env['PATH']}"
        if extra_env:
            env.update(extra_env)
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
        return subprocess.run(["git", "-C", str(cwd), "-c", "user.email=t@t", "-c", "user.name=t", *args],
                              check=True, capture_output=True, text=True)

    def test_git_hooks_in_a_checkout_leave_a_home_that_is_not_wired_to_it_alone(self):
        self.git(self.repo, "init", "-q", "-b", "main")
        self.git(self.repo, "add", "-A")
        self.git(self.repo, "commit", "-qm", "init")
        self.assertEqual(self.run_cli("apply").returncode, 0)
        other_home = pathlib.Path(tempfile.mkdtemp())
        self.addCleanup(shutil.rmtree, other_home)
        subprocess.run(["git", "-C", str(self.repo), "checkout", "-q", "-b", "feature"],
                       env={**os.environ, "HOME": str(other_home), "PYTHONDONTWRITEBYTECODE": "1"},
                       check=True, capture_output=True)
        self.assertEqual(sorted(path.name for path in other_home.iterdir()), [])
        subprocess.run(["git", "-C", str(self.repo), "checkout", "-q", "main"],
                       env={**os.environ, "HOME": str(self.home)}, check=True, capture_output=True)
        self.assertTrue((self.home / ".claude/skills/full-send").is_symlink())

    def with_remote_one_commit_ahead(self):
        remote = self.home / "remote.git"
        other = self.home / "other-machine"
        self.git(self.repo, "init", "-q", "-b", "main")
        self.git(self.repo, "add", "-A")
        self.git(self.repo, "commit", "-qm", "init")
        self.git(self.home, "clone", "-q", "--bare", str(self.repo), str(remote))
        self.git(self.repo, "remote", "add", "origin", str(remote))
        self.git(self.home, "clone", "-q", str(remote), str(other))
        (other / "skills/pushed-skill").mkdir()
        (other / "skills/pushed-skill/SKILL.md").write_text("---\nname: pushed-skill\ndescription: x\n---\nx\n")
        self.git(other, "add", "-A")
        self.git(other, "commit", "-qm", "add pushed-skill")
        self.git(other, "push", "-q", "origin", "main")

    def test_pull_with_local_edits_applies_the_working_tree_and_says_the_setup_is_stale(self):
        self.with_remote_one_commit_ahead()
        (self.repo / "skills/local-only").mkdir()
        (self.repo / "skills/local-only/SKILL.md").write_text("---\nname: local-only\ndescription: x\n---\nx\n")
        result = self.run_cli("pull", "--quiet")
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertIn("stale setup", result.stdout)
        self.assertIn("1 commits behind origin/main", result.stdout)
        self.assertTrue((self.home / ".claude/skills/local-only").is_symlink())
        self.assertFalse((self.home / ".claude/skills/pushed-skill").exists())

    def fake_git(self, subcommand, body):
        bin_dir = self.home / "fake-bin"
        bin_dir.mkdir()
        script = bin_dir / "git"
        script.write_text(
            "#!/bin/sh\n"
            'for arg in "$@"; do\n'
            f'  if [ "$arg" = {subcommand} ]; then {body}; fi\n'
            "done\n"
            f'exec {shutil.which("git")} "$@"\n'
        )
        script.chmod(0o755)
        return str(bin_dir)

    def test_pull_says_why_when_the_fast_forward_merge_fails(self):
        self.with_remote_one_commit_ahead()
        fake = self.fake_git("merge", "echo 'fatal: cannot fast-forward' >&2; exit 1")
        result = self.run_cli("pull", "--quiet", path_prefix=fake)
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertIn("git merge --ff-only failed: fatal: cannot fast-forward", result.stdout)

    def test_pull_waits_for_the_state_lock_before_touching_the_repo(self):
        self.with_remote_one_commit_ahead()
        head = self.git(self.repo, "rev-parse", "HEAD").stdout
        state = self.home / ".kolin-skills"
        state.mkdir()
        with open(state / "lock", "w") as lock:
            fcntl.flock(lock, fcntl.LOCK_EX)
            env = {**os.environ, "HOME": str(self.home)}
            pulling = subprocess.Popen([sys.executable, str(self.repo / "bin/kolin-skills"), "pull", "--quiet"],
                                       env=env, text=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
            self.addCleanup(pulling.kill)
            time.sleep(1.5)
            self.assertIsNone(pulling.poll())
            self.assertEqual(self.git(self.repo, "rev-parse", "HEAD").stdout, head)
        pulling.communicate(timeout=60)
        self.assertEqual(pulling.returncode, 0)
        self.assertTrue((self.home / ".claude/skills/pushed-skill").is_symlink())

    def test_pull_survives_a_git_call_that_hangs_and_says_which(self):
        self.with_remote_one_commit_ahead()
        fake = self.fake_git("status", "exec sleep 30")
        result = self.run_cli("pull", "--quiet", path_prefix=fake)
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertIn("status --porcelain timed out after 5s; main was not updated", result.stdout)

    def test_pull_returns_to_main_only_from_a_branch_whose_remote_was_deleted(self):
        self.with_remote_one_commit_ahead()
        self.git(self.repo, "checkout", "-q", "-b", "new-work")
        kept = self.run_cli("pull", "--quiet")
        self.assertIn("it is on new-work, not main", kept.stdout)
        self.assertEqual(self.git(self.repo, "rev-parse", "--abbrev-ref", "HEAD").stdout.strip(), "new-work")
        (self.repo / "note.md").write_text("x\n")
        self.git(self.repo, "add", "-A")
        self.git(self.repo, "commit", "-qm", "work")
        self.git(self.repo, "-c", "core.hooksPath=/dev/null", "push", "-q", "-u", "origin", "new-work")
        self.git(self.repo, "-c", "core.hooksPath=/dev/null", "push", "-q", "origin", "--delete", "new-work")
        result = self.run_cli("pull", "--quiet")
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertNotIn("stale setup", result.stdout)
        self.assertEqual(self.git(self.repo, "rev-parse", "--abbrev-ref", "HEAD").stdout.strip(), "main")
        self.assertEqual((self.home / ".claude/skills/pushed-skill/SKILL.md").read_text(), "---\nname: pushed-skill\ndescription: x\n---\nx\n")

    def test_check_in_ci_skips_home_vendor_and_builder_context(self):
        shutil.rmtree(self.repo / "tests")
        (self.repo / "tests").mkdir()
        (self.repo / "tests/test_ok.py").write_text(
            "import unittest\nclass Ok(unittest.TestCase):\n    def test_ok(self):\n        self.assertEqual(1, 1)\n"
        )
        result = self.run_cli("check", extra_env={"CI": "true"})
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertIn("CI: skipped home drift and vendored skills.", result.stdout)
        self.assertNotIn("home differs", result.stderr)

    def test_check_in_a_second_checkout_checks_the_repo_not_home(self):
        self.assertEqual(self.run_cli("apply").returncode, 0)
        first = self.repo
        self.repo = self.home / "worktree-of-Kolin-Skills"
        shutil.copytree(first, self.repo)
        shutil.rmtree(self.repo / "tests")
        (self.repo / "tests").mkdir()
        (self.repo / "skills/only-in-worktree").mkdir()
        (self.repo / "skills/only-in-worktree/SKILL.md").write_text("---\nname: only-in-worktree\ndescription: x\n---\nx\n")
        result = self.run_cli("check")
        self.assertIn("home drift was not checked", result.stdout)
        self.assertNotIn("home differs", result.stderr)
        self.assertFalse((self.home / ".claude/skills/only-in-worktree").exists())

    def test_codex_agent_mirror_keeps_backslashes_and_quotes_and_is_read_only_without_write_tools(self):
        body = 'Match \\d+ in C:\\path and say "hi" """ twice.'
        (self.repo / "agents/escape-probe.md").write_text(
            f"---\nname: escape-probe\ndescription: probe\ntools: Read, Grep\n---\n\n{body}\n")
        self.assertEqual(self.run_cli("apply").returncode, 0)
        self.assertEqual((self.home / ".codex/agents/escape-probe.toml").read_text(),
                         'name = "escape-probe"\ndescription = "probe"\nsandbox_mode = "read-only"\n'
                         f"developer_instructions = '''\n{body}\n'''\n")

    def test_every_harness_with_a_shell_tool_runs_the_env_guard_before_it(self):
        self.assertEqual(self.run_cli("apply").returncode, 0)
        claude = json.loads((self.home / ".claude/settings.json").read_text())["hooks"]["PreToolUse"]
        codex = json.loads((self.home / ".codex/hooks.json").read_text())["hooks"]["PreToolUse"]
        for name, entries in [("claude", claude), ("codex", codex)]:
            with self.subTest(harness=name):
                guarded = [entry["matcher"] for entry in entries if "block-env-reads.py" in json.dumps(entry)]
                self.assertTrue(guarded and "Bash" in guarded[0], guarded)
        claude_guarded = next(entry["matcher"] for entry in claude if "block-env-reads.py" in json.dumps(entry))
        self.assertEqual(set(claude_guarded.split("|")), {"Bash", "Read", "Grep", "Glob"})

    def write_skill(self, directory):
        directory.mkdir(parents=True)
        (directory / "SKILL.md").write_text(f"---\nname: {directory.name}\ndescription: x\n---\nx\n")

    def test_a_skill_or_agent_made_in_home_fails_check_until_imported(self):
        self.assertEqual(self.run_cli("apply").returncode, 0)
        skill = self.home / ".claude/skills/made-here"
        self.write_skill(skill)
        agent = self.home / ".claude/agents/made-here.md"
        agent.write_text("---\nname: made-here\ndescription: x\n---\nx\n")
        stray = self.run_cli("apply", "--check")
        self.assertEqual(stray.returncode, 1)
        self.assertIn("~/.claude/skills/made-here", stray.stdout)
        self.assertIn("~/.claude/agents/made-here.md", stray.stdout)
        for path in [skill, agent]:
            imported = self.run_cli("import", str(path))
            self.assertEqual(imported.returncode, 0, imported.stderr)
        self.assertTrue((self.repo / "skills/made-here/SKILL.md").is_file())
        self.assertTrue((self.repo / "agents/made-here.md").is_file())
        self.assertTrue(skill.is_symlink() and agent.is_symlink())
        self.assertEqual(self.run_cli("apply", "--check").returncode, 0)

    def test_importing_an_npx_skill_declares_it_instead_of_copying_it(self):
        installed = self.home / ".agents/skills/from-npx"
        self.write_skill(installed)
        (self.home / ".agents/.skill-lock.json").write_text(
            json.dumps({"skills": {"from-npx": {"source": "someone/skills"}}}))
        self.assertEqual(self.run_cli("apply").returncode, 0)
        self.assertEqual(self.run_cli("apply", "--check").returncode, 1)
        imported = self.run_cli("import", str(installed))
        self.assertEqual(imported.returncode, 0, imported.stderr)
        self.assertEqual(json.loads((self.repo / "upstream/skills.json").read_text()), {"someone/skills": ["from-npx"]})
        self.assertFalse((self.repo / "skills/from-npx").exists())
        self.assertEqual(self.run_cli("apply", "--check").returncode, 0)

    def test_import_refuses_a_name_the_repo_already_has(self):
        self.write_skill(self.home / ".grok/skills/explainer")
        before = (self.repo / "skills/explainer/SKILL.md").read_text()
        self.assertNotEqual(self.run_cli("import", str(self.home / ".grok/skills/explainer")).returncode, 0)
        self.assertEqual((self.repo / "skills/explainer/SKILL.md").read_text(), before)

    def test_import_refuses_a_skill_that_would_shadow_a_vendored_one(self):
        self.write_skill(self.home / ".agents/vendor/cursor-plugins/pstack/skills/tdd")
        self.write_skill(self.home / ".grok/skills/tdd")
        self.assertNotEqual(self.run_cli("import", str(self.home / ".grok/skills/tdd")).returncode, 0)
        self.assertFalse((self.repo / "skills/tdd").exists())

    def test_a_vendor_dropped_from_the_repo_leaves_home_and_pstack_agents_link_in(self):
        pstack = self.home / ".agents/vendor/cursor-plugins/pstack"
        self.write_skill(pstack / "skills/how")
        (pstack / "agents").mkdir(parents=True)
        (pstack / "agents/comment-sicko.md").write_text("---\nname: comment-sicko\ndescription: x\n---\nx\n")
        self.write_skill(self.home / ".agents/vendor/ponytail/skills/ponytail")
        for home in [".agents/skills", ".claude/skills"]:
            link = self.home / home / "ponytail"
            link.parent.mkdir(parents=True, exist_ok=True)
            link.symlink_to(self.home / ".agents/vendor/ponytail/skills/ponytail")
        self.assertEqual(self.run_cli("apply").returncode, 0)
        for home in [".agents/skills", ".claude/skills"]:
            self.assertFalse((self.home / home / "ponytail").is_symlink(), home)
            self.assertEqual((self.home / home / "how").resolve(), (pstack / "skills/how").resolve(), home)
        self.assertEqual((self.home / ".claude/agents/comment-sicko.md").resolve(), (pstack / "agents/comment-sicko.md").resolve())
        self.assertIn('name = "comment-sicko"', (self.home / ".codex/agents/comment-sicko.toml").read_text())
        self.assertEqual(self.run_cli("apply", "--check").returncode, 0)

    def test_a_dropped_npx_skill_is_retired_from_every_home_with_a_backup(self):
        installed = self.home / ".agents/skills/firecrawl"
        self.write_skill(installed)
        link = self.home / ".claude/skills/firecrawl"
        link.parent.mkdir(parents=True, exist_ok=True)
        link.symlink_to("../../.agents/skills/firecrawl")
        self.assertEqual(self.run_cli("apply").returncode, 0)
        self.assertFalse(installed.exists() or link.is_symlink())
        self.assertEqual([path.parent.name for path in (self.home / ".kolin-skills/backup").rglob("SKILL.md")], ["firecrawl"])
        self.assertEqual(self.run_cli("apply", "--check").returncode, 0)

    def test_a_declared_upstream_skill_missing_from_home_fails_check(self):
        (self.repo / "upstream/skills.json").write_text(json.dumps({"someone/skills": ["never-installed"]}))
        self.assertEqual(self.run_cli("apply").returncode, 0)
        result = self.run_cli("apply", "--check")
        self.assertEqual(result.returncode, 1)
        self.assertIn("never-installed", result.stdout)

    def make_upstream(self):
        source = self.home / "upstream-src"
        (source / "skills/pinned").mkdir(parents=True)
        self.git(source, "init", "-q", "-b", "main")
        revisions = []
        for subject in ["first", "second"]:
            (source / "skills/pinned/SKILL.md").write_text(f"---\nname: pinned\ndescription: {subject}\n---\n")
            self.git(source, "add", "-A")
            self.git(source, "commit", "-qm", subject)
            revisions.append(self.git(source, "rev-parse", "HEAD").stdout.strip())
        return source, revisions

    def write_vendor_manifest(self, source, rev):
        manifest = self.repo / "upstream/vendor.json"
        manifest.write_text(json.dumps({"pinned-vendor": {"url": source.as_uri(), "rev": rev}}, indent=2) + "\n")
        return manifest

    def vendor_head(self):
        return self.git(self.home / ".agents/vendor/pinned-vendor", "rev-parse", "HEAD").stdout.strip()

    def test_upstream_bump_moves_the_pin_and_prints_what_changed(self):
        source, (first, second) = self.make_upstream()
        manifest = self.write_vendor_manifest(source, first)
        self.run_cli("upstream")
        self.assertEqual(self.vendor_head(), first)
        result = self.run_cli("upstream", "--bump")
        self.assertEqual(self.vendor_head(), second)
        self.assertEqual(json.loads(manifest.read_text())["pinned-vendor"]["rev"], second)
        self.assertIn("second", result.stdout)
        self.assertIn("SKILL.md", result.stdout)

    def test_a_vendor_clone_off_its_pin_fails_check(self):
        source, (first, second) = self.make_upstream()
        self.write_vendor_manifest(source, first)
        self.run_cli("upstream")
        self.git(self.home / ".agents/vendor/pinned-vendor", "checkout", "-q", "--detach", second)
        result = self.run_cli("apply", "--check")
        self.assertEqual(result.returncode, 1)
        self.assertIn("pinned-vendor", result.stdout)

    def test_installs_owned_by_other_tools_stay_and_dangling_links_go(self):
        self.write_skill(self.home / ".claude/skills/reverse-engineer-anything")
        (self.home / ".claude/skills/.trash").mkdir()
        herdr = self.home / ".codex/hooks/herdr-agent-state.sh"
        herdr.parent.mkdir(parents=True)
        herdr.write_text("x\n")
        dangling = self.home / ".grok/skills/gone"
        dangling.parent.mkdir(parents=True)
        dangling.symlink_to("../../.agents/skills/gone")
        self.assertEqual(self.run_cli("apply").returncode, 0)
        self.assertFalse(dangling.is_symlink())
        self.assertTrue(herdr.is_file())
        self.assertEqual(self.run_cli("apply", "--check").returncode, 0)

    def test_check_reports_drift_without_touching_home(self):
        result = self.run_cli("apply", "--check")
        self.assertEqual(result.returncode, 1)
        self.assertIn(".codex/AGENTS.md", result.stdout)
        self.assertFalse((self.home / ".codex").exists())


if __name__ == "__main__":
    unittest.main()

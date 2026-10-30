import json
import os
import pathlib
import re
import shutil
import subprocess
import sys
import tempfile
import unittest

REPO = pathlib.Path(__file__).resolve().parent.parent
POLICY_LINE = "For code work beyond a one-line change, load poteto-mode with the Skill tool before editing."
PSTACK_SKILLS = "cursor-plugins/pstack/skills"
LOCKED_FRONTMATTER = "---\nname: {name}\ndescription: test {name}\ndisable-model-invocation: true\nicon: crown\n---\n\n# {name}\n"
SELF_INVOKING = ["poteto-mode", "how", "architect", "tdd", "interrogate", "correct", "principle-fix-root-causes", "principle-prove-it-works"]
USER_ONLY = ["swarm", "reflect"]


def has_model_lock(skill_file):
    head = skill_file.read_text().split("---\n")[1]
    return any(line.partition(":")[0].strip() == "disable-model-invocation" for line in head.splitlines())


class SelfInvokeCase(unittest.TestCase):
    def setUp(self):
        self.home = pathlib.Path(tempfile.mkdtemp()).resolve()
        self.addCleanup(shutil.rmtree, self.home)
        self.repo = self.home / "Kolin-Skills"
        shutil.copytree(REPO, self.repo, ignore=shutil.ignore_patterns(".git", "__pycache__"))
        (self.repo / "upstream/skills.json").write_text("{}\n")
        self.vendor = self.home / ".agents/vendor" / PSTACK_SKILLS
        for name in SELF_INVOKING + USER_ONLY:
            skill = self.vendor / name
            (skill / "references").mkdir(parents=True)
            (skill / "SKILL.md").write_text(LOCKED_FRONTMATTER.format(name=name))
            (skill / "references/guide.md").write_text(f"guide of {name}\n")

    def run_cli(self, *args, extra_env=None):
        env = {key: value for key, value in os.environ.items() if key != "CI"}
        env["HOME"] = str(self.home)
        env.update(extra_env or {})
        return subprocess.run([sys.executable, str(self.repo / "bin/kolin-skills"), *args],
                              env=env, text=True, capture_output=True, timeout=60)

    def apply(self):
        result = self.run_cli("apply")
        self.assertEqual(result.returncode, 0, result.stderr + result.stdout)


class ApplySelfInvokeTests(SelfInvokeCase):
    def test_apply_links_the_allowlisted_pstack_skills_without_the_model_lock(self):
        self.apply()
        for home in [".agents/skills", ".claude/skills"]:
            for name in SELF_INVOKING:
                with self.subTest(home=home, skill=name):
                    skill_file = self.home / home / name / "SKILL.md"
                    self.assertEqual(skill_file.read_text(), f"---\nname: {name}\ndescription: test {name}\nicon: crown\n---\n\n# {name}\n")
                    self.assertEqual((self.home / home / name / "references/guide.md").read_text(), f"guide of {name}\n")

    def test_apply_leaves_every_other_pstack_skill_and_the_vendor_files_locked(self):
        self.apply()
        for name in USER_ONLY:
            with self.subTest(skill=name):
                linked = self.home / ".claude/skills" / name / "SKILL.md"
                self.assertTrue(has_model_lock(linked))
                self.assertEqual((self.home / ".claude/skills" / name).resolve(), (self.vendor / name).resolve())
        for name in SELF_INVOKING:
            with self.subTest(vendor=name):
                self.assertEqual((self.vendor / name / "SKILL.md").read_text(), LOCKED_FRONTMATTER.format(name=name))

    def test_a_derived_skill_still_reaches_its_sibling_skills_by_relative_path(self):
        self.apply()
        for home in [".agents/skills", ".claude/skills"]:
            with self.subTest(home=home):
                poteto = self.home / home / "poteto-mode"
                self.assertEqual((poteto / "../how/SKILL.md").read_text().splitlines()[1], "name: how")
                self.assertEqual((poteto / "../swarm/SKILL.md").read_text().splitlines()[1], "name: swarm")

    def test_apply_stays_idempotent_and_follows_an_upstream_change_to_the_skill(self):
        self.apply()
        again = self.run_cli("apply")
        self.assertEqual((again.returncode, again.stdout), (0, "already in sync\n"))
        (self.vendor / "how/SKILL.md").write_text(LOCKED_FRONTMATTER.format(name="how") + "\nnew upstream section\n")
        self.apply()
        linked = (self.home / ".claude/skills/how/SKILL.md").read_text()
        self.assertTrue(linked.endswith("\nnew upstream section\n"))
        self.assertNotIn("disable-model-invocation", linked)

    def test_an_allowlisted_skill_that_upstream_dropped_is_unlinked(self):
        self.apply()
        shutil.rmtree(self.vendor / "tdd")
        self.apply()
        for home in [".agents/skills", ".claude/skills"]:
            self.assertFalse((self.home / home / "tdd").is_symlink(), home)
        self.assertEqual(self.run_cli("apply", "--check").returncode, 0)


class PolicyLineTests(SelfInvokeCase):
    def test_every_harness_policy_tells_the_agent_to_load_poteto_mode_with_the_skill_tool(self):
        self.apply()
        for relative in [".claude/CLAUDE.md", ".codex/AGENTS.md", ".grok/AGENTS.md"]:
            with self.subTest(policy=relative):
                self.assertIn(f"\n{POLICY_LINE}\n", (self.home / relative).read_text())


class QuickCheckTests(SelfInvokeCase):
    def failures(self, result):
        return [line for line in result.stderr.splitlines() if line.startswith("FAIL:")]

    def test_a_fresh_install_passes_the_quick_check_and_reports_how_long_it_took(self):
        self.apply()
        result = self.run_cli("check", "--quick")
        self.assertEqual((result.returncode, result.stderr), (0, ""))
        self.assertRegex(result.stdout.strip(), r"^Passed: quick check, links, hooks, policy and self-invoking skills, in \d+\.\d{2}s$")

    def test_a_pstack_skill_linked_with_its_model_lock_fails_the_quick_check(self):
        self.apply()
        agents_link = self.home / ".agents/skills/poteto-mode"
        agents_link.unlink()
        agents_link.symlink_to(self.vendor / "poteto-mode")
        result = self.run_cli("check", "--quick")
        self.assertEqual(result.returncode, 1)
        self.assertIn(f"FAIL: ~/.agents/skills/poteto-mode/SKILL.md sets disable-model-invocation, so the agent cannot start it; run kolin-skills apply", self.failures(result))

    def test_a_missing_allowlisted_skill_fails_the_quick_check(self):
        self.apply()
        shutil.rmtree(self.vendor / "poteto-mode")
        self.apply()
        result = self.run_cli("check", "--quick")
        self.assertEqual(result.returncode, 1)
        self.assertIn("FAIL: ~/.agents/skills/poteto-mode is not installed; run kolin-skills upstream", self.failures(result))

    def test_an_unlinked_policy_and_unwired_hooks_fail_the_quick_check_with_the_fix_for_each(self):
        self.apply()
        (self.home / ".claude/CLAUDE.md").unlink()
        (self.home / ".claude/settings.json").unlink()
        result = self.run_cli("check", "--quick")
        self.assertEqual(result.returncode, 1)
        self.assertIn(f"link ~/.claude/CLAUDE.md -> {self.repo}/policy/AGENTS.md", result.stdout)
        self.assertIn("write ~/.claude/settings.json", result.stdout)
        self.assertEqual(self.failures(result), ["FAIL: home differs from the repo; fix each line above"])

    def test_a_dangling_skill_link_fails_the_quick_check(self):
        self.apply()
        (self.home / ".claude/skills/gone").symlink_to(self.home / "nowhere")
        result = self.run_cli("check", "--quick")
        self.assertEqual(result.returncode, 1)
        self.assertIn(f"FAIL: ~/.claude/skills/gone links to {self.home}/nowhere, which does not exist; run kolin-skills apply", self.failures(result))

    def test_a_home_that_was_never_installed_fails_the_quick_check(self):
        result = self.run_cli("check", "--quick")
        self.assertEqual(result.returncode, 1)
        self.assertIn("FAIL: home is not wired to any checkout; run kolin-skills install", self.failures(result))

    def test_a_home_wired_to_another_checkout_fails_the_quick_check(self):
        self.apply()
        other = self.home / "other-clone"
        shutil.copytree(self.repo, other)
        result = subprocess.run([sys.executable, str(other / "bin/kolin-skills"), "check", "--quick"],
                                env={**os.environ, "HOME": str(self.home)}, text=True, capture_output=True, timeout=60)
        self.assertEqual(result.returncode, 1)
        self.assertIn(f"FAIL: home is wired to {self.repo}, not this checkout ({other}); run kolin-skills apply --adopt", self.failures(result))


class InstallForAgentsReadmeTests(unittest.TestCase):
    def section(self):
        text = (REPO / "README.md").read_text()
        match = re.search(r"^## Install \(for agents\)\n(.*?)(?=^## )", text, re.S | re.M)
        self.assertIsNotNone(match, "README.md has no '## Install (for agents)' section")
        return match.group(1)

    def commands(self):
        block = re.search(r"```sh\n(.*?)```", self.section(), re.S)
        self.assertIsNotNone(block, "the section has no sh block")
        return [line for line in block.group(1).splitlines() if line.strip() and not line.startswith("#")]

    def test_the_section_walks_an_agent_from_prerequisites_to_a_new_session_without_a_hardcoded_path(self):
        commands = self.commands()
        order = [
            next(i for i, c in enumerate(commands) if "jq" in c and "command -v" in c),
            next(i for i, c in enumerate(commands) if "sys.version_info" in c and "(3, 9)" in c),
            next(i for i, c in enumerate(commands) if "node" in c and "22" in c and "20" in c and "versions" in c),
            next(i for i, c in enumerate(commands) if c.startswith("git clone")),
            next(i for i, c in enumerate(commands) if re.search(r'python3 "\$[A-Z_]+/bin/kolin-skills" install$', c)),
            next(i for i, c in enumerate(commands) if c == 'export PATH="$HOME/.local/bin:$PATH"'),
            next(i for i, c in enumerate(commands) if c == "kolin-skills check --quick"),
        ]
        self.assertEqual(order, sorted(order))
        self.assertRegex(self.section(), r"(?i)start a new session")
        self.assertNotRegex("\n".join(commands), r"/Users/|/home/")

    def test_every_kolin_skills_command_in_the_section_is_accepted_by_the_cli(self):
        for command in self.commands():
            match = re.search(r"kolin-skills (\w[\w-]*)((?: --[\w-]+)*)$", command)
            if not match:
                continue
            subcommand, flags = match.group(1), match.group(2).split()
            helped = subprocess.run([sys.executable, str(REPO / "bin/kolin-skills"), subcommand, "--help"], text=True, capture_output=True, timeout=30)
            self.assertEqual(helped.returncode, 0, command)
            for flag in flags:
                self.assertIn(flag, helped.stdout, command)


if __name__ == "__main__":
    unittest.main()

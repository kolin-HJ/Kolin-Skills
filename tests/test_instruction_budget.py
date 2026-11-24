import json
import pathlib
import unittest

REPO = pathlib.Path(__file__).resolve().parent.parent
POLICY_MAX_BYTES = 2048
PSTACK_LOCAL_MAX_BYTES = 1024


class InstructionBudgetTests(unittest.TestCase):
    def test_policy_fits_the_byte_budget(self):
        size = (REPO / "policy/AGENTS.md").stat().st_size
        self.assertLessEqual(size, POLICY_MAX_BYTES, f"policy/AGENTS.md is {size} bytes")

    def test_pstack_local_fits_the_byte_budget_and_has_no_models_file(self):
        size = (REPO / "skills/pstack-local/SKILL.md").stat().st_size
        self.assertLessEqual(size, PSTACK_LOCAL_MAX_BYTES, f"skills/pstack-local/SKILL.md is {size} bytes")
        self.assertFalse((REPO / "skills/pstack-local/models.md").exists())

    def test_judge_is_gone_and_the_reviewer_names_net_lines(self):
        self.assertFalse((REPO / "agents/judge.md").exists())
        text = (REPO / "agents/senior-reviewer.md").read_text()
        self.assertIn("net", text.lower())
        self.assertRegex(text, r"(?i)one thing to delete|name one .*delete")

    def test_mattpocock_skills_are_not_in_the_default_manifest(self):
        manifest = json.loads((REPO / "upstream/skills.json").read_text())
        self.assertNotIn("mattpocock/skills", manifest)
        self.assertNotIn("heygen-com/hyperframes", manifest)

    def test_media_profile_declares_the_seven_hyperframes_skills(self):
        profiles = json.loads((REPO / "upstream/profiles.json").read_text())
        skills = profiles["media"]["heygen-com/hyperframes"]
        self.assertEqual(len(skills), 7)
        self.assertIn("hyperframes", skills)

    def test_precedence_is_only_in_the_policy(self):
        policy = (REPO / "policy/AGENTS.md").read_text()
        self.assertIn("Rank:", policy)
        self.assertNotIn("outrank", (REPO / "cursor/agent-policy.mdc").read_text())
        self.assertNotRegex((REPO / "README.md").read_text(), r"(?i)constitution")

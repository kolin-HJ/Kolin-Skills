import pathlib
import unittest


REPO = pathlib.Path(__file__).resolve().parent.parent
POLICY = (REPO / "policy/AGENTS.md").read_text()
PSTACK_LOCAL = (REPO / "skills/pstack-local/SKILL.md").read_text()
EXPLAINER = (REPO / "skills/explainer/SKILL.md").read_text()
STE = (REPO / "claude/output-styles/ste-visual.md").read_text()


def section(text, heading, stop):
    start = text.index(heading)
    end = text.index(stop, start + 1)
    return text[start:end]


def frontmatter(text):
    return text.split("---", 2)[1]


class ExplainShapeTests(unittest.TestCase):
    def test_policy_writing_keeps_unslop_and_bans_ascii_art(self):
        writing = section(POLICY, "## Writing", "## Adding rules")
        self.assertIn("`unslop`", writing)
        self.assertIn("ASD-STE100", writing)
        self.assertRegex(writing, r"80%")
        self.assertRegex(writing, r"numbered steps")
        self.assertRegex(writing, r"never as ASCII art")

    def test_pstack_local_routes_explain_how_and_walkthrough_to_teach_and_keeps_visualize(self):
        meta = frontmatter(PSTACK_LOCAL)
        self.assertIn("teach", meta)
        self.assertRegex(meta, r"(?i)explain")
        self.assertRegex(meta, r"(?i)walk through|walk-through|walkthrough")
        self.assertIn("`teach`", PSTACK_LOCAL)
        self.assertRegex(PSTACK_LOCAL, r"(?i)walk me through")
        self.assertRegex(PSTACK_LOCAL, r"`?/?how`?")
        self.assertIn("/visualize", PSTACK_LOCAL)

    def test_explainer_uses_the_hard_shape_and_stays_asked_only(self):
        meta = frontmatter(EXPLAINER)
        self.assertRegex(meta, r"(?i)only when|Use only when")
        self.assertRegex(meta, r"Never|unasked")
        self.assertIn("teach", meta)
        self.assertRegex(EXPLAINER, r"(?i)one-sentence answer first")
        self.assertRegex(EXPLAINER, r"7 nodes|at most 7")
        self.assertRegex(EXPLAINER, r"3 short beats|at most 3")
        self.assertRegex(EXPLAINER, r"No table|no table")
        self.assertNotIn("What the page holds, in this order", EXPLAINER)

    def test_ste_visual_uses_plain_steps_and_no_ascii_art(self):
        self.assertRegex(STE, r"(?i)first line is the answer")
        self.assertRegex(STE, r"numbered list")
        self.assertRegex(STE, r"Never draw ASCII art")
        self.assertRegex(STE, r"No table|no table")
        self.assertRegex(STE, r"only after a yes")


if __name__ == "__main__":
    unittest.main()

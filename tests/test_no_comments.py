import pathlib
import re
import subprocess
import tempfile
import unittest

REPO = pathlib.Path(__file__).resolve().parent.parent
HASH_COMMENT = re.compile(r"^\s*#(?!!)")
SLASH_COMMENT = re.compile(r"^\s*(//|/\*)")
GATE_DIRECTIVE = re.compile(r"((eslint|oxlint)-disable\S*|@ts-expect-error) .*-- \S")
STYLE_BY_SUFFIX = {".py": HASH_COMMENT, ".sh": HASH_COMMENT, ".mjs": SLASH_COMMENT, ".js": SLASH_COMMENT, ".ts": SLASH_COMMENT, ".tsx": SLASH_COMMENT}


def comment_style(path):
    if path.suffix in STYLE_BY_SUFFIX:
        return STYLE_BY_SUFFIX[path.suffix]
    if not path.suffix and path.read_bytes().startswith(b"#!"):
        return HASH_COMMENT
    return None


def comment_lines(path):
    style = comment_style(path)
    if style is None:
        return []
    return [number for number, line in enumerate(path.read_text().splitlines(), 1)
            if style.match(line) and not GATE_DIRECTIVE.search(line)]


class NoCommentsTests(unittest.TestCase):
    def test_tracked_code_carries_no_comments(self):
        tracked = subprocess.run(["git", "-C", str(REPO), "ls-files"], text=True, capture_output=True).stdout.split()
        files = [REPO / name for name in tracked if (REPO / name).is_file()]
        found = [f"{path.relative_to(REPO)}:{number}" for path in files for number in comment_lines(path)]
        self.assertEqual(found, [], "move each reason into a name, a test or the PR body (policy: No comments)")

    def test_a_comment_line_is_found_and_a_shebang_or_gate_directive_with_a_reason_is_not(self):
        with tempfile.TemporaryDirectory() as directory:
            python = pathlib.Path(directory) / "probe.py"
            python.write_text("#!/usr/bin/env python3\nx = 1  # trailing is out of scope\n# a comment\n")
            typescript = pathlib.Path(directory) / "probe.ts"
            typescript.write_text("// eslint-disable-next-line no-console -- the CLI prints\n// @ts-expect-error\n")
            self.assertEqual((comment_lines(python), comment_lines(typescript)), ([3], [2]))

if __name__ == "__main__":
    unittest.main()

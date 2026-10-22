import pathlib
import subprocess
import sys
import tempfile
import unittest


PR_BODY = pathlib.Path(__file__).resolve().parent.parent / "skills/pstack-local/scripts/pr-body"


class PrBodyTests(unittest.TestCase):
    def setUp(self):
        self.repo = pathlib.Path(tempfile.mkdtemp())
        self.git("init", "-q", "-b", "main")
        self.write("src/price.ts", "export const price = 1;\n")
        self.git("add", "-A")
        self.git("commit", "-qm", "base")
        self.git("checkout", "-qb", "work")

    def git(self, *args):
        subprocess.run(["git", "-C", str(self.repo), "-c", "user.email=t@t", "-c", "user.name=t", *args],
                       check=True, capture_output=True)

    def write(self, relative, text):
        path = self.repo / relative
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(text)

    def body(self):
        self.git("add", "-A")
        self.git("commit", "-qm", "work")
        result = subprocess.run([sys.executable, str(PR_BODY), "main"], cwd=self.repo,
                                text=True, capture_output=True, timeout=20)
        self.assertEqual(result.returncode, 0, result.stderr)
        return result.stdout

    def test_each_file_lands_in_its_group_with_its_line_counts_and_no_code(self):
        self.write("src/price.ts", "export const price = 2;\n")
        self.write("src/price.test.ts", "it('prices', () => {});\n")
        self.write("README.md", "Run it with `pr-body`.\n```sh\npr-body main\n```\n")
        self.write("docs/café.md", "Prix\n")
        self.write("docs/a.md", "plain\n")
        self.write("package-lock.json", "{}\n")
        body = self.body()
        self.assertIn("| Code | 2 | +1 -1 |\n| Tests | 1 | +1 -0 |\n| Docs | 3 | +6 -0 |", body)
        self.assertIn(
            "<summary>Code: 2 files, +1 -1</summary>\n\n"
            "- `package-lock.json` +1 -0, lockfile\n"
            "- `src/price.ts` +1 -1\n\n</details>", body)
        self.assertIn(
            "<summary>Docs: 3 files, +6 -0</summary>\n\n"
            "- `README.md` +4 -0\n- `docs/a.md` +1 -0\n- `docs/café.md` +1 -0\n\n</details>", body)
        self.assertNotIn("```diff", body)
        self.assertNotIn("export const price", body)

    def test_many_files_keep_every_group_and_stay_under_the_github_limit(self):
        for n in range(2_500):
            self.write(f"src/f{n:04}.ts", f"export const a{n} = 1;\n")
        self.write("tests/test_t.py", "assert 1\n")
        self.write("docs/d.md", "doc\n")
        body = self.body()
        self.assertRegex(body, r"- Not shown: \d+ files, see Files changed\n\n</details>\n\n<details>\n<summary>Tests")
        self.assertIn("<summary>Tests: 1 file, +1 -0</summary>\n\n- `tests/test_t.py` +1 -0", body)
        self.assertIn("<summary>Docs: 1 file, +1 -0</summary>\n\n- `docs/d.md` +1 -0", body)
        self.assertLess(len(body), 65_536 - 8_000)


if __name__ == "__main__":
    unittest.main()

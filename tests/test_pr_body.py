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

    def test_each_file_lands_in_its_group_with_its_diff(self):
        self.write("src/price.ts", "export const price = 2;\n")
        self.write("src/price.test.ts", "it('prices', () => {});\n")
        self.write("README.md", "Run it with `pr-body`.\n```sh\npr-body main\n```\n")
        self.write("docs/café.md", "Prix\n")
        self.write("docs/[a].md", "bracket\n")
        self.write("docs/a.md", "plain\n")
        self.write("package-lock.json", "{}\n")
        body = self.body()
        self.assertIn("| Code | 2 | +1 -1 |\n| Tests | 1 | +1 -0 |\n| Docs | 4 | +7 -0 |", body)
        self.assertIn("<summary>Code: 2 files, +1 -1</summary>", body)
        self.assertIn("`package-lock.json` +1 -0: lockfile", body)
        self.assertIn("-export const price = 1;\n+export const price = 2;", body)
        self.assertIn("````diff\n", body)
        self.assertIn("`docs/café.md` +1 -0\n\n```diff\n", body)
        self.assertIn("+Prix", body)
        self.assertEqual(body.count("+plain"), 1)

    def test_a_diff_past_the_github_limit_is_named_but_not_inlined(self):
        self.write("src/small.ts", "export const small = 1;\n")
        self.write("src/huge.ts", "".join(f"export const v{n} = {n};\n" for n in range(5_000)))
        body = self.body()
        self.assertIn("`src/huge.ts` +5000 -0: diff not inlined, see Files changed", body)
        self.assertIn("+export const small = 1;", body)
        self.assertLess(len(body), 65_536 - 8_000)

    def test_many_files_keep_every_group_and_stay_under_the_github_limit(self):
        for n in range(1_200):
            self.write(f"src/f{n:04}.ts", f"export const a{n} = 1;\n")
        self.write("tests/test_t.py", "assert 1\n")
        self.write("docs/d.md", "doc\n")
        body = self.body()
        self.assertRegex(body, r"Not shown: \d+ files, see Files changed\n\n</details>\n\n<details>\n<summary>Tests")
        self.assertIn("<summary>Tests: 1 file, +1 -0</summary>\n\n`tests/test_t.py` +1 -0", body)
        self.assertIn("<summary>Docs: 1 file, +1 -0</summary>\n\n`docs/d.md` +1 -0", body)
        self.assertLess(len(body), 65_536 - 8_000)


if __name__ == "__main__":
    unittest.main()

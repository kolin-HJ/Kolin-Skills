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
        self.write("package-lock.json", "{}\n")
        body = self.body()
        self.assertIn("| Code | 2 | +2 -1 |\n| Tests | 1 | +1 -0 |\n| Docs | 1 | +4 -0 |", body)
        self.assertIn("<summary>Code: 2 files, +2 -1</summary>", body)
        self.assertIn("`package-lock.json` +1 -0: lockfile, diff not shown", body)
        self.assertIn("-export const price = 1;\n+export const price = 2;", body)
        self.assertIn("````diff\n", body)
        self.assertIn("## Review this", body)

    def test_a_diff_past_the_github_limit_is_named_but_not_inlined(self):
        self.write("src/small.ts", "export const small = 1;\n")
        self.write("src/huge.ts", "".join(f"export const v{n} = {n};\n" for n in range(5_000)))
        body = self.body()
        self.assertIn("`src/huge.ts` +5000 -0: too large for the PR body, see Files changed", body)
        self.assertIn("+export const small = 1;", body)
        self.assertLess(len(body), 65_536)


if __name__ == "__main__":
    unittest.main()

import pathlib
import subprocess
import sys
import tempfile
import unittest


PR_BODY = pathlib.Path(__file__).resolve().parent.parent / "bin/pr-body"


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

    def run_pr_body(self, *features):
        self.git("add", "-A")
        self.git("commit", "-qm", "work")
        flags = [arg for feature in features for arg in ("--feature", feature)]
        return subprocess.run([sys.executable, str(PR_BODY), "main", *flags], cwd=self.repo,
                              text=True, capture_output=True, timeout=20)

    def body(self, *features):
        result = self.run_pr_body(*features)
        self.assertEqual(result.returncode, 0, result.stderr)
        return result.stdout

    def test_each_feature_lists_its_files_and_counts_and_the_rest_goes_to_other(self):
        self.write("src/price.ts", "export const price = 2;\n")
        self.write("src/price.test.ts", "it('prices', () => {});\n")
        self.write("docs/price.md", "Prix\n")
        self.write("README.md", "Run it.\n")
        self.write("package-lock.json", "{}\n")
        (self.repo / "img.png").write_bytes(b"\x00\x01\x02")
        body = self.body("Pricing=src/price.ts,src/price.test.ts,docs/")
        self.assertRegex(body, r"(?m)^- \*\*Pricing:\*\* .*`3 files · code \+1 -1 · tests \+1 -0 · docs \+1 -0`$")
        self.assertRegex(body, r"(?m)^- \*\*Other:\*\* .*`3 files · docs \+1 -0`$")
        self.assertIn(
            "**Pricing**\n"
            "- `docs/price.md` +1 -0\n"
            "- `src/price.test.ts` +1 -0\n"
            "- `src/price.ts` +1 -1\n\n"
            "**Other**\n"
            "- `README.md` +1 -0\n"
            "- `img.png` binary\n"
            "- `package-lock.json` +1 -0, lockfile\n", body)

    def test_a_body_without_a_feature_fails(self):
        self.write("src/price.ts", "export const price = 2;\n")
        result = self.run_pr_body()
        self.assertNotEqual(result.returncode, 0)
        self.assertIn("--feature", result.stderr)

    def test_a_feature_path_that_matches_no_changed_file_fails(self):
        self.write("src/price.ts", "export const price = 2;\n")
        result = self.run_pr_body("Pricing=src/prices.ts")
        self.assertNotEqual(result.returncode, 0)
        self.assertIn("src/prices.ts", result.stderr)

    def test_a_file_in_two_features_fails(self):
        self.write("src/price.ts", "export const price = 2;\n")
        result = self.run_pr_body("Pricing=src/", "Checkout=src/price.ts")
        self.assertNotEqual(result.returncode, 0)
        self.assertIn("src/price.ts", result.stderr)

    def test_many_files_keep_every_feature_and_stay_under_the_github_limit(self):
        for n in range(2_500):
            self.write(f"src/f{n:04}.ts", f"export const a{n} = 1;\n")
        self.write("tests/test_t.py", "assert 1\n")
        body = self.body("Source=src/", "Checks=tests/")
        self.assertRegex(body, r"(?m)^- \*\*Source:\*\* .*`2500 files · code \+2500 -0`$")
        self.assertRegex(body, r"- Not shown: \d+ files, see Files changed\n\n\*\*Checks\*\*\n- `tests/test_t.py` \+1 -0\n")
        self.assertLess(len(body), 65_536 - 8_000)


if __name__ == "__main__":
    unittest.main()

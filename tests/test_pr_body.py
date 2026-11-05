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

    def test_the_diff_groups_files_by_code_tests_and_docs_and_names_each_feature(self):
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
            "## Diff\n\n"
            "**6 files touched · +4 -1** · 1.0 test lines per code line\n\n"
            "**Code** · 3 files · +1 -1\n"
            "- `img.png` binary · Other\n"
            "- `package-lock.json` +1 -0, lockfile · Other\n"
            "- `src/price.ts` +1 -1 · Pricing\n\n"
            "**Tests** · 1 file · +1 -0\n"
            "- `src/price.test.ts` +1 -0 · Pricing\n\n"
            "**Docs** · 2 files · +2 -0\n"
            "- `README.md` +1 -0 · Other\n"
            "- `docs/price.md` +1 -0 · Pricing\n\n"
            "## Check these\n", body)

    def test_a_single_feature_does_not_repeat_its_name_on_each_file(self):
        self.write("src/price.ts", "export const price = 2;\n")
        self.write("docs/price.md", "Prix\n")
        body = self.body("Pricing=src/,docs/")
        self.assertIn("- `src/price.ts` +1 -1\n", body)
        self.assertIn("- `docs/price.md` +1 -0\n", body)

    def test_a_group_with_no_files_is_left_out(self):
        self.write("src/price.ts", "export const price = 2;\n")
        body = self.body("Pricing=src/")
        self.assertIn("**Code** · 1 file · +1 -1\n", body)
        self.assertNotIn("**Tests**", body)
        self.assertNotIn("**Docs**", body)

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

    def test_many_files_keep_every_group_and_stay_under_the_github_limit(self):
        for n in range(2_500):
            self.write(f"src/f{n:04}.ts", f"export const a{n} = 1;\n")
        self.write("tests/test_t.py", "assert 1\n")
        body = self.body("Source=src/", "Checks=tests/")
        self.assertRegex(body, r"(?m)^- \*\*Source:\*\* .*`2500 files · code \+2500 -0`$")
        self.assertRegex(body, r"- Not shown: \d+ files, see Files changed\n\n\*\*Tests\*\* · 1 file · \+1 -0\n- `tests/test_t.py` \+1 -0 · Checks\n")
        self.assertLess(len(body), 65_536 - 8_000)


if __name__ == "__main__":
    unittest.main()

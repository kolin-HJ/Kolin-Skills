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

    def render(self):
        result = subprocess.run([sys.executable, str(PR_BODY), "main"], cwd=self.repo,
                                text=True, capture_output=True, timeout=60)
        self.assertEqual(result.returncode, 0, result.stderr)
        return result.stdout

    def body(self):
        self.git("add", "-A")
        self.git("commit", "-qm", "work")
        return self.render()

    def test_each_file_lands_in_its_group_with_its_line_counts_and_no_code(self):
        self.write("src/price.ts", "export const price = 2;\n")
        self.write("src/price.test.ts", "it('prices', () => {});\n")
        self.write("README.md", "Run it with `pr-body`.\n```sh\npr-body main\n```\n")
        self.write("docs/café.md", "Prix\n")
        self.write("docs/a.md", "plain\n")
        self.write("package-lock.json", "{}\n")
        self.write("src/a|b.ts", "x\n")
        body = self.body()
        self.assertTrue(body.endswith(
            "## Diff\n\n"
            "| Group / file | Lines |\n|---|---|\n"
            "| **Code** · 3 files | **+2 -1** |\n"
            "| &emsp;`package-lock.json` | +1 -0, lockfile |\n"
            "| &emsp;`src/a\\|b.ts` | +1 -0 |\n"
            "| &emsp;`src/price.ts` | +1 -1 |\n"
            "| **Tests** · 1 file | **+1 -0** |\n"
            "| &emsp;`src/price.test.ts` | +1 -0 |\n"
            "| **Docs** · 3 files | **+6 -0** |\n"
            "| &emsp;`README.md` | +4 -0 |\n"
            "| &emsp;`docs/a.md` | +1 -0 |\n"
            "| &emsp;`docs/café.md` | +1 -0 |\n"), body)

    def test_release_reports_each_pr_and_direct_commit(self):
        self.git("checkout", "-qb", "feature")
        self.write("src/feature.py", "one\ntwo\n")
        self.write("tests/test_feature.py", "assert True\n")
        self.git("add", "-A")
        self.git("commit", "-qm", "feature")
        self.git("checkout", "-q", "work")
        self.git("merge", "--no-ff", "feature", "-m", "Merge pull request #11 from team/feature\n\nAdd feature")
        self.write("docs/guide.md", "guide\n")
        self.git("add", "-A")
        self.git("commit", "-qm", "Write guide (#12)")
        self.write("src/direct.py", "direct\n")
        self.git("add", "-A")
        self.git("commit", "-qm", "direct")
        body = self.render()
        self.assertIn("| #11 Add feature | +2 -0 | +1 -0 | +0 -0 | 2 |", body)
        self.assertIn("| #12 Write guide | +0 -0 | +0 -0 | +1 -0 | 1 |", body)
        self.assertIn("| Direct commits | +1 -0 | +0 -0 | +0 -0 | 1 |", body)
        for title, path in (("#11 Add feature", "src/feature.py"), ("#12 Write guide", "docs/guide.md"),
                            ("Direct commits", "src/direct.py")):
            block = body.split(f"<summary>{title} ·", 1)[1].split("</details>", 1)[0]
            self.assertIn(f"`{path}` |", block)

    def test_feature_branch_has_no_pr_section_and_verification_names_head(self):
        self.write("src/feature.py", "feature\n")
        body = self.body()
        head = subprocess.check_output(["git", "-C", str(self.repo), "rev-parse", "--short", "HEAD"], text=True).strip()
        self.assertNotIn("## PRs", body)
        self.assertIn(f"- Ran: `<command>` at `{head}`: <result>", body)
        self.assertIn(f"- Reviewed: <senior-reviewer or interrogate> at `{head}`: <verdict>", body)

    def test_large_release_keeps_all_pr_rows_under_budget(self):
        for n in range(3):
            for i in range(800):
                self.write(f"src/pr{n}/file{i:04}.py", "value = 1\n")
            self.git("add", "-A")
            self.git("commit", "-qm", f"Feature {n} (#{n + 1})")
        body = self.render()
        for n in range(3):
            self.assertIn(f"| #{n + 1} Feature {n} | +800 -0 |", body)
        self.assertIn("Not shown:", body)
        self.assertLess(len(body), 65_536 - 8_000)

    def test_many_files_keep_every_group_and_stay_under_the_github_limit(self):
        for n in range(2_500):
            self.write(f"src/f{n:04}.ts", f"export const a{n} = 1;\n")
        self.write("tests/test_t.py", "assert 1\n")
        body = self.body()
        self.assertIn("| **Code** · 2500 files | **+2500 -0** |", body)
        self.assertRegex(body, r"\| &emsp;Not shown: \d+ files, see Files changed \| \|\n\| \*\*Tests\*\*")
        self.assertIn("| **Tests** · 1 file | **+1 -0** |\n| &emsp;`tests/test_t.py` | +1 -0 |", body)
        self.assertTrue(body.endswith("| **Docs** · 0 files | **+0 -0** |\n"), body[-200:])
        self.assertLess(len(body), 65_536 - 8_000)


if __name__ == "__main__":
    unittest.main()

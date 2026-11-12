import json
import pathlib
import shutil
import subprocess
import sys
import tempfile
import unittest

CLI = pathlib.Path(__file__).resolve().parent.parent / "bin/feature-budget"


class FeatureBudgetTests(unittest.TestCase):
    def setUp(self):
        self.root = pathlib.Path(tempfile.mkdtemp())
        self.addCleanup(shutil.rmtree, self.root)

    def write(self, relative, text):
        path = self.root / relative
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(text)
        return path

    def source(self, relative, lines, imports=()):
        rows = [f"import x from '{spec}'" for spec in imports]
        n = 0
        while len(rows) < lines:
            rows.append(f"export const n{n} = {n}")
            n += 1
        self.write(relative, "\n".join(rows[:lines]) + "\n")

    def run_cli(self, *args):
        return subprocess.run([sys.executable, str(CLI), str(self.root), *args],
                              text=True, capture_output=True, timeout=20)

    def git(self, *args):
        subprocess.run(["git", "-C", str(self.root), "-c", "user.name=t", "-c", "user.email=t@example.com",
                        "-c", "commit.gpgsign=false", *args], check=True, capture_output=True)

    def commit_all(self, message):
        self.git("add", "-A")
        self.git("commit", "-q", "--no-verify", "-m", message)

    def test_counts_source_files_and_lines_and_skips_tests(self):
        for name in ("a", "b", "c"):
            self.source(f"src/features/otif/{name}.ts", 10)
        self.source("src/features/otif/otif.test.ts", 200)
        self.source("node_modules/features/fake/x.ts", 10)
        result = self.run_cli()
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertIn("files=3 lines=30 budget=5/800 (read)  ok", result.stdout)
        self.assertNotIn("files=4", result.stdout)
        self.assertIn("(repo-standard, Layout)", result.stdout)

    def test_over_budget_fails_review_and_double_stops_the_wave_without_failing(self):
        for n in range(6):
            self.source(f"src/features/wide/{n}.ts", 1)
        for n in range(11):
            self.source(f"src/features/huge/{n}.ts", 1)
        result = self.run_cli()
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertIn("wide  files=6 lines=6 budget=5/800 (read)  over — fails review", result.stdout)
        self.assertIn("huge  files=11 lines=11 budget=5/800 (read)  2x — wave stops until Kolin approves a new budget (repo-standard, Layout)", result.stdout)

    def test_reads_budgets_from_the_plan_and_falls_back_to_kind_defaults(self):
        self.write(".pstack/feature-budgets.json", json.dumps({"features": {
            "custom": {"files": 2, "lines": 40},
            "form": {"kind": "edit"},
        }}))
        for n in range(3):
            self.source(f"src/features/custom/{n}.ts", 1)
        for n in range(7):
            self.source(f"src/features/form/{n}.ts", 1)
        result = self.run_cli()
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertIn("custom  files=3 lines=3 budget=2/40 (plan)  over — fails review", result.stdout)
        self.assertIn("form  files=7 lines=7 budget=7/1200 (edit)  ok", result.stdout)

    def test_a_tree_with_no_feature_folder_reports_zero_and_exits_0(self):
        self.source("src/lib/util.ts", 10)
        result = self.run_cli()
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertIn("0 features (report-only)", result.stdout)
        self.assertIn("(repo-standard, Layout)", result.stdout)

    def test_lists_under_40_line_single_importer_and_skips_a_library_wrapper(self):
        self.source("src/features/otif/tiny.ts", 12)
        self.source("src/features/otif/stripe.ts", 10, imports=("stripe",))
        self.source("src/features/otif/page.ts", 40, imports=("./tiny", "./stripe"))
        result = self.run_cli()
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertIn("fragment: src/features/otif/tiny.ts 12 lines, 1 importer", result.stdout)
        self.assertNotIn("fragment: src/features/otif/stripe.ts", result.stdout)
        self.assertNotIn("fragment: src/features/otif/page.ts", result.stdout)

    def test_a_plan_entry_with_paths_counts_a_feature_outside_a_features_folder(self):
        self.write(".pstack/feature-budgets.json", json.dumps({"features": {
            "reporting/items": {"kind": "edit", "paths": ["app/(app)/reporting/items", "lib/items"]},
        }}))
        self.source("app/(app)/reporting/items/page.tsx", 10)
        self.source("lib/items/store.ts", 20)
        self.source("lib/items/store.test.ts", 300)
        self.source("lib/other.ts", 50)
        result = self.run_cli()
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertIn("1 features", result.stdout)
        self.assertIn("reporting/items  files=2 lines=30 budget=7/1200 (edit)  ok", result.stdout)

    def test_base_fails_when_a_feature_over_twice_its_budget_grows_and_passes_when_it_shrinks(self):
        self.git("init", "-q", "-b", "main")
        for n in range(11):
            self.source(f"src/features/huge/{n}.ts", 4)
        self.source("src/features/small/a.ts", 4)
        self.commit_all("base")
        self.git("checkout", "-q", "-b", "work")
        self.source("src/features/huge/0.ts", 9)
        self.source("src/features/huge/huge.test.ts", 500)
        self.source("src/features/small/a.ts", 60)
        self.commit_all("grow")
        grown = self.run_cli("--base", "main")
        self.assertEqual(grown.returncode, 1, grown.stdout)
        self.assertIn("FAIL: huge is over twice its budget and this change adds 5 lines against main", grown.stderr)
        self.assertNotIn("small", grown.stderr)
        self.assertEqual(self.run_cli().returncode, 0)
        (self.root / "src/features/huge/1.ts").unlink()
        (self.root / "src/features/huge/2.ts").unlink()
        self.commit_all("cut back")
        cut = self.run_cli("--base", "main")
        self.assertEqual(cut.returncode, 0, cut.stderr)

    def test_a_raised_budget_in_the_plan_lets_the_feature_grow(self):
        self.git("init", "-q", "-b", "main")
        for n in range(11):
            self.source(f"src/features/huge/{n}.ts", 4)
        self.commit_all("base")
        self.git("checkout", "-q", "-b", "work")
        self.source("src/features/huge/0.ts", 9)
        self.write(".pstack/feature-budgets.json", json.dumps({"features": {"huge": {"files": 12, "lines": 2500}}}))
        self.commit_all("grow with an approved budget")
        result = self.run_cli("--base", "main")
        self.assertEqual(result.returncode, 0, result.stderr)

    def test_a_broken_plan_fails_instead_of_falling_back_to_defaults(self):
        self.write(".pstack/feature-budgets.json", "{not json")
        self.source("src/features/otif/a.ts", 1)
        result = self.run_cli()
        self.assertNotEqual(result.returncode, 0)
        self.assertIn("is not valid JSON", result.stderr)


if __name__ == "__main__":
    unittest.main()

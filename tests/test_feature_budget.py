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

    def run_cli(self):
        return subprocess.run([sys.executable, str(CLI), str(self.root)],
                              text=True, capture_output=True, timeout=20)

    def test_counts_source_files_and_lines_and_skips_tests(self):
        for name in ("a", "b", "c"):
            self.source(f"src/features/otif/{name}.ts", 10)
        self.source("src/features/otif/otif.test.ts", 200)
        result = self.run_cli()
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertIn("files=3 lines=30 budget=5/800 (read)  ok", result.stdout)
        self.assertNotIn("files=4", result.stdout)
        self.assertIn("Where Kolin steps in", result.stdout)

    def test_over_budget_fails_review_and_double_stops_the_wave_without_failing(self):
        for n in range(6):
            self.source(f"src/features/wide/{n}.ts", 1)
        for n in range(11):
            self.source(f"src/features/huge/{n}.ts", 1)
        result = self.run_cli()
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertIn("wide  files=6 lines=6 budget=5/800 (read)  over — fails review", result.stdout)
        self.assertIn("huge  files=11 lines=11 budget=5/800 (read)  2x — wave stops until Kolin approves a new budget (foundation, Where Kolin steps in)", result.stdout)

    def test_reads_budgets_from_the_plan_and_falls_back_to_kind_defaults(self):
        self.write(".pstack/feature-budgets.json", json.dumps({
            "custom": {"files": 2, "lines": 40},
            "form": {"kind": "edit"},
        }))
        for n in range(3):
            self.source(f"src/features/custom/{n}.ts", 1)
        for n in range(7):
            self.source(f"src/features/form/{n}.ts", 1)
        result = self.run_cli()
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertIn("custom  files=3 lines=3 budget=2/40 (plan)  over — fails review", result.stdout)
        self.assertIn("form  files=7 lines=7 budget=7/1200 (edit)  ok", result.stdout)

    def test_lists_under_40_line_single_importer_and_skips_a_library_wrapper(self):
        self.source("src/features/otif/tiny.ts", 12)
        self.source("src/features/otif/stripe.ts", 10, imports=("stripe",))
        self.source("src/features/otif/page.ts", 40, imports=("./tiny", "./stripe"))
        result = self.run_cli()
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertIn("fragment: src/features/otif/tiny.ts 12 lines, 1 importer", result.stdout)
        self.assertNotIn("fragment: src/features/otif/stripe.ts", result.stdout)
        self.assertNotIn("fragment: src/features/otif/page.ts", result.stdout)


if __name__ == "__main__":
    unittest.main()

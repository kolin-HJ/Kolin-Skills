import pathlib
import subprocess
import sys
import tempfile
import unittest


AUDIT = pathlib.Path(__file__).resolve().parent.parent / "skills/pstack-local/scripts/diff-audit"


class DiffAuditTests(unittest.TestCase):
    def setUp(self):
        self.repo = pathlib.Path(tempfile.mkdtemp())
        self.git("init", "-q", "-b", "main")
        self.write("src/price.ts", "export function price(n: number) {\n  return n * 2;\n}\n")
        self.write("src/price.test.ts", "it('doubles', () => {\n  expect(price(2)).toBe(4);\n});\n"
                   "it('zero', () => {\n  expect(price(0)).toBe(0);\n});\n")
        self.git("add", "-A")
        self.git("commit", "-qm", "base")

    def git(self, *args):
        subprocess.run(["git", "-C", str(self.repo), "-c", "user.email=t@t", "-c", "user.name=t", *args],
                       check=True, capture_output=True)

    def write(self, relative, text):
        path = self.repo / relative
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(text)

    def audit(self, *args):
        return subprocess.run([sys.executable, str(AUDIT), "main", *args], cwd=self.repo,
                              text=True, capture_output=True, timeout=20)

    def test_each_reward_hack_and_slop_shape_blocks(self):
        cases = {
            "skip": ("src/price.test.ts", "it.skip('doubles', () => {\n  expect(price(2)).toBe(4);\n});\n"
                     "it('zero', () => {\n  expect(price(0)).toBe(0);\n});\n"),
            "test-removed": ("src/price.test.ts", "it('doubles', () => {\n  expect(price(2)).toBe(4);\n});\n"),
            "weak-assert": ("src/price.test.ts", "it('doubles', () => {\n  expect(price(2)).toBeTruthy();\n});\n"
                            "it('zero', () => {\n  expect(price(0)).toBe(0);\n});\n"),
            "escape-hatch": ("src/price.ts", "export function price(n: any) {\n  return n * 2;\n}\n"),
            "swallowed-error": ("src/price.ts", "export function price(n: number) {\n"
                                "  try { return n * 2; } catch {}\n}\n"),
            "comment": ("src/price.ts", "export function price(n: number) {\n  // double it\n  return n * 2;\n}\n"),
            "dependency": ("package.json", '{\n  "dependencies": {\n    "left-pad": "^1.3.0"\n  }\n}\n'),
        }
        for kind, (relative, text) in cases.items():
            with self.subTest(kind=kind):
                self.git("checkout", "-q", "--", ".")
                self.git("clean", "-qfd")
                self.write(relative, text)
                result = self.audit()
                self.assertEqual(result.returncode, 1, result.stdout)
                self.assertIn(f"block {kind}: {relative}", result.stdout)
                self.assertEqual(self.audit("--allow", kind).returncode, 0)

    def test_a_clean_change_passes_and_lists_each_addition_for_the_value_check(self):
        self.write("src/tax.ts", "export function tax(n: number) {\n  return n / 10;\n}\n")
        self.write("src/price.ts", "// eslint-disable-next-line no-console -- logs the audit trail\n"
                   "export function price(n: number) {\n  return n * 2;\n}\n")
        result = self.audit()
        self.assertEqual(result.returncode, 0, result.stdout)
        self.assertIn("new file: src/tax.ts", result.stdout)
        self.assertIn("new symbol: tax (src/tax.ts)", result.stdout)
        self.assertIn("net lines: +4 -0", result.stdout)
        self.assertNotIn("block", result.stdout)


if __name__ == "__main__":
    unittest.main()

import json
import os
import pathlib
import shutil
import subprocess
import sys
import tempfile
import unittest


REPO = pathlib.Path(__file__).resolve().parent.parent
BIN = REPO / "bin/pglite-replay"
STUB = """import { readFileSync, writeFileSync } from 'node:fs'
function record(sql) {
  const path = process.env.PGLITE_RECORD
  if (!path) return
  let prior = []
  try { prior = JSON.parse(readFileSync(path, 'utf8')) } catch {}
  prior.push(sql)
  writeFileSync(path, JSON.stringify(prior))
}
export class PGlite {
  static async create() { return new PGlite() }
  async exec(sql) {
    if (sql.includes('__FAIL__')) throw new Error('exec failed')
    record(sql.trim())
  }
}
"""
STUB_PACKAGE = json.dumps({"name": "@electric-sql/pglite", "type": "module",
                            "exports": {".": "./dist/index.js"}, "main": "./dist/index.js"})


class PgliteReplayTests(unittest.TestCase):
    def setUp(self):
        self.home = pathlib.Path(tempfile.mkdtemp()).resolve()
        self.addCleanup(shutil.rmtree, self.home)
        self.app = self.home / "app"
        self.record = self.home / "execs.json"
        runtime = self.home / ".kolin-skills/pglite-runtime"
        module = runtime / "node_modules/@electric-sql/pglite"
        (module / "dist").mkdir(parents=True)
        (runtime / "package.json").write_text('{"private":true}\n')
        (module / "package.json").write_text(STUB_PACKAGE + "\n")
        (module / "dist/index.js").write_text(STUB)
        fake_npm = self.home / "bin"
        fake_npm.mkdir()
        npm = fake_npm / "npm"
        npm.write_text("#!/bin/sh\necho npm-was-called >&2\nexit 1\n")
        npm.chmod(0o755)
        self.env = {
            **os.environ,
            "HOME": str(self.home),
            "PATH": f"{fake_npm}{os.pathsep}{os.environ['PATH']}",
            "PGLITE_RECORD": str(self.record),
        }

    def write_sql(self, relative, text):
        path = self.app / relative
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(text)
        return path

    def run_bin(self, *args):
        return subprocess.run(
            [sys.executable, str(BIN), *args],
            cwd=self.app, env=self.env, text=True, capture_output=True, timeout=20,
        )

    def execs(self):
        return json.loads(self.record.read_text()) if self.record.is_file() else []

    def test_missing_migrations_fails(self):
        self.app.mkdir()
        result = self.run_bin()
        self.assertNotEqual(result.returncode, 0)
        self.assertIn("supabase/migrations", result.stderr)
        self.assertFalse(self.record.is_file())

    def test_replays_migrations_in_name_order_then_sql_tests(self):
        self.write_sql("supabase/migrations/20240102000000_later.sql", "CREATE TABLE later (id int);\n")
        self.write_sql("supabase/migrations/20240101000000_first.sql", "CREATE TABLE first (id int);\n")
        self.write_sql("supabase/tests/check.sql", "SELECT 1;\n")
        result = self.run_bin(str(self.app))
        self.assertEqual((result.returncode, result.stderr), (0, ""), result.stdout)
        self.assertEqual(self.execs(), ["CREATE TABLE first (id int);", "CREATE TABLE later (id int);", "SELECT 1;"])
        self.assertIn("applied 2, tested 1", result.stdout)
        self.assertNotIn("189", result.stdout)

    def test_sql_error_fails_and_skips_later_files(self):
        self.write_sql("supabase/migrations/a.sql", "CREATE TABLE ok (id int);\n")
        self.write_sql("supabase/migrations/b.sql", "SELECT '__FAIL__';\n")
        self.write_sql("supabase/tests/check.sql", "SELECT 1;\n")
        result = self.run_bin()
        self.assertNotEqual(result.returncode, 0)
        self.assertEqual(self.execs(), ["CREATE TABLE ok (id int);"])
        self.assertIn("exec failed", result.stderr)

    def test_does_not_call_npm_when_the_runtime_is_present(self):
        self.write_sql("supabase/migrations/a.sql", "SELECT 1;\n")
        result = self.run_bin()
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertNotIn("npm-was-called", result.stderr)

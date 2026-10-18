import { execFileSync } from "node:child_process";
import { existsSync, readFileSync, writeFileSync } from "node:fs";
import path from "node:path";
import { fileURLToPath } from "node:url";

import { GATE_POLICY } from "./lib/gate-policy.mjs";
import { writeJson } from "./lib/write-json.mjs";

const ROOT = path.resolve(path.dirname(fileURLToPath(import.meta.url)), "..");
const BASELINE_PATH = path.join(ROOT, "scripts", "file-length-baseline.json");
const SCOPES = GATE_POLICY.scopes["file-length"];
const SOURCE_FILE = /\.(ts|tsx|js|mjs|cjs)$/;
const GENERATED = /(^|\/)(node_modules|\.next|dist)\/|(^|\/)next-env\.d\.ts$/;
const MAX_LINES = GATE_POLICY.maxFileLines;
const FIX_HINT = `split the file by what it owns so each part stays at or under ${MAX_LINES} lines, in its own change before the feature that needs the room`;

function listSourceFiles() {
  const out = execFileSync(
    "git",
    ["ls-files", "-z", "--cached", "--others", "--exclude-standard", "--", ...SCOPES],
    { cwd: ROOT, encoding: "utf8", maxBuffer: 64 * 1024 * 1024 }
  );
  const files = new Set(
    out
      .split("\0")
      .filter((f) => SOURCE_FILE.test(f) && !GENERATED.test(f))
      .filter((f) => existsSync(path.join(ROOT, f)))
  );
  return [...files].sort();
}

function lineCount(file) {
  const text = readFileSync(path.join(ROOT, file), "utf8");
  return text.split("\n").length - (text.endsWith("\n") ? 1 : 0);
}

function scan() {
  const found = new Map();
  for (const file of listSourceFiles()) {
    const lines = lineCount(file);
    if (lines > MAX_LINES) found.set(file, lines);
  }
  return found;
}

function readBaseline() {
  if (!existsSync(BASELINE_PATH)) return {};
  return JSON.parse(readFileSync(BASELINE_PATH, "utf8"));
}

function writeBaseline(counts) {
  const sorted = Object.fromEntries(
    [...counts.entries()].sort(([a], [b]) => (a < b ? -1 : a > b ? 1 : 0))
  );
  writeFileSync(BASELINE_PATH, `${JSON.stringify(sorted, null, 2)}\n`);
}

function compare(found, baseline) {
  const over = [];
  const stale = [];
  for (const [file, lines] of found) {
    const allowed = baseline[file] ?? MAX_LINES;
    if (lines > allowed) over.push({ file, lines, allowed });
  }
  for (const [file, allowed] of Object.entries(baseline)) {
    const current = found.get(file) ?? 0;
    if (current < allowed) stale.push({ file, current, allowed });
  }
  return { over, stale };
}

function printOver(over) {
  for (const { file, lines, allowed } of over) {
    console.error(`${file}: ${lines} lines, allowed ${allowed}`);
  }
  console.error(`\n${over.length} file(s) over ${MAX_LINES} lines: ${FIX_HINT}.`);
}

const mode = process.argv[2] ?? "--check";
const found = scan();

if (mode === "--init") {
  writeBaseline(found);
  console.log(
    `file-length baseline written from scratch: ${found.size} files over ${MAX_LINES} lines`
  );
  process.exit(0);
}

const baseline = readBaseline();
const { over, stale } = compare(found, baseline);

if (mode === "--json") {
  const files = [...new Set([...found.keys(), ...Object.keys(baseline)])].sort();
  const rows = files.map((file) => ({
    file,
    key: `lines over ${MAX_LINES}`,
    current: found.get(file) ?? 0,
    allowed: baseline[file] ?? MAX_LINES,
  }));
  await writeJson({ rows });
  process.exit(0);
}

if (mode === "--update") {
  if (over.length > 0) {
    printOver(over);
    console.error(
      "\nrefusing to update: --update only lowers counts or drops entries, it never raises one. Nothing was written."
    );
    process.exit(1);
  }
  writeBaseline(
    new Map(
      Object.keys(baseline).flatMap((file) => {
        const current = found.get(file);
        return current === undefined ? [] : [[file, current]];
      })
    )
  );
  const dropped = stale.filter((s) => s.current === 0).length;
  console.log(
    `file-length baseline updated: ${stale.length - dropped} lowered, ${dropped} dropped, ${found.size} files remain over ${MAX_LINES} lines`
  );
  process.exit(0);
}

if (mode !== "--check") {
  console.error(`unknown mode ${mode}; use --check (default), --json, --update or --init`);
  process.exit(2);
}

if (over.length > 0) printOver(over);
if (stale.length > 0) {
  for (const { file, current, allowed } of stale) {
    const now = current === 0 ? `at or under ${MAX_LINES} lines or gone` : `${current} lines`;
    console.error(`${file}: ${now}, baseline still allows ${allowed}`);
  }
  console.error(
    `\nstale baseline entries: ${stale.length}. Lock in the shorter files: node scripts/check-file-length.mjs --update`
  );
}
if (over.length > 0 || stale.length > 0) process.exit(1);
console.log(
  `no file grew past ${MAX_LINES} lines: ${found.size} baselined files over the limit (${Object.keys(baseline).length} baseline entries)`
);

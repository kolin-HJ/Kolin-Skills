import { execFileSync } from "node:child_process";
import { existsSync, readFileSync, writeFileSync } from "node:fs";
import { createRequire } from "node:module";
import path from "node:path";
import { fileURLToPath } from "node:url";

import { commentRanges } from "./lib/comments.mjs";
import { GATE_POLICY } from "./lib/gate-policy.mjs";
import { writeJson } from "./lib/write-json.mjs";

const require = createRequire(import.meta.url);
const ts = require("typescript");

const ROOT = path.resolve(path.dirname(fileURLToPath(import.meta.url)), "..");
const BASELINE_PATH = path.join(ROOT, "scripts", "comment-baseline.json");
const SCOPES = GATE_POLICY.scopes.comments;
const SOURCE_FILE = /\.[cm]?[jt]sx?$/;
const GENERATED = /(^|\/)(node_modules|\.next|dist)\/|(^|\/)next-env\.d\.ts$/;
const FIX_HINT = "move the reason into a name, type, test or the PR body";
const EXEMPT_HINT =
  "Only directives a tool in this repo reads are exempt: @ts-expect-error with a reason, @vitest-environment and /// <reference>.";

const ALLOWED_DIRECTIVES = [/^@ts-expect-error\s+\S/s, /^@vitest-environment\s+\S/];

const SCRIPT_KIND = {
  ".tsx": ts.ScriptKind.TSX,
  ".jsx": ts.ScriptKind.JSX,
  ".ts": ts.ScriptKind.TS,
  ".mts": ts.ScriptKind.TS,
  ".cts": ts.ScriptKind.TS,
  ".js": ts.ScriptKind.JS,
  ".mjs": ts.ScriptKind.JS,
  ".cjs": ts.ScriptKind.JS,
};

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

function directiveBody(commentText) {
  if (commentText.startsWith("//")) return commentText.slice(2).trim();
  return commentText
    .replace(/^\/\*+/, "")
    .replace(/\*\/$/, "")
    .trim();
}

function isAllowed(commentText) {
  if (/^\/\/\/\s*<reference\b/.test(commentText)) return true;
  const body = directiveBody(commentText);
  return ALLOWED_DIRECTIVES.some((pattern) => pattern.test(body));
}

function findComments(file) {
  const text = readFileSync(path.join(ROOT, file), "utf8");
  const sourceFile = ts.createSourceFile(
    file,
    text,
    ts.ScriptTarget.Latest,
    false,
    SCRIPT_KIND[path.extname(file)]
  );
  return commentRanges(sourceFile)
    .map((range) => ({ text: text.slice(range.pos, range.end), pos: range.pos }))
    .filter((comment) => !isAllowed(comment.text))
    .map((comment) => ({
      line: sourceFile.getLineAndCharacterOfPosition(comment.pos).line + 1,
      preview: comment.text.split("\n")[0].slice(0, 100),
    }));
}

function scan() {
  const found = new Map();
  for (const file of listSourceFiles()) {
    const comments = findComments(file);
    if (comments.length > 0) found.set(file, comments);
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
  for (const [file, comments] of found) {
    const allowed = baseline[file] ?? 0;
    if (comments.length > allowed) over.push({ file, comments, allowed });
  }
  for (const [file, allowed] of Object.entries(baseline)) {
    const current = found.get(file)?.length ?? 0;
    if (current < allowed) stale.push({ file, current, allowed });
  }
  return { over, stale };
}

function printOver(over) {
  for (const { file, comments, allowed } of over) {
    console.error(`${file}: ${comments.length} comment(s), baseline allows ${allowed}`);
    for (const { line, preview } of comments) console.error(`  ${file}:${line}  ${preview}`);
  }
  console.error(`\n${over.length} file(s) gained comments. Code carries no comments: ${FIX_HINT}.`);
  console.error(EXEMPT_HINT);
}

const mode = process.argv[2] ?? "--check";
const found = scan();
const total = [...found.values()].reduce((sum, comments) => sum + comments.length, 0);

if (mode === "--init") {
  writeBaseline(new Map([...found].map(([file, comments]) => [file, comments.length])));
  console.log(`comment baseline written from scratch: ${found.size} files, ${total} comments`);
  process.exit(0);
}

const baseline = readBaseline();
const { over, stale } = compare(found, baseline);

if (mode === "--json") {
  const files = [...new Set([...found.keys(), ...Object.keys(baseline)])].sort();
  const rows = files.map((file) => ({
    file,
    key: "comments",
    current: found.get(file)?.length ?? 0,
    allowed: baseline[file] ?? 0,
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
        const current = found.get(file)?.length ?? 0;
        return current > 0 ? [[file, current]] : [];
      })
    )
  );
  const dropped = stale.filter((s) => s.current === 0).length;
  console.log(
    `comment baseline updated: ${stale.length - dropped} lowered, ${dropped} dropped, ${total} comments remain`
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
    console.error(`${file}: ${current} comment(s), baseline still allows ${allowed}`);
  }
  console.error(
    `\nstale baseline entries: ${stale.length}. Lock in the lower counts: node scripts/check-comments.mjs --update`
  );
}
if (over.length > 0 || stale.length > 0) process.exit(1);
console.log(
  `no new comments: ${total} baselined comments across ${found.size} files (${Object.keys(baseline).length} baseline entries)`
);

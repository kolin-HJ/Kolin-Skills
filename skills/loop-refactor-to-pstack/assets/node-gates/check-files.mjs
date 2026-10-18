import { spawn } from "node:child_process";
import path from "node:path";
import { fileURLToPath } from "node:url";

export const ROOT = path.resolve(path.dirname(fileURLToPath(import.meta.url)), "..");
export const PER_FILE_GATES = [
  "comments",
  "file-length",
  "guards",
  "rules",
  "oxlint",
  "agents-refs",
  "feature-map",
];
export const DEADCODE_GATE = "deadcode";
const DEADCODE_FILE = "(dead-code graph)";

export function runScript(args) {
  return new Promise((resolve, reject) => {
    const child = spawn("pnpm", ["-s", "run", ...args], { cwd: ROOT });
    const stdout = [];
    const stderr = [];
    child.stdout.on("data", (chunk) => stdout.push(chunk));
    child.stderr.on("data", (chunk) => stderr.push(chunk));
    child.on("error", reject);
    child.on("close", (code) =>
      resolve({
        code,
        stdout: Buffer.concat(stdout).toString("utf8"),
        stderr: Buffer.concat(stderr).toString("utf8"),
      })
    );
  });
}

async function measurePerFileGate(gate) {
  const { code, stdout, stderr } = await runScript([gate, "--json"]);
  if (code !== 0) throw new Error(`pnpm ${gate} --json exited with ${code}:\n${stderr}`);
  return JSON.parse(stdout).rows;
}

async function measureDeadcode() {
  const { stdout, stderr } = await runScript([DEADCODE_GATE, "--format", "json"]);
  if (!stdout.trimStart().startsWith("{")) {
    throw new Error(`pnpm ${DEADCODE_GATE} --format json printed no report:\n${stderr}`);
  }
  const report = JSON.parse(stdout);
  const baselined = report.baseline ?? { entries: 0, matched: 0 };
  return [
    {
      file: DEADCODE_FILE,
      key: "baselined findings",
      current: baselined.matched,
      allowed: baselined.entries,
    },
    { file: DEADCODE_FILE, key: "new findings", current: report.total_issues, allowed: 0 },
  ];
}

export function measureGate(gate) {
  return gate === DEADCODE_GATE ? measureDeadcode() : measurePerFileGate(gate);
}

export function isOver(row) {
  return row.current > row.allowed;
}

export function isStale(row) {
  return row.current < row.allowed;
}

export function sum(rows, field) {
  return rows.reduce((total, row) => total + row[field], 0);
}

export function describeRow(gate, row) {
  return `${gate}: ${row.file} (${row.key}): ${row.current}, baseline allows ${row.allowed}`;
}

function repoPath(arg) {
  const base = process.env.INIT_CWD ?? process.cwd();
  const relative = path.relative(ROOT, path.resolve(base, arg)).split(path.sep).join("/");
  if (relative.startsWith("..") || path.isAbsolute(relative)) {
    console.error(`${arg} is outside the repository`);
    process.exit(2);
  }
  return relative;
}

function isUnder(file, target) {
  return target === "" || file === target || file.startsWith(`${target}/`);
}

function gateLine(gate, rows) {
  const over = rows.filter(isOver).length;
  const stale = rows.filter(isStale).length;
  const flags = [over > 0 ? `${over} over` : "", stale > 0 ? `${stale} stale` : ""].filter(
    (flag) => flag !== ""
  );
  const counts = `${sum(rows, "current")} now, baseline ${sum(rows, "allowed")}`;
  return `  ${gate.padEnd(15)} ${counts}${flags.length > 0 ? `, ${flags.join(", ")}` : ""}`;
}

async function main() {
  const args = process.argv.slice(2);
  if (args.length === 0) {
    console.error("usage: pnpm -s gates:files <file or folder>...");
    process.exit(2);
  }
  const targets = args.map(repoPath);
  const measured = await Promise.all(PER_FILE_GATES.map(measureGate));
  const byGate = PER_FILE_GATES.map((gate, i) => ({ gate, rows: measured[i] }));
  const inTargets = (row) => targets.some((target) => isUnder(row.file, target));
  for (const target of targets) {
    console.log(target === "" ? "(repository root)" : target);
    for (const { gate, rows } of byGate) {
      console.log(
        gateLine(
          gate,
          rows.filter((row) => isUnder(row.file, target))
        )
      );
    }
  }
  const mine = byGate.flatMap(({ gate, rows }) =>
    rows.filter(inTargets).map((row) => ({ gate, row }))
  );
  const elsewhere = byGate.flatMap(({ gate, rows }) =>
    rows.filter((row) => isOver(row) && !inTargets(row)).map((row) => ({ gate, row }))
  );
  const report = (title, entries) => {
    if (entries.length === 0) return;
    console.log(`\n${title}`);
    for (const { gate, row } of entries) console.log(`  ${describeRow(gate, row)}`);
  };
  report(
    "over baseline in the given paths:",
    mine.filter(({ row }) => isOver(row))
  );
  report(
    "stale, lower at wave end:",
    mine.filter(({ row }) => isStale(row))
  );
  report("over baseline elsewhere:", elsewhere);
  const failed = mine.some(({ row }) => isOver(row)) || elsewhere.length > 0;
  console.log(
    failed
      ? "\nFAIL: a count rose above its baseline. Fix the finding; a baseline only shrinks."
      : "\nOK: no count rose above its baseline."
  );
  process.exit(failed ? 1 : 0);
}

if (process.argv[1] === fileURLToPath(import.meta.url)) await main();

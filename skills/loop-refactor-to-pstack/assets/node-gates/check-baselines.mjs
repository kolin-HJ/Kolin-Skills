import { execFileSync } from "node:child_process";
import { existsSync, readFileSync } from "node:fs";
import path from "node:path";
import { fileURLToPath } from "node:url";

import { DEADCODE_GATE, PER_FILE_GATES, ROOT, measureGate, sum } from "./check-files.mjs";

export const REGISTRY_FILE = "scripts/baselines.json";
const BASELINE_FILE = /(^|\/)[^/]+-baseline\.json$/;
const TARGET = 0;
const ENTRY_FIELDS = ["file", "gate", "format", "unit", "target"];

function nested(json) {
  return new Map(
    Object.entries(json).flatMap(([group, files]) =>
      Object.entries(files).map(([file, count]) => [`${group} ${file}`, count])
    )
  );
}

export const FORMATS = {
  "per-file": (json) => new Map(Object.entries(json)),
  nested,
  listed: (json) => new Map(json.map((entry) => [entry, 1])),
  lint: (json) =>
    new Map(
      Object.entries(json).flatMap(([dir, categories]) =>
        Object.entries(categories).flatMap(([category, files]) =>
          Object.entries(files).map(([file, count]) => [`${category} ${dir}/${file}`, count])
        )
      )
    ),
  fallow: (json) =>
    new Map(
      Object.entries(json)
        .filter(([, value]) => Array.isArray(value))
        .flatMap(([category, entries]) => entries.map((entry) => [`${category} ${entry}`, 1]))
    ),
};

export function readJsonIfPresent(file) {
  const absolute = path.join(ROOT, file);
  return existsSync(absolute) ? JSON.parse(readFileSync(absolute, "utf8")) : null;
}

export function readRegistry() {
  return JSON.parse(readFileSync(path.join(ROOT, REGISTRY_FILE), "utf8"));
}

export function baselineFilesOnDisk() {
  return execFileSync("git", ["ls-files", "-z", "--cached", "--others", "--exclude-standard"], {
    cwd: ROOT,
    encoding: "utf8",
    maxBuffer: 64 * 1024 * 1024,
  })
    .split("\0")
    .filter((file) => BASELINE_FILE.test(file) && existsSync(path.join(ROOT, file)));
}

function checkEntry(entry, scripts) {
  const problems = [];
  const fields = Object.keys(entry).sort();
  if (JSON.stringify(fields) !== JSON.stringify([...ENTRY_FIELDS].sort())) {
    problems.push(
      `has fields ${fields.join(", ")}; an entry has exactly ${ENTRY_FIELDS.join(", ")}`
    );
  }
  if (entry.target !== TARGET) problems.push(`target is ${entry.target}; every baseline targets 0`);
  if (!(entry.format in FORMATS)) {
    problems.push(`format ${entry.format} is not one of ${Object.keys(FORMATS).join(", ")}`);
  }
  if (typeof entry.unit !== "string" || entry.unit.trim() === "") {
    problems.push("names no unit that burns it to zero");
  }
  const gateSteps = scripts.check.split("&&").map((step) => step.trim());
  if (!(entry.gate in scripts) || !gateSteps.includes(`pnpm ${entry.gate}`)) {
    problems.push(`gate ${entry.gate} is not a package.json script that pnpm check runs`);
  }
  if (entry.gate !== DEADCODE_GATE && !PER_FILE_GATES.includes(entry.gate)) {
    problems.push(`gate ${entry.gate} is missing from PER_FILE_GATES in scripts/check-files.mjs`);
  }
  const json = readJsonIfPresent(entry.file);
  if (json === null) {
    problems.push(
      "has no file; a baseline burned to zero is deleted with its registry entry, so drop the entry"
    );
  } else if (entry.format in FORMATS && FORMATS[entry.format](json).size === 0) {
    problems.push(
      `is empty; delete ${entry.file} and its entry here, so the gate fails on any finding`
    );
  }
  return problems.map((problem) => `${REGISTRY_FILE}: ${entry.file} ${problem}`);
}

function check() {
  const registry = readRegistry();
  const { scripts } = JSON.parse(readFileSync(path.join(ROOT, "package.json"), "utf8"));
  const registered = new Set(registry.map((entry) => entry.file));
  const problems = [
    ...registry.flatMap((entry) => checkEntry(entry, scripts)),
    ...(registered.size < registry.length ? [`${REGISTRY_FILE} lists a file twice`] : []),
    ...baselineFilesOnDisk()
      .filter((file) => !registered.has(file))
      .map(
        (file) =>
          `${file}: a baseline with no entry in ${REGISTRY_FILE}; register it with its gate, the unit that burns it to zero and target 0, or fix the findings and delete it`
      ),
  ];
  if (problems.length > 0) {
    for (const problem of problems) console.error(problem);
    console.error(
      `\n${problems.length} baseline registry problem(s). A baseline is temporary debt with an owner: registered, burned to zero, then deleted.`
    );
    process.exit(1);
  }
  const findings = registry.reduce(
    (total, entry) => total + FORMATS[entry.format](readJsonIfPresent(entry.file)).size,
    0
  );
  console.log(
    `every baseline is registered with target 0: ${registry.length} baselines, ${findings} entries left`
  );
}

async function status() {
  const registry = readRegistry();
  const measured = await Promise.all(registry.map((entry) => measureGate(entry.gate)));
  const width = Math.max(...registry.map((entry) => entry.gate.length));
  registry.forEach((entry, i) => {
    const rows = measured[i];
    const baselined = rows.filter((row) => row.allowed > 0);
    const files = new Set(baselined.map((row) => row.file)).size;
    const spread = entry.format === "fallow" ? "the project graph" : `${files} files`;
    console.log(
      `${entry.gate.padEnd(width)}  baseline ${sum(baselined, "allowed")} in ${spread}, now ${sum(rows, "current")}, target ${entry.target}  (${entry.file}; unit: ${entry.unit})`
    );
  });
  console.log(`\n${registry.length} baselines left. The program is done when this list is empty.`);
}

if (process.argv[1] === fileURLToPath(import.meta.url)) {
  const mode = process.argv[2] ?? "--check";
  if (mode === "--check") check();
  else if (mode === "--status") await status();
  else {
    console.error(`unknown mode ${mode}; use --check (default) or --status`);
    process.exit(2);
  }
}

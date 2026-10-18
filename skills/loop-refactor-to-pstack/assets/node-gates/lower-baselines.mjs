import { existsSync, readFileSync, rmSync, writeFileSync } from "node:fs";
import path from "node:path";

import { FORMATS, readJsonIfPresent, readRegistry } from "./check-baselines.mjs";
import {
  DEADCODE_GATE,
  ROOT,
  describeRow,
  isOver,
  isStale,
  measureGate,
  runScript,
  sum,
} from "./check-files.mjs";

const RUN_AFTER_CONFIG_WRITES = [DEADCODE_GATE];

function updateCommand(gate) {
  return gate === DEADCODE_GATE ? ["deadcode:baseline"] : [gate, "--update"];
}

function stop(lines) {
  for (const line of lines) console.error(line);
  console.error("stopped: the gates before this one are lowered, the rest are not.");
  process.exit(1);
}

async function remeasured(step) {
  const rows = await measureGate(step.gate);
  const rose = rows.filter(isOver).map((row) => describeRow(step.gate, row));
  if (rose.length > 0) stop([...rose, `${step.gate} rose while the earlier gates were lowered.`]);
  return lowering(step, rows);
}

async function updateWithoutGrowth(step) {
  const absolute = path.join(ROOT, step.file);
  const original = existsSync(absolute) ? readFileSync(absolute, "utf8") : null;
  const entries = FORMATS[step.format];
  const before = original === null ? new Map() : entries(JSON.parse(original));
  const { code, stdout, stderr } = await runScript(updateCommand(step.gate));
  if (code !== 0) stop([`${step.gate}: update failed with ${code}`, stdout, stderr]);
  const written = readJsonIfPresent(step.file);
  const grown = [...(written === null ? new Map() : entries(written))].filter(
    ([key, count]) => count > (before.get(key) ?? 0)
  );
  if (grown.length === 0) return;
  if (original === null) rmSync(absolute);
  else writeFileSync(absolute, original);
  stop([
    ...grown.map(([key]) => `${step.file}: ${key} was added by the update`),
    `${step.gate}: its update raised the baseline, so ${step.file} was restored.`,
  ]);
}

function lowering(entry, rows) {
  const baselined = rows.filter((row) => row.allowed > 0);
  const kept = baselined.map((row) => ({ ...row, current: Math.min(row.current, row.allowed) }));
  return {
    ...entry,
    changed: rows.some(isStale),
    before: sum(baselined, "allowed"),
    after: sum(kept, "current"),
    entriesBefore: baselined.length,
    entriesAfter: kept.filter((row) => row.current > 0).length,
  };
}

function summary({ gate, before, after, entriesBefore, entriesAfter, changed }) {
  const counts = `${before} -> ${after} (${entriesBefore} -> ${entriesAfter} entries)`;
  return `${gate}: ${changed ? counts : `${before}, unchanged`}`;
}

function inLoweringOrder(registry) {
  const late = (entry) => RUN_AFTER_CONFIG_WRITES.indexOf(entry.gate);
  return [
    ...registry.filter((entry) => late(entry) === -1),
    ...registry.filter((entry) => late(entry) !== -1).sort((a, b) => late(a) - late(b)),
  ];
}

const args = process.argv.slice(2);
if (args.some((arg) => arg !== "--dry-run")) {
  console.error("usage: pnpm -s gates:lower [--dry-run]");
  process.exit(2);
}
const dryRun = args.includes("--dry-run");
const registry = inLoweringOrder(readRegistry());
const measured = await Promise.all(registry.map((entry) => measureGate(entry.gate)));

const rises = registry.flatMap((entry, i) =>
  measured[i].filter(isOver).map((row) => describeRow(entry.gate, row))
);
for (const rise of rises) console.error(rise);
const refusal = `${rises.length} count(s) rose above their baseline, so nothing can be lowered until they are fixed`;

const plan = registry.map((entry, i) => lowering(entry, measured[i]));
if (dryRun) {
  for (const step of plan) console.log(`would lower ${summary(step)}`);
  console.log(`\ndry run: nothing was written.${rises.length > 0 ? ` ${refusal}.` : ""}`);
  process.exit(rises.length > 0 ? 1 : 0);
}
if (rises.length > 0) {
  console.error(`\nrefusing to lower: ${refusal}. Nothing was written.`);
  process.exit(1);
}

for (const planned of plan) {
  const step = RUN_AFTER_CONFIG_WRITES.includes(planned.gate) ? await remeasured(planned) : planned;
  if (!step.changed) {
    console.log(summary(step));
    continue;
  }
  await updateWithoutGrowth(step);
  console.log(summary(step));
  if (step.entriesAfter === 0) {
    console.log(
      `  ${step.file} is now empty: delete it and its entry in scripts/baselines.json so the gate fails on any finding`
    );
  }
}

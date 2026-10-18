import { execFileSync } from "node:child_process";
import { readFileSync } from "node:fs";
import { join } from "node:path";
import { fileURLToPath } from "node:url";
import { parseArgs } from "node:util";

const UNIT_HEADER = "id\ttrack\tstate\tbranch\tpr\tsha\tbrief";
const COMMIT_START = "\x1e";
const FIELD = "\x1f";
const NO_UNIT = "(no Unit trailer)";
const UNKNOWN_UNIT = "(unit not in units.tsv)";

export function parseUnits(tsv) {
  const [header, ...rows] = tsv.trimEnd().split("\n");
  if (header !== UNIT_HEADER) throw new Error(`units.tsv header is not "${UNIT_HEADER}"`);
  return new Map(rows.filter(Boolean).map((row) => row.split("\t")).map(([id, track]) => [id, track]));
}

export function parseLog(log) {
  return log
    .split(COMMIT_START)
    .filter((chunk) => chunk.trim() !== "")
    .map((chunk) => {
      const [head, ...stats] = chunk.split("\n");
      const [sha, unit] = head.split(FIELD);
      const files = stats
        .filter((line) => line.trim() !== "")
        .map((line) => {
          const [added, deleted, path] = line.split("\t");
          return { path, added: added === "-" ? 0 : Number(added), deleted: deleted === "-" ? 0 : Number(deleted) };
        });
      const units = unit.split(",").map((id) => id.trim()).filter(Boolean);
      return { sha, units, files };
    })
    .reverse();
}

export function waveRows(units, commits) {
  const waves = new Map();
  for (const commit of commits) {
    const wave = commit.units.length === 0 ? NO_UNIT : (units.get(commit.units[0]) ?? UNKNOWN_UNIT);
    const row = waves.get(wave) ?? { wave, units: new Set(), commits: 0, added: 0, deleted: 0, files: new Set() };
    for (const id of commit.units) row.units.add(id);
    row.commits += 1;
    for (const file of commit.files) {
      row.added += file.added;
      row.deleted += file.deleted;
      row.files.add(file.path);
    }
    waves.set(wave, row);
  }
  return [...waves.values()];
}

export function renderTable(rows, baseMerges) {
  const lines = ["| Wave | Units | Commits | Lines | Files |", "|---|---|---|---|---|"];
  for (const row of rows) {
    lines.push(`| ${row.wave} | ${row.units.size} | ${row.commits} | +${row.added} / -${row.deleted} | ${row.files.size} |`);
  }
  const total = (pick) => rows.reduce((sum, row) => sum + pick(row), 0);
  const files = new Set(rows.flatMap((row) => [...row.files]));
  lines.push(
    `| Total | ${total((row) => row.units.size)} | ${total((row) => row.commits)} | +${total((row) => row.added)} / -${total((row) => row.deleted)} | ${files.size} |`
  );
  lines.push("", `Base merges into the branch: ${baseMerges}.`);
  return lines.join("\n");
}

function git(args) {
  return execFileSync("git", args, { encoding: "utf8", maxBuffer: 256 * 1024 * 1024 });
}

function main() {
  const { values } = parseArgs({ options: { store: { type: "string" }, base: { type: "string" } } });
  if (values.store === undefined || values.base === undefined) {
    console.error("usage: wave-table.mjs --store <orch store> --base <base ref>");
    process.exit(2);
  }
  const units = parseUnits(readFileSync(join(values.store, "units.tsv"), "utf8"));
  const range = `${values.base}..HEAD`;
  const log = git([
    "log",
    "--no-merges",
    "--no-renames",
    "--numstat",
    `--format=${COMMIT_START}%H${FIELD}%(trailers:key=Unit,valueonly,separator=%x2C)`,
    range,
  ]);
  const baseMerges = Number(git(["rev-list", "--merges", "--count", range]).trim());
  console.log(renderTable(waveRows(units, parseLog(log)), baseMerges));
}

if (process.argv[1] === fileURLToPath(import.meta.url)) main();

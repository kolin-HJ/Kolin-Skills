import { spawnSync } from "node:child_process";
import { existsSync, readFileSync } from "node:fs";
import path from "node:path";

import {
  FORMATS,
  REGISTRY_FILE,
  baselineFilesOnDisk,
  readJsonIfPresent,
  readRegistry,
} from "./check-baselines.mjs";
import { ROOT } from "./check-files.mjs";
import { CONFIGS, compareConfig } from "./lib/ratchet.mjs";

const baseRef = process.argv[2];
if (!baseRef) {
  console.error("usage: node scripts/check-baseline-ratchet.mjs <base-ref>");
  process.exit(2);
}
const resolved = spawnSync("git", ["rev-parse", "--verify", "--quiet", `${baseRef}^{commit}`], {
  cwd: ROOT,
  encoding: "utf8",
});
if (resolved.status !== 0) {
  console.error(`cannot resolve base ref ${baseRef}; fetch it first`);
  process.exit(2);
}

function renamesSinceBase() {
  const diff = spawnSync("git", ["diff", "--name-status", "-M", "-z", baseRef], {
    cwd: ROOT,
    encoding: "utf8",
    maxBuffer: 64 * 1024 * 1024,
  });
  const fields = diff.stdout.split("\0");
  const renames = new Map();
  for (let i = 0; i < fields.length;) {
    const status = fields[i];
    if (status.startsWith("R")) {
      renames.set(fields[i + 1], fields[i + 2]);
      i += 3;
    } else {
      i += status.startsWith("C") ? 3 : 2;
    }
  }
  return renames;
}

const RENAMES = renamesSinceBase();

function readAtBase(file) {
  const result = spawnSync("git", ["show", `${baseRef}:${file}`], {
    cwd: ROOT,
    encoding: "utf8",
    maxBuffer: 64 * 1024 * 1024,
  });
  return result.status === 0 ? result.stdout : null;
}

function readAtHead(file) {
  const absolute = path.join(ROOT, file);
  return existsSync(absolute) ? readFileSync(absolute, "utf8") : null;
}

function gitLines(args) {
  return spawnSync("git", args, { cwd: ROOT, encoding: "utf8", maxBuffer: 64 * 1024 * 1024 })
    .stdout.split("\0")
    .filter((file) => file !== "");
}

function filesFor(config) {
  const atBase = gitLines(["ls-tree", "-r", "-z", "--name-only", baseRef]).filter(config.match);
  const atHead = gitLines(["ls-files", "-z", "--cached", "--others", "--exclude-standard"])
    .filter(config.match)
    .filter((file) => existsSync(path.join(ROOT, file)));
  const headOfBase = atBase.map((file) => RENAMES.get(file) ?? file);
  const pairs = [
    ...atBase.map((file, i) => ({ file: headOfBase[i], baseFile: file })),
    ...atHead
      .filter((file) => !headOfBase.includes(file))
      .map((file) => ({ file, baseFile: file })),
  ];
  return pairs.sort((a, b) => a.file.localeCompare(b.file));
}

function registeredBaselines() {
  const head = readRegistry();
  const baseText = readAtBase(REGISTRY_FILE);
  const base = baseText === null ? [] : JSON.parse(baseText);
  const headByFile = new Map(head.map((entry) => [entry.file, entry]));
  const problems = base.flatMap((entry) => {
    const now = headByFile.get(entry.file);
    if (now === undefined && readJsonIfPresent(entry.file) !== null) {
      return [`${entry.file}: still on disk, but its ${REGISTRY_FILE} entry was removed`];
    }
    if (now !== undefined && now.format !== entry.format) {
      return [
        `${entry.file}: its format in ${REGISTRY_FILE} changed from ${entry.format} to ${now.format}`,
      ];
    }
    return [];
  });
  const unregistered = baselineFilesOnDisk()
    .filter((file) => !headByFile.has(file))
    .map((file) => `${file}: a baseline file with no entry in ${REGISTRY_FILE}`);
  const byFile = new Map([...head, ...base].map((entry) => [entry.file, entry]));
  const tracked = [...byFile.values()].map(({ file, gate, format }) => ({
    file,
    unit: `baselined ${gate} entries`,
    entries: FORMATS[format],
  }));
  return { problems: [...problems, ...unregistered], tracked };
}

const registered = registeredBaselines();
for (const problem of registered.problems) console.error(problem);
if (registered.problems.length > 0) {
  console.error(
    `\n${registered.problems.length} baseline(s) escaped the ratchet. Every baseline keeps its registry entry and format until it is burned to zero and deleted.\n`
  );
}
let grew = registered.problems.length > 0;
const registeredConfigs = registered.tracked.map((tracked) => ({
  ...tracked,
  match: (file) => file === tracked.file,
}));
for (const config of [...registeredConfigs, ...CONFIGS]) {
  for (const { file, baseFile } of filesFor(config)) {
    const { dropped, raised, baseMissing, sizes } = compareConfig({
      file,
      config,
      baseText: readAtBase(baseFile),
      headText: readAtHead(file),
      renames: RENAMES,
    });
    for (const key of dropped) {
      console.error(`${file}: ${key} is no longer enforced`);
    }
    if (dropped.length > 0) {
      console.error(
        `${file}: ${dropped.length} rule(s), plugin(s) or option(s) removed. Removing one drops its baselined findings without fixing them.\n`
      );
    }
    for (const { key, from, to } of raised) {
      console.error(`${file}: ${key} rose from ${from} to ${to}`);
    }
    if (raised.length > 0) {
      const origin = baseMissing ? ", in a file the base does not have" : "";
      console.error(
        `${file}: ${raised.length} new or raised ${config.unit}${origin}. A baseline may only shrink; fix the finding instead of exempting it.\n`
      );
    }
    if (dropped.length > 0 || raised.length > 0) {
      grew = true;
      continue;
    }
    console.log(`${file}: ${sizes.base} -> ${sizes.head} ${config.unit}, none new or raised`);
  }
}
if (grew) process.exit(1);

import { execFileSync, spawn } from "node:child_process";
import { existsSync, readFileSync, writeFileSync } from "node:fs";
import path from "node:path";
import { fileURLToPath } from "node:url";

const HERE = path.dirname(fileURLToPath(import.meta.url));
const WORKERS = ["haiku", "sonnet"];

const [repo, outDir, only] = process.argv.slice(2);
if (!repo || !outDir) {
  console.error("usage: node prepare.mjs <hj-supply-chain checkout> <empty directory outside it> [case id]");
  process.exit(2);
}
const ROOT = path.resolve(repo);
const OUT = path.resolve(outDir);
const cases = JSON.parse(readFileSync(path.join(HERE, "cases.json"), "utf8")).filter(
  (c) => !only || c.id === only
);
const git = (cwd, ...args) => execFileSync("git", args, { cwd, encoding: "utf8" }).trim();

const runs = cases.flatMap((c) => WORKERS.map((worker) => ({ c, worker, dir: path.join(OUT, `${c.id}-${worker}`) })));
for (const { dir } of runs) {
  if (existsSync(dir)) {
    console.error(`${dir} exists; pass an empty directory so every run starts from its base`);
    process.exit(1);
  }
}
for (const { c, dir } of runs) git(ROOT, "worktree", "add", "-q", "--detach", dir, c.base);
await Promise.all(
  runs.map(
    ({ dir }) =>
      new Promise((resolve, reject) =>
        spawn("pnpm", ["install", "--frozen-lockfile", "--prefer-offline"], { cwd: dir, stdio: "ignore" }).on(
          "exit",
          (code) => (code === 0 ? resolve() : reject(new Error(`pnpm install failed in ${dir}`)))
        )
      )
  )
);
for (const { c, worker, dir } of runs) {
  const brief = readFileSync(path.join(HERE, c.brief), "utf8").replaceAll("{{WORKTREE}}", dir);
  const file = path.join(OUT, `${c.id}-${worker}.brief.md`);
  writeFileSync(file, brief);
  console.log(`${c.id}\t${worker}\t${dir}\t${file}`);
}

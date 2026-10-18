import { execFileSync } from "node:child_process";
import { copyFileSync, existsSync, readFileSync } from "node:fs";
import path from "node:path";
import { fileURLToPath } from "node:url";

const HERE = path.dirname(fileURLToPath(import.meta.url));

const [repo, outDir] = process.argv.slice(2);
if (!repo || !outDir) {
  console.error("usage: node prepare.mjs <hj-supply-chain checkout> <empty directory outside it>");
  process.exit(2);
}
const ROOT = path.resolve(repo);

const cases = JSON.parse(readFileSync(path.join(HERE, "cases.json"), "utf8"));
const git = (cwd, ...args) => execFileSync("git", args, { cwd, encoding: "utf8" }).trim();

for (const c of cases) {
  const dir = path.join(outDir, c.dir);
  if (existsSync(dir)) {
    console.error(`${dir} exists; pass an empty directory so every case starts from its base`);
    process.exit(1);
  }
  git(ROOT, "worktree", "add", "-q", "--detach", dir, c.base);
  git(dir, "apply", "--index", "--binary", path.join(HERE, c.patch));
  execFileSync("pnpm", ["install", "--frozen-lockfile", "--prefer-offline"], {
    cwd: dir,
    stdio: "ignore",
  });
  const bodyFile = path.join(outDir, `${c.dir}-description.md`);
  copyFileSync(path.join(HERE, c.body), bodyFile);
  console.log(`\n=== ${c.id}\n`);
  console.log(
    [
      `Please review the change checked out at \`${dir}\` (run every command from there). The change is staged on top of HEAD: \`git diff --cached\`, going into \`staging\`.`,
      "",
      `Task as the user stated it: ${c.task}.`,
      "",
      `The author's description is in \`${bodyFile}\`. Read-only review: do not edit files, commit or run a formatter. Give me your full findings report.`,
    ].join("\n")
  );
}

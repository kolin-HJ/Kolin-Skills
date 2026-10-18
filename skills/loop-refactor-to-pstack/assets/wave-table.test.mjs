import assert from "node:assert/strict";
import { execFileSync } from "node:child_process";
import { mkdtempSync, writeFileSync } from "node:fs";
import { tmpdir } from "node:os";
import { join } from "node:path";
import { test } from "node:test";
import { fileURLToPath } from "node:url";

const here = fileURLToPath(new URL(".", import.meta.url));
const script = join(here, "wave-table.mjs");
const commitUnit = join(here, "commit-unit.sh");

function repo() {
  const dir = mkdtempSync(join(tmpdir(), "wave-table-"));
  const run = (cmd, args, env = {}) =>
    execFileSync(cmd, args, { cwd: dir, encoding: "utf8", env: { ...process.env, ...env } });
  run("git", ["init", "-q", "-b", "base"]);
  run("git", ["config", "user.email", "t@example.com"]);
  run("git", ["config", "user.name", "t"]);
  writeFileSync(join(dir, "a.txt"), "one\n");
  run("git", ["add", "a.txt"]);
  run("git", ["commit", "-q", "-m", "base"]);
  run("git", ["checkout", "-q", "-b", "program"]);
  return { dir, run };
}

test("commits made by commit-unit.sh are grouped by the wave each unit belongs to", () => {
  const { dir, run } = repo();
  const store = join(dir, ".store");
  run("mkdir", ["-p", store]);
  writeFileSync(
    join(store, "units.tsv"),
    "id\ttrack\tstate\tbranch\tpr\tsha\tbrief\nw01-lane1\tw01-dead-code\tpending\t\t\t\t\nw02-lane1\tw02-dates\tpending\t\t\t\t\n"
  );
  run("cp", [commitUnit, join(store, "commit-unit.sh")]);
  const commit = (unit, file, body) => {
    writeFileSync(join(dir, file), body);
    writeFileSync(join(store, "msg"), `refactor: ${unit}\n`);
    run("bash", [join(store, "commit-unit.sh"), unit, join(store, "msg"), file], {
      COMMIT_ATTRIBUTION: "Co-Authored-By: Agent <agent@example.com>",
    });
  };
  commit("w01-lane1", "a.txt", "two\nthree\n");
  commit("w02-lane1", "b.txt", "new\n");
  writeFileSync(join(dir, "c.txt"), "loose\n");
  run("git", ["add", "c.txt"]);
  run("git", ["commit", "-q", "-m", "chore: no trailer"]);

  const out = run("node", [script, "--store", store, "--base", "base"]);
  assert.equal(
    out,
    [
      "| Wave | Units | Commits | Lines | Files |",
      "|---|---|---|---|---|",
      "| w01-dead-code | 1 | 1 | +2 / -1 | 1 |",
      "| w02-dates | 1 | 1 | +1 / -0 | 1 |",
      "| (no Unit trailer) | 0 | 1 | +1 / -0 | 1 |",
      "| Total | 2 | 3 | +4 / -1 | 3 |",
      "",
      "Base merges into the branch: 0.",
      "",
    ].join("\n")
  );
});

test("a base merge is counted and its commits stay out of the waves", () => {
  const { dir, run } = repo();
  const store = join(dir, ".store");
  run("mkdir", ["-p", store]);
  writeFileSync(join(store, "units.tsv"), "id\ttrack\tstate\tbranch\tpr\tsha\tbrief\n");
  writeFileSync(join(dir, "p.txt"), "program\n");
  run("git", ["add", "p.txt"]);
  run("git", ["commit", "-q", "-m", "feat: x\n\nUnit: ghost"]);
  run("git", ["checkout", "-q", "base"]);
  writeFileSync(join(dir, "q.txt"), "base moved\n");
  run("git", ["add", "q.txt"]);
  run("git", ["commit", "-q", "-m", "base work"]);
  run("git", ["checkout", "-q", "program"]);
  run("git", ["merge", "-q", "--no-edit", "base"]);

  const out = run("node", [script, "--store", store, "--base", "base"]);
  assert.equal(
    out,
    [
      "| Wave | Units | Commits | Lines | Files |",
      "|---|---|---|---|---|",
      "| (unit not in units.tsv) | 1 | 1 | +1 / -0 | 1 |",
      "| Total | 1 | 1 | +1 / -0 | 1 |",
      "",
      "Base merges into the branch: 1.",
      "",
    ].join("\n")
  );
});

test("a rename counts its two paths once each and a unit committed twice counts once", () => {
  const { dir, run } = repo();
  const store = join(dir, ".store");
  run("mkdir", ["-p", store]);
  writeFileSync(join(store, "units.tsv"), "id\ttrack\tstate\tbranch\tpr\tsha\tbrief\nw03-move\tw03-split\tpending\t\t\t\t\n");
  run("mkdir", ["-p", "lib"]);
  run("git", ["mv", "a.txt", "lib/a.txt"]);
  run("git", ["commit", "-q", "-m", "refactor: move\n\nUnit: w03-move"]);
  writeFileSync(join(dir, "lib/a.txt"), "one\ntwo\n");
  run("git", ["add", "lib/a.txt"]);
  run("git", ["commit", "-q", "-m", "refactor: follow-up\n\nUnit: w03-move"]);

  const out = run("node", [script, "--store", store, "--base", "base"]);
  assert.equal(
    out.split("\n")[2],
    "| w03-split | 1 | 2 | +2 / -1 | 2 |"
  );
});

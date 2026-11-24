#!/usr/bin/env node
import { execFileSync } from "node:child_process";

const SKIP = /(\.test\.|\.spec\.|(^|\/)tests?\/|_test\.(py|go)$|(^|\/)test_[^/]+\.py$|lock\.json|\.lock$|lock\.yaml$|generated\/|\.gen\.(ts|js)$)/;
const base = process.argv[2] || "origin/HEAD";
const raw = execFileSync("git", ["diff", "--numstat", "-z", "--no-renames", base, "HEAD"], { encoding: "utf8" });
let added = 0;
let removed = 0;
for (const record of raw.split("\0")) {
  if (!record) continue;
  const [plus, minus, path] = record.split("\t");
  if (plus === "-" || SKIP.test(path)) continue;
  added += Number(plus);
  removed += Number(minus);
}
const changed = added + removed;
if (changed > 600) {
  console.error(`PR size ${changed} changed lines (excluding tests, lockfiles, generated); split under 600`);
  process.exit(1);
}
console.log(`PR size ${changed} changed lines`);

import assert from "node:assert/strict";
import { test } from "node:test";

import { isReleasePr, proofProblems } from "./check-pr-proof.mjs";

const APP_FILE = ["apps/web/src/lib/demand-plan-grid.ts"];
const SCRIPT_FILE = ["scripts/trust-curve.mjs"];

test("an app change with a verify run passes", () => {
  const body = [
    "## Why",
    "x",
    "## Verification",
    "- Ran: `pnpm -s verify goto /demand/demand-plan` 200, the placeholder row shows; evidence `.verify/evidence/demand-plan/placeholder.png`",
    "- Ran: `pnpm check` all gates pass",
  ].join("\n");
  assert.deepEqual(proofProblems({ body, changedFiles: APP_FILE }), []);
});

test("an app change that says why verify did not run passes", () => {
  const body = [
    "## Verification",
    "- Ran: `pnpm check` all gates pass",
    "- Not run: verify on the page, because BigQuery credentials are missing on this machine",
  ].join("\n");
  assert.deepEqual(proofProblems({ body, changedFiles: APP_FILE }), []);
});

test("an app change with only gate runs fails", () => {
  const body = ["## Verification", "- Ran: `pnpm check` all gates pass"].join("\n");
  assert.deepEqual(proofProblems({ body, changedFiles: APP_FILE }), [
    "the change touches app source but ## Verification has no `pnpm -s verify` or parity-pair run, and no `Not run: verify ..., because ...` line saying why",
  ]);
});

test("a body with no Verification section fails", () => {
  assert.deepEqual(proofProblems({ body: "## Why\nbecause", changedFiles: SCRIPT_FILE }), [
    "the PR body has no ## Verification section",
  ]);
});

test("prose with no Ran line and a Not run line with no reason both fail", () => {
  const body = ["## Verification", "Tests pass and it works.", "- Not run: the browser"].join("\n");
  assert.deepEqual(proofProblems({ body, changedFiles: SCRIPT_FILE }), [
    "## Verification lists no `- Ran: \\`<command>\\` <result>` line",
    '"Not run: the browser" names no reason; write "Not run: <check>, because <why>"',
  ]);
});

test("a script-only change needs a Ran line but no verify run", () => {
  const body = [
    "## Verification",
    "- Ran: `node scripts/trust-curve.mjs --days 30` 41 PRs listed",
  ].join("\n");
  assert.deepEqual(proofProblems({ body, changedFiles: SCRIPT_FILE }), []);
});

test("a test-only change under app source needs no verify run", () => {
  const body = ["## Verification", "- Ran: `pnpm test` 1,357 passed"].join("\n");
  assert.deepEqual(proofProblems({ body, changedFiles: ["apps/web/src/lib/dates.test.ts"] }), []);
});

test("the word verify outside a verify command does not count as an app run", () => {
  const body = [
    "## Verification",
    "- Ran: `pnpm check` and I will verify later",
    "- Not run: the browser, because verify needs BigQuery",
  ].join("\n");
  assert.deepEqual(proofProblems({ body, changedFiles: APP_FILE }), [
    "the change touches app source but ## Verification has no `pnpm -s verify` or parity-pair run, and no `Not run: verify ..., because ...` line saying why",
  ]);
});

test("a parity-pair run counts as an app run", () => {
  const body = [
    "## Verification",
    "- Ran: `node .agents/skills/verify-supply-chain/scripts/parity-pair.mjs --base ../base --head . --out ../p` 0 changes",
  ].join("\n");
  assert.deepEqual(proofProblems({ body, changedFiles: APP_FILE }), []);
});

const pr = (baseRef, headRef, headRepo, baseRepo = "HydroJug/hj-supply-chain") => ({
  base: { ref: baseRef, repo: { full_name: baseRepo } },
  head: { ref: headRef, repo: { full_name: headRepo } },
});

test("a staging to main PR from this repository is a release", () => {
  assert.equal(isReleasePr(pr("main", "staging", "HydroJug/hj-supply-chain")), true);
});

test("a feature PR, a PR into staging and a fork branch named staging are not releases", () => {
  assert.equal(isReleasePr(pr("main", "fix/x", "HydroJug/hj-supply-chain")), false);
  assert.equal(isReleasePr(pr("staging", "staging", "HydroJug/hj-supply-chain")), false);
  assert.equal(isReleasePr(pr("main", "staging", "someone/hj-supply-chain")), false);
  assert.equal(isReleasePr(undefined), false);
});

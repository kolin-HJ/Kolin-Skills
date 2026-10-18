import assert from "node:assert/strict";
import { test } from "node:test";

import {
  candidates,
  featureOf,
  featuresToRecheck,
  headOnlyErrors,
  merge,
  verdict,
} from "./pair-verdict.mjs";

const NAMES = ["supply-plan", "supply-plan-new-variant-demand", "dashboard", "comments"];

test("a change counts only when both passes show it; one seen once is drift", () => {
  assert.deepEqual(
    verdict(
      [
        "deep.dashboard./dashboard.grid0",
        "deep.supply-plan./supply/supply-plan.grid0",
        "comments.threads",
      ],
      ["deep.dashboard./dashboard.grid0", "comments.threads.0", "deep.dashboard.dock-risk.text"]
    ),
    {
      changes: ["deep.dashboard./dashboard.grid0", "comments.threads.0"],
      onlyInPass2: ["deep.dashboard.dock-risk.text"],
      driftCleared: ["deep.supply-plan./supply/supply-plan.grid0"],
    }
  );
});

test("a feature is found by its whole name, not by a shorter name it starts with", () => {
  assert.equal(
    featureOf("deep.supply-plan-new-variant-demand./supply/new-variant-demand-dev.grid0", NAMES),
    "supply-plan-new-variant-demand"
  );
  assert.equal(featureOf("supply-plan.rows", NAMES), "supply-plan");
  assert.equal(featureOf("dashboard /dashboard", NAMES), "dashboard");
});

test("a failure no feature owns stops the recheck instead of being skipped", () => {
  assert.deepEqual(
    featuresToRecheck(
      {
        changes: [{ at: "deep.dashboard./dashboard.grid0" }],
        errors: ["comments /dashboard/comments"],
      },
      NAMES
    ),
    ["dashboard", "comments"]
  );
  assert.equal(
    featuresToRecheck(
      {
        changes: [],
        errors: [],
        against: [{ errors: ["the local app_users table changed during this run"] }],
      },
      NAMES
    ),
    null
  );
});

test("merged per-feature observations keep every feature and every moved table", () => {
  const merged = merge([
    { head: "abc", at: "t0", ms: { a: 1 }, features: { a: 1 }, deep: { a: {} } },
    {
      head: "abc",
      at: "t1",
      ms: { b: 2 },
      features: { b: 2 },
      deep: { b: {} },
      worldChanged: ["grid_views"],
    },
  ]);
  assert.deepEqual(merged, {
    head: "abc",
    at: "t0",
    ms: { a: 1, b: 2 },
    features: { a: 1, b: 2 },
    deep: { a: {}, b: {} },
    worldChanged: ["grid_views"],
  });
});

test("an error only the branch hit stays fatal even when pass 2 is clean", () => {
  assert.deepEqual(
    headOnlyErrors(
      {
        errors: [
          "dashboard /dashboard",
          "comments /dashboard/comments",
          "the local grid_views table changed",
        ],
        against: [{ errors: ["comments /dashboard/comments"] }],
      },
      NAMES
    ),
    ["dashboard /dashboard", "the local grid_views table changed"]
  );
});

test("unsettled differences are rechecked like changes", () => {
  assert.deepEqual(
    candidates({
      changes: [{ at: "deep.dashboard./dashboard.grid0" }],
      unsettled: [{ at: "comments.threads" }],
    }),
    ["deep.dashboard./dashboard.grid0", "comments.threads"]
  );
});

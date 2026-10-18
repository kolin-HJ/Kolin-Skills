import assert from "node:assert/strict";
import { test } from "node:test";
import { isFinding, spansWithLines } from "./check-agents-refs.mjs";

test("a span inside ~~ ~~ is a removed mention, and one outside it is not", () => {
  assert.deepEqual(
    spansWithLines("Gone: ~~`warm-cron.ts`, `warm-probe.ts`~~. Kept: `compute.ts`."),
    [
      { text: "warm-cron.ts", line: 1, removed: true },
      { text: "warm-probe.ts", line: 1, removed: true },
      { text: "compute.ts", line: 1, removed: false },
    ]
  );
});

test("a removed mention fails once the name exists again, and a plain one fails while it is missing", () => {
  const results = [
    isFinding({ removed: true, target: "warm-cron.ts" }, true),
    isFinding({ removed: true, target: "warm-cron.ts" }, false),
    isFinding({ removed: false, target: "compute.ts" }, false),
    isFinding({ removed: false, target: "compute.ts" }, true),
    isFinding({ removed: false, target: "old_main" }, false),
  ];
  assert.deepEqual(results, [true, false, true, false, false]);
});

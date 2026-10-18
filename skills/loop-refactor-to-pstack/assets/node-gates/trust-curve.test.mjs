import assert from "node:assert/strict";
import { test } from "node:test";

import { followUps } from "./trust-curve.mjs";

const GRID = "apps/web/src/lib/grid.ts";
const pr = (number, title, day, files) => ({
  number,
  title,
  mergedAt: `2026-09-${String(day).padStart(2, "0")}T10:00:00Z`,
  files,
});

test("each fix or revert is credited to exactly one earlier PR", () => {
  const rows = followUps(
    [
      pr(1, "feat(grid): add placeholders", 1, [GRID, "AGENTS.md"]),
      pr(2, "feat(other): also edits the grid", 2, [GRID, "apps/web/src/lib/other.ts"]),
      pr(3, 'Revert "feat(grid): add placeholders"', 4, [GRID]),
      pr(4, "fix(other): the other bug", 5, ["apps/web/src/lib/other.ts"]),
      pr(5, "fix(docs): typo", 5, ["AGENTS.md"]),
      pr(6, "fix(grid): broad cleanup", 6, [
        GRID,
        "apps/web/src/lib/a.ts",
        "apps/web/src/lib/b.ts",
      ]),
      pr(7, "fix(grid): too late", 20, [GRID]),
    ],
    7
  );
  assert.deepEqual(
    rows.map((row) => [row.number, row.fixes.map((fix) => fix.number)]),
    [
      [1, [3]],
      [2, [4]],
      [3, []],
      [4, []],
      [5, []],
      [6, []],
      [7, []],
    ]
  );
});

## Why

A placeholder item checked "Demand plan" on the Placeholder Items page did not appear on `/demand/demand-plan`. The grid's three Postgres loaders dropped every `DEV-` UPC. Planners could see the item on the Variant list but not on the plan grid they review.

## Scope

- `getPlanGridDataFromPg` in `lib/demand-plan-grid.ts` admits a `DEV-` UPC when `loadDevItemsForDivision` returns it with `inDemandPlan` true. That covers the active division and excludes Promoted and Cancelled items.
- Type, color, spec, release, launch date and the "Developing" status come from `supply_dev_items` through the existing fallback map.
- `AGENTS.md` and ADR 0055 now describe the rule.
- Out of scope: the BigQuery path (`PLAN_WRITE_PATH=bq`), and showing a placeholder that has no plan units. A row exists only once the item has a rough plan with a channel.

## Blast Radius

Planners on `/demand/demand-plan` see checked placeholders in the monthly and weekly grids. Placeholder demand is stamped division `shared`, so scoping by the division's own dev-item list keeps other divisions' placeholders out. Other readers still exclude `DEV-%`.

## Verification

- `demand-plan-grid.integration.test.ts` runs the real loaders against local Postgres and passes. It checks that a checked placeholder appears with its attributes and units, monthly and weekly, and that an unchecked one is absent. With the loader change reverted, the two presence tests fail.
- Format, `comments`, `rules`, `guards` and `agents-refs` pass.
- Not run: the app in a browser, type-aware oxlint, `pnpm check` and the full `pnpm test`. This checkout's `node_modules/@hj/*` points at another worktree, so the app returns 500. The new test only runs with `DEMAND_PLAN_GRID_DB_TEST=1`, so CI skips it.

🤖 Generated with [Claude Code](https://claude.com/claude-code)

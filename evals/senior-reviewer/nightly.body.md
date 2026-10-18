## Why

Plan rows freeze their price when they are written. When NetSuite later sets or changes an item's base price, existing rows keep the old amount until a planner runs Reprice on the Demand Tools page. The Tools preview showed it: Launching items stored at $5, $10 or $0 now have real prices, and DTC - Placeholder moves by about +$1.4M.

This runs both Tools actions every night so the plan follows the item data. A planner no longer has to remember either button.

## Scope

- `/api/cron/demand-tools-sync` runs `syncItemFields` and then `applyReprice`, the same functions the buttons call. A failing step posts to Google Chat, the other step still runs, and the route answers 500.
- Vercel cron is UTC only, so `apps/web/vercel.json` schedules it at `0 10` and `0 11`. `isNightlyWindow` lets only the run at 4am America/Denver through. The other answers `{ ok: true, skipped: true }`.
- `applyReprice` and `syncItemFields` request a BigQuery push only for the months they changed, and `syncItemFields` returns early when no division differs. The Tools page buttons share this. Before, each step queued a push for all 29 production months every night.
- ADR 0111 and the Demand Tools feature map record the schedule and the reasons.

## Tradeoffs

- Two schedules plus a guard instead of one fixed UTC time, so the run stays at 4am Denver across daylight saving changes.
- Item fields runs before reprice because both rewrite `supply_plan_monthly` for the same pairs.

## Blast Radius

Production only, since Vercel runs crons only there. The nightly reprice rewrites `amount` and `gross_amount` for every plan month, past months included, with no confirm step. This is the same scope as the button. Revenue feeds ABC class and suggested safety stock, so a NetSuite price change now moves purchasing suggestions the next morning. A UPC with no base price is skipped, not zeroed.

Decided: `items.items_netsuite` refreshes every 30 minutes, so the 4am run reads current prices. Past months are repriced on purpose.

## Verification

- `isNightlyWindow` test: 3 cases at fixed instants across both daylight saving changes. It fails when I change the hour or the time zone.
- Local server at 18:10 Denver time: the route answered `{"ok":true,"skipped":true}`.
- Not run: the in-window path, which writes to the database. Both steps are the existing Tools functions.
- Local run through the real functions: a mispriced row was fixed on the first reprice and the second changed nothing. The item fields change path had no mismatch to test with locally. The database was restored.
- `format:check`, typecheck, `comments`, `guards`, `rules`, `agents-refs`, `feature-map`, `file-length` and `deadcode` pass. `oxlint` passes.
- A fresh reviewer read the diff and found one wrong ADR claim, which is fixed.

🤖 Generated with [Claude Code](https://claude.com/claude-code)



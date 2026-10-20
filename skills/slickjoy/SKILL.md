---
name: slickjoy
description: The rules Kolin set for the SlickJoy refactor on 2026-10-19 (quality bar, gates, UI, build policy). Use for any work in the SlickJoy repo or the Reporting app that shares its packages, before you plan, brief, build or review a unit.
---

# SlickJoy refactor rules

Kolin agreed these on 2026-10-19 (MT). The full spec is the Phase 0 plan (`phase0.md` in the program folder, on the box at `/workspace/runs/quality-program-2026-10-19/`). When it and this file disagree, the plan wins; report the gap. The portable rules (flow, checkpoints, quality bars, ratchets, brief template, UI bar) live in `foundation`; this file holds only SlickJoy specifics.

## North star

A codebase agents can be fully trusted to manage with no supervision, with code a person can read. Agent-first is the lens for every choice: pick the option an agent gets right on the first try, and make every bar a command with pass/fail output and fix text.

## Code

- No Effect or other functional-effects library. Plain strict TypeScript: `Result<T, E>` union, tagged `ProviderError` kinds that each carry a `fix` hint, an exhaustive `switch` on the kind, one retry owner (the job runner), one limiter per connector (`withConnectorSlot`), and dependencies passed as one typed argument. No container, decorators or global singletons.
- Strict TypeScript, moving to TS 7 early (U2). OXC only: oxlint (type-aware) and oxfmt.
- Delete the out-of-scope connectors in U3 (tag first).
- The shared lint and security package lives in the SlickJoy repo; Reporting consumes it with a drift check.
- Node 22 LTS everywhere: both repos, the box and Vercel functions.

## Gates

- No GitHub CI. All gates run locally: pre-commit (<= 10 s), pre-push (<= 3 min) and `npm run verify`, which writes `.verify/<sha>.json`. Pushes to protected branches need that evidence.
- Agents may not skip the local gate. The owner hook blocks the skip flags; a bypass is for Kolin only. Never edit the hooks.
- Local Supabase without Docker (`local-supabase` skill).
- Contract tests replay recorded fixtures through MSW in Vitest. No live accounts in tests.
- Parity with staging is a gate: routes, handlers, crons and Shopify routes must match the staging baseline unless a delete is listed as approved.

## UI

- Desktop and mobile must both look clean and professional. `verify:responsive` takes screenshots of every route at 390 px and 1440 px. No horizontal scroll, tap targets of at least 44 x 44 px, and tables become cards below 768 px.
- Shopify embedded app: Polaris web components (after React 19). Web app: shadcn on Base UI.
- Tables and charts: AG Grid and AG Charts Community only. Enterprise packages are banned (`slickjoy/no-ag-enterprise`). All use goes through the one `DataView<Row>` wrapper and the chart wrapper, which render designed cards on mobile from the same `ColumnDef`. No raw `<table>` (`slickjoy/no-raw-table`).
- Brand color is locked: `--color-primary` is `#1ABC9C` in light mode and `#18DCB5` in dark mode. Tokens only; no raw hex or rgb in components. Text on it passes WCAG AA.
- Inspiration from X: Linear, Stripe, Vercel, Shopify admin and Mercury (notes in `/workspace/runs/ui-inspiration-x-2026-10-19.md`).

## Build policy

- All work runs on Kolin's Claude subscription through T3. `ANTHROPIC_API_KEY` stays unset.
- Opus plans and reviews, in a fresh read-only thread. Sonnet builds. Haiku does mechanical sweeps (renames, codemods, fixture recording). Effort is set per task.
- Check Claude usage before each batch.
- Every brief has Goal / Done when / Evidence / Constraints / Stop when, and cites the plan sections, the `architect` and `correct` skills, and the brand-color rule.
- One unit at a time on `refactor/foundation`. A unit is accepted only after `verify` passes and the Opus review returns PASS.
- No commit to staging, push, migration or deploy without Kolin's words.

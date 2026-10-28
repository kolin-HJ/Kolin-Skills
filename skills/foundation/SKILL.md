---
name: foundation
description: Kolin's engineering standard for multi-phase work and repo structure — the flow from plan to release, quality bars, feature-first layout and per-feature budgets, gates, ratchets and the UI bar. Use when planning a multi-phase feature, rebuild or port, when setting up gates, budgets or layout in a repo, or when Kolin asks for the standard. Not needed for a bug fix, a small feature, a review or a question.
---

# Foundation

Reference for large work: a multi-phase feature, a rebuild or port, or setting up a repo's gates and layout. `gap-audit` and `loop-refactor-to-pstack` build on it. It names no project. The global policy owns approvals, code rules, tests and PR format; this file adds only the flow, the check points and the bars for large work.

## North star

A codebase agents can manage without supervision, written so a person can read it. Pick the option an agent with little context gets right on the first try. Readable code breaks ties, because Kolin reviews by reading code. A reader opens one folder and understands one feature top to bottom, and every feature has the same shape. Gates guard this bar; they never replace it. When speed and long-term quality conflict, choose quality and say what it costs.

## The flow

| Step | What happens | pstack owner | Exit |
|---|---|---|---|
| 1 Idea | Write the value case: the outcome, for whom, the cost of doing nothing, the smallest change | `figure-it-out` | Five-line value case |
| 2 Plan (Phase 0) | Spec: scope, units, decisions with a recommended option, estimate. Docs only | `poteto-mode` playbook | Multi-phase work: **Kolin reviews the plan before any build**. Smaller work proceeds on the value case |
| 3 Architecture | Sketch the types, signatures, feature-first module map (Layout), boundaries and state machines before any code; set each feature's file and line budget | `architect`, then `interrogate` | **Kolin approves data structures and system flows**, then ADR plus gate rules seeded at today's count |
| 4a Paved path | New app or rebuild with several features: build the shared primitives and one exemplar feature in the final shape, before any fan-out. Skip for work inside an existing paved path | `poteto-mode` playbooks | **Kolin reads the exemplar** and says it reads well |
| 4b Build | One builder per feature, end to end, copying the exemplar; one check that proves each unit | `poteto-mode` playbooks, `principle-sequence-verifiable-units` | Unit passes the local gate |
| 5 Review | A fresh read-only reviewer that did not build the unit, at most two rounds. At each wave end, a fresh agent reads one finished feature cold (Layout, feature read) | `senior-reviewer`, `interrogate` by risk | PASS, and every feature inside its budget |
| 6 Verify | Proof on the real artifact: the repo's verification skill, staging first, parity against the base | `principle-prove-it-works`, the verification skill | Evidence pasted |
| 7 Release | PR in the policy format, then Kolin merges | policy "Pull requests" | **Kolin's yes** |
| 8 Learn | A mistake seen twice, or once for security, data-loss, or irreversible classes, becomes a check | `correct` | Rule, test or type merged |

The pstack owners are optional tools for each step, not required reads. After a release, `context-audit --pr <repo>#<n>` measures it. When Kolin asks for one PR for a large change, use one commit per verified unit and a review map in the PR body (unit, commits, files, the check that proves it).

## Where Kolin steps in

The policy's Approvals list always applies. Large work adds three check points:

- A multi-phase plan (Phase 0), before its build starts. Work of one or a few units proceeds on the value case.
- The exemplar feature (step 4a), before builders fan out. Its layout becomes every feature's layout, so a wrong shape here is copied everywhere.
- A feature over twice its budget (Layout): the wave stops until Kolin approves a new budget.

Ask once: one bundled question, recommended option first, with the work prepared so his yes is the last step.

## Quality bars

These add to the policy's Code and Done rules:

- **Readable:** a feature lives in one folder inside its budget (Layout). Files aim for 400 lines and split before the policy's 1,000 at a seam that owns one concept. When a complexity cap fires, simplify in place (a table, a `switch`, a state model); never split only to pass a metric.
- **Typed:** strict mode, and the count of casts and `as unknown as` only falls.
- **Value check:** of every addition, ask whether it fixes the problem at its root or works around it. Remove what fails.
- **Tested fast:** under 60 s per module, no sleeps. External APIs replay recorded contract fixtures (for example MSW in Vitest); no live accounts in tests.
- **Small scope:** the unit changes only what its brief names. Delete out-of-scope code; never park it.
- **Componentized:** one shared component per UI pattern and one wrapper per third-party library, so a later switch changes one place.

## Layout

Organize by feature, not by technical layer. A layer split (`contract/`, `core/`, `server/`, `client/`) spreads one feature over four trees; that is how a single report page grew to 37 files and 3,800 lines.

```
src/
  foundation/        built once: transport, platform adapter, UI kit, formatting
  features/<name>/   everything for one feature: its contract, server, page, tests
```

- A feature folder starts with one file per side of a boundary (for example `contract.ts`, `server.ts`, `page.tsx`, plus tests) and grows a file only by the Readable rule.
- Boundary gates protect the layout: features never import each other, and a platform SDK or a library the repo wraps (Componentized) is imported only in `foundation/`. Inside a feature, gate only a runtime boundary (the page never imports the server file); never add layer folders.
- Budget per feature, in source files and lines with tests excluded, set in the step 3 plan Kolin reviews (`.pstack/feature-budgets.json`). Defaults: a read-only page 5 files and 800 lines, an edit page 7 and 1,200, a core write flow 12 and 2,500. `bin/feature-budget` reports the counts (report-only in `kolin-skills check`). Over budget fails review; over twice the budget stops the wave until Kolin approves a new budget (`Where Kolin steps in`).
- **Feature read.** A fresh agent opens one finished feature with no brief beyond its name, traces one request from the page to the data, and reports the files opened, the lines and every file under 40 lines with one importer (inline it), except a single library wrapper (Componentized: one wrapper per third-party lib).

## Guardrails

- A bad pattern seen twice, or once for security, data loss or an irreversible action, becomes a lint rule, test or check, seeded at today's count in a ratchet and driven to zero (`correct`). The rule message names the fix.
- Every gate names the bug it prevents. Gate tooling stays under about a quarter of the app's lines.
- Metric gates report and never block an edit, commit or push, because agents pass a blocking metric by cutting code into fragments. Metric gates are cyclomatic and cognitive complexity, CRAP, mutation score, `max-depth`, `max-lines-per-function`, `max-statements`, `max-params` and `max-nested-callbacks`. The one blocking size rule is the policy's 1,000-line limit, at pre-commit or pre-push. Turning off a blocking metric gate is its own PR with Kolin's yes.
- Strict TypeScript and a type-aware linter (oxlint, oxfmt) where the repo uses TS.
- Errors in plain TypeScript unless the user asks for an effects library: a `Result` union, tagged error kinds with a fix hint, an exhaustive `switch`, one retry owner, one rate limiter and a timeout per external connection, and outside writes that are safe to retry (an idempotency key or an upsert).
- Gates run locally: pre-commit (about 10 s), pre-push (a few minutes) and a `verify` command. Where a repo has CI, each CI job's command also runs in the local check, so CI never finds a new failure.
- A rebuild, port or migration of a live feature starts with `.pstack/parity.md` before any builder runs: one row per behavior a user relies on (`behavior | live file:line | smoke step | status`). Each brief carries its rows, and a cutover waits until every row passes or carries Kolin's approved cut.
- Local databases run without Docker (`local-supabase`).

## UI bar

Desktop and phone both clean and professional, tables become cards on phones, tokens only, Kolin's library picks and inspiration: `references/ui-bar.md`.

## Legacy repos

To bring an existing repo up to this standard, run `gap-audit`. For a whole-repo program on one branch, use `loop-refactor-to-pstack`.

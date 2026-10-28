---
name: repo-standard
description: Kolin's bar for a repo — feature-first layout and budgets, quality bars, gate and ratchet design, the UI bar, and the checklist to audit a repo against it. Use when setting up gates, budgets or layout, when planning a rebuild, port or migration of a live feature, or when Kolin asks to audit a repo, says "what is it missing", "bring it up to standard", "close the gaps" or "make it agent-ready". The method (plan, build, review, ship) is pstack's poteto-mode, not this file.
---

# Repo standard

What a finished repo looks like. pstack's `poteto-mode` is how to get there; the policy owns approvals, code rules and tests. A unit is one change that one builder finishes and one check proves.

## North star

A codebase agents can manage without supervision, written so a person can read it. Pick the option an agent with little context gets right on the first try. Readable code breaks ties, because Kolin reviews by reading code. A reader opens one folder and understands one feature top to bottom, and every feature has the same shape. Gates guard this bar; they never replace it. When speed and long-term quality conflict, choose quality and say what it costs.

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
- Budget per feature, in source files and lines with tests excluded, set in the plan Kolin reviews (`.pstack/feature-budgets.json`). Defaults: a read-only page 5 files and 800 lines, an edit page 7 and 1,200, a core write flow 12 and 2,500. `bin/feature-budget` reports the counts (report-only in `kolin-skills check`). Over budget fails review; over twice the budget stops the wave until Kolin approves a new budget.
- **Feature read.** A fresh agent opens one finished feature with no brief beyond its name, traces one request from the page to the data, and reports the files opened, the lines and every file under 40 lines with one importer (inline it), except a single library wrapper (Componentized: one wrapper per third-party lib).

## Guardrails

- A new rule (policy, Adding rules) becomes a lint rule, test or check where it can. A ratchet starts at today's count and goes to zero. The rule message names the fix.
- Every gate names the bug it prevents. Gate tooling stays under about a quarter of the app's lines.
- Metric gates report and never block an edit, commit or push, because agents pass a blocking metric by cutting code into fragments. Metric gates are cyclomatic and cognitive complexity, CRAP, mutation score, `max-depth`, `max-lines-per-function`, `max-statements`, `max-params` and `max-nested-callbacks`. The one blocking size rule is the policy's 1,000-line limit, at pre-commit or pre-push. Turning off a blocking metric gate is its own PR with Kolin's yes.
- Strict TypeScript and a type-aware linter (oxlint, oxfmt) where the repo uses TS.
- Errors in plain TypeScript unless the user asks for an effects library: a `Result` union, tagged error kinds with a fix hint, an exhaustive `switch`, one retry owner, one rate limiter and a timeout per external connection, and outside writes that are safe to retry (an idempotency key or an upsert).
- Gates run locally: pre-commit (about 10 s), pre-push (a few minutes) and a `verify` command. Where a repo has CI, each CI job's command also runs in the local check, so CI never finds a new failure.
- A rebuild, port or migration of a live feature starts with `.pstack/parity.md` before any builder runs: one row per behavior a user relies on (`behavior | live file:line | smoke step | status`). Each brief carries its rows, and a cutover waits until every row passes or carries Kolin's approved cut.

## UI bar

Desktop and phone both clean and professional, tables become cards on phones, tokens only, Kolin's library picks and inspiration: `references/ui-bar.md`.

## PR Verification

Policy (Pull requests) owns the rule. Copy `references/pr-verification.md` into `.github/PULL_REQUEST_TEMPLATE.md`, or merge the `Ran:` / `Not run:` lines into an existing template. `pr-body` already prints this shape. CI body-lint (`loop-refactor-to-pstack` `assets/workflow/check-pr-proof.mjs`) is the ratchet when recent PRs skip that shape.

## Audit a repo

Read only. Measure, do not guess, and record each row's command and count.

| Area | Measure |
|---|---|
| Instruction file | One root `AGENTS.md`, under about 200 lines; no `CLAUDE.md` copy |
| Gates | Formatter, type-aware linter, strict type check, dead-code check, tests, and one gate command. Local hooks (pre-commit, pre-push, `verify` evidence) if there is no CI. With CI, each job's command also runs in the local gate; a check only CI runs is a gap (a CI-only `bundle-budget` let a red build reach `staging` twice in one release) |
| Ratchets | A baseline file with target 0 per rule; counts per rule today |
| Typing | `any`, casts, non-null assertions, untyped JS files |
| Layout | Feature-first or layer-first (Layout above); per feature, the folders it spans, its file and line count against the budget; files under 40 lines with one importer, except a single library wrapper (Componentized); gate tooling lines as a share of app lines. Run one feature read and report its trace |
| Shape | Files over the line limit, long functions, deep nesting, duplicates (jscpd), single-caller helpers, functions with a CRAP score of 10 or more (complexity joined with coverage, `unclebob/crapper`; a flat `switch` or lookup table is exempt; without the tool, mark it missing and propose it). Complexity and CRAP are report-only; a blocking metric gate is itself a gap |
| Errors | Swallowed errors, try/catch around own code, retries outside one owner |
| Tests | A test for each behavior a caller relies on (policy, Done), not one per entry point; tests of a constant, config, prose or file existence to delete; recorded contract fixtures for external APIs; slow or sleeping tests; surviving mutants in tested code (Stryker for TypeScript), reported, not ratcheted; without the tool, mark it missing and propose it |
| Boundaries | Import rules, one home per concept, parked or out-of-scope code |
| Guardrails | Agent hooks that block gate skips and protected pushes; secrets out of the tree; on GitHub, `delete_branch_on_merge` on (a stacked PR merged into its already-merged base is lost) and the CI jobs required on the integration branch |
| Approval text | Repo instruction text (`AGENTS.md`, repo skills) that requires an ask before a reversible step on a work branch (commit, push, opening a PR) conflicts with the global policy's Approvals. Flag it with `file:line` and rewrite it to match. It cost waits of 9 to 67 minutes in two repos |
| Agent roles | A repo agent that shares a global agent's name (`senior-reviewer`, `poteto-agent`) and pins a lower model than `skills/pstack-local/models.md` gives that role. Flag it |
| Verification | A verification skill with a CLI and feature maps; parity against staging or the base |
| PR Verification | Template `.github/PULL_REQUEST_TEMPLATE.md` (or GitHub's other template paths) has `## Verification` with `Ran:` / `Not run: <check>, because <why>`. No template is met if `pr-body` emits that shape. Measure the template with `rg`; count recent `gh pr list --json body` that miss it. CI body-lint (`check-pr-proof.mjs` or equivalent) is the ratchet when they miss; a template without lint is enough when they match |
| UI (if any) | Raw tables, raw hex colors, screens without 390 and 1440 px checks, tap targets |
| Runtime | One pinned version everywhere |

Write `.pstack/gap-report.md`, or the path Kolin names: a score per area (met, partial or missing, with the count), the gaps ranked by risk times reach (data loss, security and money first, then gates, then readability), one step per gap with **Done when**, and the decisions Kolin owns in one bundled ask, recommended option first. Stop at the report unless Kolin asked you to close the gaps.

To close gaps, run each one as a pstack playbook (Refactoring, Feature), gates first, and rerun the rows it touched before the next one. Gap PRs merge into a `gaps/<date>` branch, never into the integration branch ahead of feature work, and ship as their own release after Kolin reads each PR's value case (a gap split merged into `staging` was reverted in #930). A split cuts at a seam that owns one concept; never split to lower a complexity or CRAP count. A whole-repo program on one branch is `loop-refactor-to-pstack`.

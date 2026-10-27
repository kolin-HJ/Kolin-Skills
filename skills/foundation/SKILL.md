---
name: foundation
description: Kolin's portable engineering foundation for any repo — the north star (code agents can manage unsupervised and people can read), the agent-first lens, the flow from idea to plan, architecture, build, review, verify and release, the points where Kolin checks things himself, quality bars, feature-first layout and per-feature budgets, guardrails, lint and ratchet rules, componentization, strict typing and the UI bar. Use at the start of any feature, refactor, plan, brief, review or architecture work in any repo, and whenever you set up gates, write a builder brief or decide what needs Kolin's approval.
---

# Foundation

The root skill. Every other skill inherits from it: process playbooks (pstack, `loop-refactor-to-pstack`, `gap-audit`), principles (`principle-*`) and utilities. It fits any repo and names no project. Project rules go in that repo's `AGENTS.md` or its own project skill, never here. The global policy (`policy/AGENTS.md`, linked as `~/.claude/CLAUDE.md` and `~/.codex/AGENTS.md`) owns approvals, code rules, tests, briefs and PR format. This file adds the flow and the bars, and does not repeat the policy.

## North star

A codebase agents can be fully trusted to manage with no supervision, written so a person can read it. Agent-first is the lens for every choice: pick the option an agent with little context gets right on the first try. Readable code is the tiebreak: Kolin reviews by reading code, so a clever line that saves a file but costs a reader loses.

The bar is a codebase an experienced engineer would have laid out: a reader opens one folder and understands one feature top to bottom, and every feature has the same shape. Gates guard this bar; they never replace it. Code that passes every gate and still needs ten files to explain one page fails it.

Long-term quality always wins. Pick the clean, durable design that will still be right in a year, not the fastest patch. When short-term speed and long-term quality conflict, choose quality and say what it costs.

## First principles before any code moves

A short step, written before the first edit (`principle-redesign-from-first-principles`, `principle-foundational-thinking`):

1. **Problem:** what is wrong or missing, for whom, in one sentence.
2. **Constraints:** what must hold (behavior, data, budget, the repo's rules).
3. **Options:** two or three real designs, including "change nothing".
4. **Smallest right design:** the one that fixes the root cause with the least code and still holds in a year.

## Think with Kolin

On a big decision, lay out the options with their tradeoffs and one recommendation. Stress-test the reasoning before you present it: `sharpen` the question, `interrogate` the design, and restate his goal with `in-your-own-words` so a wrong reading shows early.

When to bring him in is your judgment call. Signals that point toward asking: a new feature with data-structure questions, a request you can read two ways, and a change with wide codebase impact. You make the final call. The hard check points below are not judgment calls: they always need him.

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

After a release, `bin/context-audit --pr <repo>#<n>` measures it. A finding that costs real time twice may become a gate (policy, "Instruction files").

When Kolin asks for one PR for a large change, keep it one PR, with one commit per verified unit and a review map in the PR body (unit, commits, files, the check that proves it).

## Where Kolin steps in

He checks these himself. Everything else is reversible and proceeds.

- A multi-phase plan (Phase 0), before its build starts. Work of one or a few units proceeds on the value case.
- The exemplar feature (step 4a), before builders fan out. Its layout becomes every feature's layout, so a wrong shape here is copied everywhere.
- A feature over twice its budget (Layout): the wave stops until Kolin approves a new budget.
- **Data structures and system flows (design-approval gate).** Before you add or change a data structure (types, tables, schemas, payloads, state machines) or a system flow (who calls whom, in what order, through which queue or job), show Kolin the proposed layout: the shapes, relations, the flow and a short reason. Ask: "Here is how we will lay this out. Does this make sense? Is this what you had in mind?" Wait for his approval before you implement it.
- Merges, and any change to `main`, `master`, `staging` or `sandbox` (policy, Approvals). Deploys and production releases.
- Money: billing, pricing, purchases, spend caps.
- Secrets and credentials: creating, rotating or sharing them.
- App Store and marketplace submissions.
- Schema changes and migrations, each with a backup step.
- Messages to people and other external writes.

Ask once: one bundled question, recommended option first, with the work already prepared so his yes is the last step. Between those points, report only a real result, a real decision or a block.

## Quality bars (definition of done for every unit)

Each bar is a command with output and fix text, so an agent knows it is done without asking. Metric bars report and never block (Guardrails).

- Readable: a feature lives in one folder inside its budget (Layout); files aim for 400 lines and split only before the policy's 1,000, at a seam that owns one concept; functions about 60 lines, nesting 3 levels, one name per concept. A new file or helper needs the policy's owner or second caller (policy, Code); a metric is never the reason. When a complexity cap fires, simplify the logic (a table, a `switch`, a state model) in place.
- Typed: strict mode; no `any`, cast, non-null assertion or `as unknown as`. The count only falls.
- Tested: every behavior a caller relies on (policy, Tests and proof), fast (under 60 s per module), no sleeps. External APIs replay recorded contract fixtures (for example MSW in Vitest); no live accounts in tests.
- Small scope: the unit changes only what its brief names. Out-of-scope code is deleted (tag the last commit first), never parked.
- One home: a concept lives in one module. Extend the owner; no parallel helper.
- Componentized: one shared component per UI pattern and one wrapper per third-party library, so a later switch changes one place.
- Earns its keep (value check): ask of every addition, "Does this give real value to the codebase? Is it a proper quality implementation, or did we bootstrap or work around the problem instead of fixing it at the root?" Remove anything that fails the check. Fix the root cause instead of adding a workaround (`principle-fix-root-causes`).
- Concise: the least code that holds the bar (`principle-laziness-protocol`, `principle-subtract-before-you-add`).

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

## Guardrails, lint and ratchets

- A bad pattern seen twice, or once for security, data-loss, or irreversible classes, becomes a lint rule, test or check, seeded at today's count in a ratchet and driven to zero (`correct`). A rule message names the fix and the file to use instead.
- Every gate names the bug it prevents, and gate tooling stays small next to the code it guards (about a quarter of the app's lines at most). Metric gates report; they never block an edit, commit or push, because agents pass a blocking metric by cutting code into fragments. Metric gates are cyclomatic and cognitive complexity, CRAP, mutation score, and the lint rules `max-depth`, `max-lines-per-function`, `max-statements`, `max-params` and `max-nested-callbacks`. The one size rule that blocks, where the repo's pre-commit or pre-push enforces it, is the policy's 1,000-line file limit, never at edit. Turning off an existing blocking metric gate is its own PR, with Kolin's yes in the PR body.
- Strict TypeScript where the repo uses TS; a type-aware linter (OXC: oxlint and oxfmt) and the newest TypeScript the tools support.
- Errors in plain TypeScript, with no effects library unless the user asks: a `Result` union, tagged error kinds that each carry a fix hint, an exhaustive `switch` on the kind, one retry owner, one rate limiter and a timeout per external connection, a write to an outside system that is safe to retry (an idempotency key or an upsert, `principle-make-operations-idempotent`), dependencies passed as one typed argument.
- One pinned runtime version (for example one Node LTS) in every repo, the box and the host.
- Gates run locally, never in paid CI: pre-commit (about 10 s), pre-push (a few minutes) and a `verify` command that writes evidence per commit SHA. Pushes to protected branches need that evidence. Where a repo has CI, each job's command also runs in the local check command (skipped when `CI` is set), so CI repeats a pass and never finds a new failure. Agents never skip a gate; `hooks/gate/block-forbidden-git.sh` blocks the skip flags.
- Parity with the base or staging is a gate: routes, handlers and jobs match the baseline unless a delete was approved.
- A rebuild, port or migration of a live feature starts with `.pstack/parity.md`, before any builder runs: one row per behavior a user relies on (`behavior | live file:line | smoke step | status`), from a read-only pass over the live code. Each builder brief carries its rows, and its "Done when" is their smoke steps passing. A review finding for a live behavior with no row adds the row and its smoke step in the same fix round. A cutover waits until every row passes or carries Kolin's approved cut.
- Local databases run without Docker (`local-supabase`).

## UI bar

Desktop and phone both clean and professional, tables become cards on phones, tokens only, Kolin's library picks and inspiration: `references/ui-bar.md`.

## Legacy repos

To bring an existing repo up to this foundation, run `gap-audit` (`~/.agents/skills/gap-audit/SKILL.md`): audit, ranked gap report, small verified steps, re-audit until every ratchet reads zero. For a whole-repo program on one branch, use `loop-refactor-to-pstack`.

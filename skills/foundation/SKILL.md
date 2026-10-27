---
name: foundation
description: Kolin's portable engineering foundation for any repo — the north star (code agents can manage unsupervised and people can read), the agent-first lens, the flow from idea to plan, architecture, build, review, verify and release, the points where Kolin checks things himself, quality bars, guardrails, lint and ratchet rules, componentization, strict typing and the UI bar. Use at the start of any feature, refactor, plan, brief, review or architecture work in any repo, and whenever you set up gates, write a builder brief or decide what needs Kolin's approval.
---

# Foundation

The root skill. Every other skill inherits from it: process playbooks (pstack, `loop-refactor-to-pstack`, `gap-audit`), principles (`principle-*`) and utilities. It fits any repo and names no project. Project rules go in that repo's `AGENTS.md` or its own project skill, never here. The global policy (`policy/AGENTS.md`, linked as `~/.claude/CLAUDE.md` and `~/.codex/AGENTS.md`) owns approvals, code rules, tests, briefs and PR format. This file adds the flow and the bars, and does not repeat the policy.

## North star

A codebase agents can be fully trusted to manage with no supervision, written so a person can read it. Agent-first is the lens for every choice: pick the option an agent with little context gets right on the first try. Readable code is the tiebreak: Kolin reviews by reading code, so a clever line that saves a file but costs a reader loses.

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
| 3 Architecture | Sketch the types, signatures, module map, boundaries and state machines before any code; each boundary a gate | `architect`, then `interrogate` | **Kolin approves data structures and system flows**, then ADR plus gate rules seeded at today's count |
| 4 Build | Small units, one thread each, one check that proves each unit | `poteto-mode` playbooks, `principle-sequence-verifiable-units` | Unit passes the local gate |
| 5 Review | A fresh read-only reviewer that did not build the unit, at most two rounds | `senior-reviewer`, `interrogate` by risk | PASS |
| 6 Verify | Proof on the real artifact: the repo's verification skill, staging first, parity against the base | `principle-prove-it-works`, the verification skill | Evidence pasted |
| 7 Release | PR in the policy format, then Kolin merges | policy "Before a PR ships" | **Kolin's yes** |
| 8 Learn | Every mistake seen becomes a check | `correct` | Rule, test or type merged |

After a release, `bin/context-audit --pr <repo>#<n>` measures it. Each finding moves up the layers of the global policy's "How agents earn trust".

When Kolin asks for one PR for a large change, keep it one PR, with one commit per verified unit and a review map in the PR body (unit, commits, files, the check that proves it).

## Where Kolin steps in

He checks these himself. Everything else is reversible and proceeds.

- A multi-phase plan (Phase 0), before its build starts. Work of one or a few units proceeds on the value case.
- **Data structures and system flows (design-approval gate).** Before you add or change a data structure (types, tables, schemas, payloads, state machines) or a system flow (who calls whom, in what order, through which queue or job), show Kolin the proposed layout: the shapes, relations, the flow and a short reason. Ask: "Here is how we will lay this out. Does this make sense? Is this what you had in mind?" Wait for his approval before you implement it.
- Merges, and any change to `main`, `master`, `staging` or `sandbox` (policy, Approvals). Deploys and production releases.
- Money: billing, pricing, purchases, spend caps.
- Secrets and credentials: creating, rotating or sharing them.
- App Store and marketplace submissions.
- Schema changes and migrations, each with a backup step.
- Messages to people and other external writes.

Ask once: one bundled question, recommended option first, with the work already prepared so his yes is the last step. Between those points, report only a real result, a real decision or a block (policy, Delegation).

## Quality bars (definition of done for every unit)

Each bar is a command with pass/fail output and fix text, so an agent knows it is done without asking.

- Readable: small files (aim for 400 lines; split before the policy's 1,000), short functions (about 60 lines), shallow nesting (3 levels), one name per concept.
- Typed: strict mode; no `any`, cast, non-null assertion or `as unknown as`. The count only falls.
- Tested: every behavior a caller relies on (policy, Tests and proof), fast (under 60 s per module), no sleeps. External APIs replay recorded contract fixtures (for example MSW in Vitest); no live accounts in tests.
- Small scope: the unit changes only what its brief names. Out-of-scope code is deleted (tag the last commit first), never parked.
- One home: a concept lives in one module. Extend the owner; no parallel helper.
- Componentized: one shared component per UI pattern and one wrapper per third-party library, so a later switch changes one place.
- Earns its keep (value check): ask of every addition, "Does this give real value to the codebase? Is it a proper quality implementation, or did we bootstrap or work around the problem instead of fixing it at the root?" Remove anything that fails the check. Fix the root cause instead of adding a workaround (`principle-fix-root-causes`).
- Concise: the least code that holds the bar (`principle-laziness-protocol`, `principle-subtract-before-you-add`).
## Guardrails, lint and ratchets

- Every bad pattern becomes a lint rule, test or check, seeded at today's count in a ratchet and driven to zero (`correct`). A rule message names the fix and the file to use instead.
- Strict TypeScript where the repo uses TS; a type-aware linter (OXC: oxlint and oxfmt) and the newest TypeScript the tools support.
- Errors in plain TypeScript, with no effects library unless the user asks: a `Result` union, tagged error kinds that each carry a fix hint, an exhaustive `switch` on the kind, one retry owner, one rate limiter per external connection, dependencies passed as one typed argument.
- One pinned runtime version (for example one Node LTS) in every repo, the box and the host.
- Gates run locally, never in paid CI: pre-commit (about 10 s), pre-push (a few minutes) and a `verify` command that writes evidence per commit SHA. Pushes to protected branches need that evidence. Where a repo has CI, each job's command also runs in the local check command (skipped when `CI` is set), so CI repeats a pass and never finds a new failure. Agents never skip a gate; `hooks/gate/block-forbidden-git.sh` blocks the skip flags.
- Parity with the base or staging is a gate: routes, handlers and jobs match the baseline unless a delete was approved.
- A rebuild, port or migration of a live feature starts with `.pstack/parity.md`, before any builder runs: one row per behavior a user relies on (`behavior | live file:line | smoke step | status`), from a read-only pass over the live code. Each builder brief carries its rows, and its "Done when" is their smoke steps passing. A review finding for a live behavior with no row adds the row and its smoke step in the same fix round. A cutover waits until every row passes or carries Kolin's approved cut.
- Local databases run without Docker (`local-supabase`).

## UI bar

Desktop and phone both clean and professional, tables become cards on phones, tokens only, Kolin's library picks and inspiration: `references/ui-bar.md`.

## Legacy repos

To bring an existing repo up to this foundation, run `gap-audit` (`~/.agents/skills/gap-audit/SKILL.md`): audit, ranked gap report, small verified steps, re-audit until every ratchet reads zero. For a whole-repo program on one branch, use `loop-refactor-to-pstack`.

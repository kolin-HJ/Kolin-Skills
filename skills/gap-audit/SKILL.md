---
name: gap-audit
description: Audit an existing or legacy repo against Kolin's foundation (quality bars, gates, ratchets, guardrails, typing, tests, UI bar, instruction file), write a ranked gap report, then close the gaps in small verified steps and re-audit after each step until every ratchet reads zero. Use when Kolin points an agent at a repo and asks what it is missing, how far it is from the standard, to "audit", "bring up to standard", "close the gaps" or to make it agent-ready.
---

# Gap audit

The standard is `foundation/SKILL.md` plus the global policy. This skill measures a repo against them and closes the distance. For a full multi-week refactor on one branch, hand off to `loop-refactor-to-pstack` after the first report.

## 1. Audit (read only)

Run `how` on each area, fanned out with `swarm` when the repo is large. Measure, do not guess. For each row, record the command you ran and its count.

| Area | Measure |
|---|---|
| Instruction file | One root `AGENTS.md`, under about 200 lines, routing through `poteto-mode`; no `CLAUDE.md` copy |
| Gates | Formatter, type-aware linter, strict type check, dead-code check, tests, and one check command. Local hooks (pre-commit, pre-push, `verify` evidence) if there is no CI. With CI, each job's command also runs in a local hook; a check only CI runs is a gap (a CI-only `bundle-budget` let a red build reach `staging` twice in one release) |
| Ratchets | A baseline file with target 0 per rule; counts per rule today |
| Typing | `any`, casts, non-null assertions, untyped JS files |
| Shape | Files over the line limit, long functions, deep nesting, duplicates (jscpd), single-caller helpers, functions with a CRAP score of 10 or more (complexity joined with coverage, `unclebob/crapper`; a flat `switch` or lookup table is exempt; without the tool, mark it missing and propose it) |
| Errors | Swallowed errors, try/catch around own code, retries outside the one owner |
| Tests | A test for each behavior a caller relies on (policy, Tests and proof), not one per entry point; tests of a constant, config, prose or file existence to delete; recorded contract fixtures for external APIs; slow or sleeping tests; surviving mutants in tested code (Stryker for TypeScript), as a ratchet; without the tool, mark it missing and propose it |
| Boundaries | Import rules, one home per concept, parked or out-of-scope code |
| Guardrails | Agent hooks that block gate skips and protected pushes; secrets out of the tree; on GitHub, `delete_branch_on_merge` on (a stacked PR merged into its already-merged base is lost) and the CI jobs required on the integration branch |
| Approval text | Repo instruction text (`AGENTS.md`, repo skills) that requires an ask before a reversible step on a work branch (commit, push, opening a PR) conflicts with the global policy's Approvals. Flag it with `file:line` and rewrite it to match. It cost waits of 9 to 67 minutes in two repos |
| Agent seats | A repo agent that shares a global seat's name (`senior-reviewer`, `poteto-agent`) and pins a lower model than the seat in `skills/pstack-local/models.md`. Flag it |
| Verification | A verification skill with a CLI and feature maps; parity against staging or the base |
| UI (if any) | Raw tables, raw hex colors, screens without 390 and 1440 px checks, tap targets |
| Runtime | One pinned version everywhere |

## 2. Report

Write `.pstack/gap-report.md` (or the path the user names), in plain STE-style prose:

1. Score per area: met, partial or missing, with the measured count.
2. Gaps ranked by risk times reach: data loss, security and money first, then gates (they make every later step safe), then readability.
3. One step per gap, each with **Goal**, **Done when**, **Evidence**, **Constraints** and **Stop when**, and an estimate.
4. The decisions the user owns, in one bundled ask with a recommended option first (`foundation`, "Where Kolin steps in").

Stop here and send the report unless the user already asked you to close the gaps.

## 3. Close (one gap per step)

- Before the first step, send the decision bundle and wait for its answers, including scope Kolin may cut (UI, CI). Do not prototype an option he has not picked. List the open PRs (`gh pr list`) and fold or avoid any that touch the same files.
- Gates first: add the missing gate, seed it at today's count, prove it flags one case and passes one.
- Then drive counts down, a codemod first (`principle-build-the-lever`), then small lanes. Each step is one verified commit-sized change on a branch; commit and push it under the policy's Approvals rule.
- A split cuts at a seam: the new module owns one concept and takes a few inputs. A hook or component that takes 10 or more inputs only moves lines; it does not close a file-length gap. Record the file as open instead.- Each repeated mistake found becomes a rule through `correct`.
- After each step and before the next one starts, rerun the audit rows the step touched and update the report: counts before and after, the next step. Never defer the re-audit to a final wave.
- After each step, write the resume point to `.pstack/status.md`, so a session limit loses no work.

## 4. Done

Every area is met, every ratchet baseline is deleted (zero allowance), the local gate passes at the tip, and the re-audit is clean. Report the final table and anything the user chose to leave open.

# Plan: fewer rules, more judgment

Draft, 2026-10-28. Nothing here is built yet.

## Goal

The model gets three things from this repo: hard limits it cannot infer, Kolin's taste, and knowledge it does not have. Everything that tells it *how to work* step by step goes, unless the same mistake has cost real time twice.

Success is measured, not felt: on the same task set, the lean setup costs fewer tokens and causes no more rework or review findings than today's setup.

## Where we are

Three cuts already landed in the last 30 hours:

| PR | Cut |
|---|---|
| #65 | Process hooks (edit-guard, fix-rounds, mode-reminder, main-session shell-edit block, fork deny). Policy from 139 lines to the outcome rules. senior-reviewer from 28 KB to 6 KB. |
| #67 | poteto-mode and foundation off the default route. builder-context injection deleted. |
| #68, #69 | foundation and full-stop trimmed. Every file reworded. |

The hook blocks in the 2026-10-26 baseline came almost all from hooks that #65 deleted. In the last day, the hooks that still exist blocked about 20 calls (sleep polls, forbidden git, context budget). Hooks are no longer the main load.

What is left, by weight:

```
Always in context (every session)        Pulled in during work (last 14 days, SKILL.md reads)
──────────────────────────────────       ──────────────────────────────────────────────────
Harness prompt (T3 Code, Claude Code)    poteto-mode (pstack, upstream)   515
MCP instructions + tool names:           pstack-local                     124
  Vercel 244, Supabase 28, Asana 41,     gap-audit                         54
  BigQuery 9, Shopify, Claude Docs       foundation                        52
policy/AGENTS.md         ~620 words      principle-* leaves (pstack)       ~90
STE Visual style         ~150 words      user-notes 20, break-ui 15,
repo AGENTS.md           ~450 words      mobile-native 6, full-stop 6
skill descriptions       ~20 lines
10 hooks                 (~20 blocks/day)  senior-reviewer: 70 runs, 90M tokens in 1 day
```

The largest piece of always-on context is not ours: the harness prompt and the MCP servers. The largest piece we own is pstack, through poteto-mode and pstack-local.

## The sorting rule

Each file goes into one of four groups.

| Group | Test | Action |
|---|---|---|
| **Limit** | A wrong call is unsafe, irreversible, or Kolin's to make | Keep, short |
| **Taste** | Kolin wants it and a model would not do it untold | Keep, one line each |
| **Knowledge** | Facts or catalogs the model lacks | Keep as a skill, cut its procedure |
| **Method** | How to plan, split, review, ship, write | Cut, unless a measured mistake repeats |

## Stage 0: measure first

Without this, we cannot tell if a cut helped or hurt.

1. Pick 4 real tasks: one bug fix, one small feature, one UI change, one PR takeover. Use closed work from hj-supply-chain or hj-portal so the right answer is known.
2. Run each on today's setup. Record tokens, tool calls, subagents, review findings, Kolin's grade and the rework PRs. `context-audit --sessions` and `context-audit --pr` give most of it.
3. After each stage below, rerun the same 4 tasks.

This also replaces the audit planned for 2026-11-04 with a controlled comparison.

## Stage 1: pstack (largest lever we own)

pstack brings poteto-mode (20 KB), about 20 principle leaves, and its own flow names (Autonomy, Shipping, Babysit). `pstack-local` exists only to bend pstack to Kolin's rules. Its "Where Kolin's rules win" section is a list of conflicts.

| File | Action |
|---|---|
| `upstream/vendor.json` `pstack` entry | **Remove.** Keep `deslop`, `control-ui`, `control-cli`, `thermo-nuclear-code-quality-review`. |
| `skills/pstack-local/` (SKILL.md, models.md) | **Delete.** Nothing left to adapt. |
| `bin/kolin-skills` `SIZE_BUDGETS` | Drop the `pstack-local` row. |
| `cursor/agent-policy.mdc` | Drop the pstack-local sentence. |
| `README.md` | Drop the pstack sections. |
| `skills/loop-refactor-to-pstack/` (25K words, 46 sessions in 30 days) | **Decision for Kolin.** It is built on pstack. Options: (a) archive it to a branch, (b) keep pstack only for this skill as an explicit `/loop-refactor-to-pstack` dependency. |

If a pstack principle earned its place, copy the one line into `policy/AGENTS.md` under Code. Candidates: "fix the root cause", "test behavior, not implementation". Both are already in the policy in some form.

## Stage 2: process skills

| Skill | Group | Action |
|---|---|---|
| `foundation` | Method + Knowledge | Delete "The flow", "Where Kolin steps in" and "Guardrails" (the policy's Approvals already covers them). Keep "Layout", "Quality bars" and `references/ui-bar.md` as reference. Rename to `repo-standard` so it does not read as a flow. |
| `gap-audit` | Method | Merge into `repo-standard` as one short section: "To audit a repo, compare it against this file and list the gaps by cost." Delete the 4-phase loop. |
| `full-stop` | Method + Limit | Cut the 11-step flow to the parts a model gets wrong: the ready checklist, the stop rules and the report line `Ready for Kolin to merge.` Target under 300 words. |
| `full-send` | Limit | Keep. It is the merge-permission scope, and it is user-invoked. |
| `modernize` | Method | Cut to "decide first if it should still land, keep the author's intent and credit". Under 200 words. |
| `council` | User-invoked | Keep. No cost unless invoked. |
| `explainer`, `user-notes` | Knowledge (format) | Keep. |

## Stage 3: knowledge skills

Keep the facts. Cut the procedure and the forced output shapes.

| Skill | Action |
|---|---|
| `break-ui` (1,756 words + CATALOG) | Keep `CATALOG.md` and the 4 hard rules. Cut the 6 phases and the "Required Output Format". |
| `emil-design-eng` | Keep. Already trimmed in #69. |
| `mobile-native` | Keep. |
| `local-supabase` | Keep. Remove the Docker deny in `hooks/bash-guard.py` only if Stage 0 shows the skill alone prevents Docker databases. |

## Stage 4: policy and style

`policy/AGENTS.md` renders to `~/.claude/CLAUDE.md`, `~/.codex/AGENTS.md` and `~/.grok/AGENTS.md`.

| Section | Action |
|---|---|
| Working | Cut "Do the work yourself..." to one line. The subagent rules move to the agent descriptions, where the harness already reads them. |
| Approvals | Keep as is. |
| Code | Keep the taste lines. Cut "Extend the owner..." and "Files stay under 1,000 lines" (the gate enforces the line limit). |
| Security | Keep as is. |
| Done | Keep "Done means proven on the real artifact" and the gate line. Cut the test-style sentences to one. |
| Pull requests | Change "A fresh `senior-reviewer` reads the diff before the PR opens" to: only for a PR over 150 changed lines, or one that touches schema, auth, access, money or a migration. |
| Writing | Delete. `claude/output-styles/ste-visual.md` already says it for Claude. Keep one sentence for Codex and Grok. |
| Adding rules | Keep. It is the brake on regrowth. |

Target: under 2,500 characters (today's `SIZE_BUDGETS` row is 4,500). Lower the budget to match, so the policy cannot grow back silently.

## Stage 5: agents and hooks

| File | Action |
|---|---|
| `agents/senior-reviewer.md` | Keep the two passes. Make "Skip" the default under 150 lines, so the policy change in Stage 4 and the agent agree. |
| `agents/poteto-agent.md` | Rename to `builder` (the name points at pstack). Cut "Spend" to one line. |
| `agents/haiku-worker.md` | Keep. |
| `hooks/agent-default-model.py` | Keep the Opus-on-editor deny (cost). Re-test the `isolation: worktree` deny: if the harness now runs gate commands in a worktree, delete it. |
| `hooks/bash-guard.py` | Keep the sleep and curl blocks (they hang the turn). Docker block: see Stage 3. |
| `hooks/block-env-reads.py`, `hooks/gate/*` | Keep. Security and protected branches. |
| `hooks/lint-changed-lines.py` | Keep. It informs, it does not block. |
| `hooks/context-budget.py`, `compact-context.py`, `keep-awake.py`, `mcp-access.py`, `heavy-slot.py` | Keep. They do not constrain the model. |
| `tests/` | Delete the cases for each removed hook branch and skill. |

## Stage 6: outside this repo

These cost context in every session and this repo does not control them yet.

| Source | Action |
|---|---|
| MCP servers (Vercel 244 tools, Supabase, Asana, BigQuery, Shopify, Claude Docs) | Turn each off by default. Turn one on per project in that project's `.mcp.json` or settings. Supabase `execute_sql` failed 32 of 32 times in the baseline. **Decision for Kolin:** which servers each project needs. |
| `claude/settings.json` `skillOverrides` | Keep. It already hides the bundled skills. |
| T3 Code orchestration prompt | Not ours. No action. |

## Order and size

```
Stage 0 measure ──► Stage 1 pstack ──► rerun ──► Stage 2+3 skills ──► Stage 4+5 policy, agents, hooks ──► rerun ──► Stage 6 MCP
   (1 session)       (1 PR)                        (1 PR)               (1 PR)                                       (settings, per project)
```

Each stage is one PR on a work branch, gated by `kolin-skills check`. Every cut is reversible with `git revert`.

## Decisions for Kolin

1. Drop pstack from `upstream/vendor.json`? Recommended: yes.
2. `loop-refactor-to-pstack`: archive it, or keep pstack only for it? Recommended: archive, and rebuild it without pstack if a repo needs it again.
3. senior-reviewer only above 150 lines or for schema, auth, access, money and migrations? Recommended: yes.
4. Which MCP servers stay on by default? Recommended: none, enable per project.
5. Which 4 closed tasks make the Stage 0 set?

## Rollback rule

If a rerun shows more rework or a repeated mistake, add back the one line that prevents it, not the whole file. That is the policy's Adding rules bar.

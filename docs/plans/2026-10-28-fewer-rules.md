# Plan: pstack as the one method

Draft 2, 2026-10-28.

## Status

Stages 1–4 shipped in one PR. Where the build differs from the plan below:

- `gap-audit`'s audit table is knowledge, so it moved into `repo-standard` ("Audit a repo"). Only its close loop was cut.
- `foundation`'s two check points (the multi-phase plan and the exemplar feature) are approvals, so they moved into the policy's Approvals list.
- `break-ui` keeps its phases, which are mostly failure signatures and truncation rules. Only the forced output format was cut.
- `pstack-local` keeps the PR body and reply-style overrides, because `pr-body` and the STE style still differ from pstack.
- The policy is 3,391 characters, not under 2,500. The rest is Approvals and Security. `SIZE_BUDGETS` is 3,500.
- The `isolation: worktree` deny in `hooks/agent-default-model.py` was not re-tested.

Open: Stage 0 (the baseline replay) and Stage 5 (MCP connectors, by hand).

## Goal

pstack is the method: how to plan, build, review and ship. Kolin-Skills adds only what pstack lacks:

| Layer | Holds | Lives in |
|---|---|---|
| Limits | Approvals, security, product guards | `policy/AGENTS.md` |
| Taste | Where Kolin's code bar differs from pstack (no comments, test scope) | `policy/AGENTS.md`, one line each |
| Harness map | pstack's Cursor tools, models and paths on this machine | `skills/pstack-local/` |
| Knowledge | Facts pstack does not have (UI craft, phone tells, local Supabase, repo layout) | Own skills, no procedure |
| Tooling | `kolin-skills`, `pr-body`, `context-audit`, hooks | `bin/`, `hooks/` |

Any own file that tells a model how to work, where a pstack playbook already says it, goes.

## Why the setup feels heavy

There are two method layers, and they overlap:

```
                 pstack (method)                         Kolin-Skills (also method today)
                 ───────────────                         ────────────────────────────────
Plan             multi-phase-plan, figure-it-out,   ◄──►  foundation  "The flow", "Where Kolin steps in"
                 orchestrate
Audit a repo     how (census), loop-refactor Phase 0 ◄──► gap-audit   4-phase loop
Open a PR        opening-a-pr                        ◄──► full-stop   steps 1–8
Drive to green   babysit                             ◄──► full-stop   steps 9–11
Land             shipping                            ◄──► full-send   merge step
Review           interrogate + deslop + no-comments  ◄──► senior-reviewer before every PR
Write            unslop, technical-writing,          ◄──► policy "Writing" + STE Visual style
                 "Writing the reply"
Adapter          (none)                              ──►  pstack-local "Where Kolin's rules win"
```

Each row is two sets of rules for one job. Where they differ, the model has to reconcile them, and `pstack-local` is a list of those differences. Remove the right column wherever pstack covers it, and the conflicts go with it.

The hooks are not the main load anymore. #65 deleted the ones behind the 2026-10-26 block counts. In the last day, the hooks that still exist blocked about 20 calls.

## Stage 0: measure first

Replay 4 closed tasks from their parent commit, in a fresh worktree, with the prompt Kolin would have typed. Compare each result to the merged PR.

| Task | Kind | Why it is a good test |
|---|---|---|
| hj-supply-chain #948 | Bug fix (+21/−30) | A real bug (Clear filters vs stored column filters before the grid mounts) that review graded B− in release #926 |
| hj-supply-chain #944 | Refactor (+25/−16) | A duplicate `parseUpcList` that review missed the first time |
| hj-supply-chain #957 | Feature (+294/−111) | Medium feature that follows an existing pattern (the supply plan's Incoming row) |
| hj-portal #630 | UI behavior (+181/−32) | Filter that applies while typing and persists across navigation |

Record per run: tokens, tool calls, subagents, review findings, diff size against the merged PR, and Kolin's grade. `context-audit --sessions 1` gives the first three.

Run the set once now, and again after Stages 1–2 and 3–4.

## Stage 1: pstack is the default route

PR #67 took `poteto-mode` off the default route. Put it back as the one method:

| File | Change |
|---|---|
| `policy/AGENTS.md`, Working | Add: "For code work beyond a one-line change, follow `poteto-mode`, read through `pstack-local`." |
| `agents/poteto-agent.md` | Keep Kolin's version (the brief quotes the principles, and the builder does not read the 20 KB file). It already overrides pstack's own `poteto-agent`. |
| `skills/pstack-local/SKILL.md` | Keep the term map and model roles. Cut "Where Kolin's rules win" to the overrides that remain after Stage 2 (see below). |
| `upstream/vendor.json` | Keep pstack. Move the `rev` pin forward when upstream changes. |

## Stage 2: own skills that duplicate a playbook

| Skill | pstack covers it with | Action |
|---|---|---|
| `foundation` | multi-phase-plan, figure-it-out, orchestrate, feature | Delete "The flow", "Where Kolin steps in" and "Guardrails". Keep "Layout", "Quality bars" and `references/ui-bar.md`. Rename to `repo-standard`, so "foundation" means pstack. |
| `gap-audit` | `how` census, `loop-refactor-to-pstack` Phase 0 | Delete. "Audit this repo" becomes Phase 0 of `loop-refactor-to-pstack`, read-only, measured against `repo-standard`. Its split loop caused the reverted work in #926 (#930). |
| `full-stop` | opening-a-pr, then babysit `drive` | Cut to a short alias: run opening-a-pr, then babysit until merge-ready, then report `Ready for Kolin to merge.` Keep only the ready checklist. |
| `full-send` | shipping | Keep as the merge permission. Point its merge step at the shipping playbook. Keep the migration and promotion checks (they are limits). |
| `council` | interrogate (multi-model) | Keep. pstack roles run on Claude only, so this is the one cross-provider review, and it is user-invoked. |
| `modernize` | none | Keep. |
| `loop-refactor-to-pstack` | built on pstack | Keep. Add the read-only audit entry from `gap-audit`. |
| `break-ui`, `emil-design-eng`, `mobile-native`, `local-supabase`, `explainer`, `user-notes` | none | Keep as knowledge. `break-ui`: keep `CATALOG.md` and the 4 hard rules, and cut the 6 phases and the forced output format. |

After this stage, `pstack-local` "Where Kolin's rules win" keeps only:

- **Autonomy.** pstack lets external actions (team chat, tickets) run without asking. Kolin's Approvals list wins.
- **Comments.** pstack keeps a non-obvious why. Kolin keeps none.
- **Tests.** Only for a named behavior a caller relies on. No snapshot.
- **Builder brief.** The builder does not read `poteto-mode`.

The PR body and reply-style overrides go. The PR body follows pstack's opening-a-pr, filled from `pr-body <base>` when the repo has no template.

## Stage 3: one review, one writing system

| Item | Change |
|---|---|
| Review | One fresh review before a PR opens. In a pstack run, that is `interrogate`, with `senior-reviewer` as its Claude reviewer seat in `pstack-local/models.md`. Outside pstack, `senior-reviewer`. Skip it under 150 changed lines unless the diff touches schema, auth, access, money or a migration (`senior-reviewer` "Scale to the diff" already says this; the policy line is changed to match). |
| `policy/AGENTS.md`, Writing | Delete. pstack's unslop and "Writing the reply" govern prose. |
| `claude/output-styles/ste-visual.md` | Keep rules 1–4 (lead with the result, diagram, explainer offer, full detail for errors). They are layout, and they do not conflict with pstack. |

## Stage 4: policy size and hooks

| File | Change |
|---|---|
| `policy/AGENTS.md` | Keep Approvals, Security, Code taste, Done, Adding rules. Remove the lines the gate already enforces ("Files stay under 1,000 lines"). Target under 2,500 characters, and lower `SIZE_BUDGETS` in `bin/kolin-skills` to match. |
| `hooks/agent-default-model.py` | Re-test the `isolation: worktree` deny. If the harness now runs gate commands in a worktree, delete that branch. Keep the Opus-on-editor deny. |
| `hooks/bash-guard.py` | Keep the sleep and curl blocks. Keep the Docker block (cheap, and it backs `local-supabase`). |
| Other hooks | Keep. They protect secrets and protected branches, or only inform. |
| `tests/` | Remove cases for each deleted branch or skill. |
| `README.md` | Rewrite the skills table around the two layers. |

## Stage 5: MCP servers off by default

Every MCP server costs context in each session. Supabase `execute_sql` failed 32 of 32 times in the baseline.

| Change | Where |
|---|---|
| Turn off every claude.ai connector by default (Vercel, Supabase, Asana, BigQuery, Shopify, Claude Docs) | claude.ai connector settings (Kolin, by hand) |
| Turn one on per project where it is used | That project's `.mcp.json` or `.claude/settings.json` |

## Order

```
Stage 0 baseline ─► Stage 1+2 (1 PR) ─► rerun ─► Stage 3+4 (1 PR) ─► rerun ─► Stage 5 (settings)
```

Each PR goes on a work branch, gated by `kolin-skills check`. Every cut can be reverted with `git revert`.

## Rollback rule

If a rerun shows more rework or a repeated mistake, add back the one line that prevents it, not the whole file.

## Decisions already made (2026-10-28)

1. pstack stays, and it is the foundation.
2. `senior-reviewer` only above 150 lines, or for schema, auth, access, money and migrations.
3. No MCP server on by default.
4. Stage 0 tasks: the 4 above.

## Open

- Stage 1 puts `poteto-mode` back on the default route. That reverses part of #67, and it brings back a 20 KB read in each main session (not in builders). The Stage 0 rerun shows whether removing the duplicate own skills more than pays for it.

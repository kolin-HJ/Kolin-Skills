# Haiku worker cases

Four merged mechanical changes from hj-supply-chain, frozen as a base commit, a brief and the expected diff. They measure whether the `haiku-worker` agent (`~/.claude/agents/haiku-worker.md`, `claude-haiku-5-5`, medium) does a recipe lane as well as a Sonnet 5.5 worker given the same brief, and at what total cost once the advisor's review is counted. Results and the routing recommendation are in `report.md`.

| Case | Kind | Source commit | Traps |
|---|---|---|---|
| `renumber` | rename | `6651e592` | five `0163` hits mean the Demand tab ADR; the migration id lives in TypeScript |
| `adr-sync` | doc sync | `2938f742` | "as it was" sections and old-URL examples stay; two other ADRs are out of the file list |
| `dead-exports` | codemod | `9d9740e1` | `formatDay` from `@/lib/dates` must not be renamed |
| `modal-shell` | codemod | `c2c37999` | two of four candidates do not fit `ModalShell` and must be stopped on |

`expected/dead-exports.patch` drops the merged commit's `tags` to `labels` test rename, because `pnpm deadcode` does not report it at the base and the brief does not ask for it.

## Run

1. `node prepare.mjs <hj-supply-chain checkout> <empty dir outside it> [case]`. It adds one detached worktree per case and worker at the case's base, runs `pnpm install`, and writes `<case>-<worker>.brief.md` with the worktree path filled in. This folder lives outside the repo so a worker never finds the expected diff.
2. Spawn the workers in parallel, one per brief. Haiku: `subagent_type: haiku-worker`. Sonnet: a general-purpose agent with `model: sonnet`, told to read the body of `haiku-worker.md` as its rules. Both get only the brief's path.
3. For each finished worker, spawn an advisor (general-purpose, `model: opus`) with `advisor.md` filled in. It sees the brief, the diff and the worker's report, never `expected/`. On REVISE, send its MESSAGE TO WORKER to the same worker with SendMessage, then send the new report back to the same advisor. Stop at ACCEPT or after three worker rounds.
4. Record each run in `runs/agents.tsv` (`case, worker, rounds, worker_agent, advisor_agent`). A revise round resumes the same agents, so one transcript holds every round.
5. Score each run: `node score.mjs <runs dir> <case> <worker>` reruns the case's gates plus `oxfmt --check` on changed code files and counts hunks that differ from `expected/`. Score traps by hand from the diff and the report against `cases.json`.
6. Tokens and cost: `node summarize.mjs <subagents dir>` prints the per-run table from `runs/agents.tsv`. `node usage.mjs <subagents dir>/agent-<id>.jsonl ...` sums one transcript. Transcripts live under `~/.claude/projects/<project>/<session>/subagents/`. The script dedupes streamed lines by message id and applies the Haiku long-context tier per request.
7. Remove the worktrees with `git worktree remove --force` when done.

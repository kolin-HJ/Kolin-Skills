# Reviewer cases

Four changes frozen as a base commit plus a stored patch and description, with the findings a good review of each must reach. Three are open PRs (#587, #588, #589) at the head commits in `cases.json`; one (`dock-week`) is a clean one-line commit where the right verdict is Ship, so a reviewer that always blocks cannot score well. They measure the `senior-reviewer` brief (`~/.claude/agents/senior-reviewer.md`) the way a test measures code: change the brief, rerun the cases, compare.

## Run

1. `node ~/.agents/evals/senior-reviewer/prepare.mjs <hj-supply-chain checkout> <empty dir outside it>`. For each case it adds a worktree at `base` under a project-shaped name, stages `<id>.patch`, installs dependencies, copies the description next to it and prints the reviewer prompt. This folder lives outside the repo, beside the brief it measures, so a reviewer never finds the expected findings and repo searches never hit the frozen diffs.
2. Spawn one reviewer per prompt, in parallel. Claude Code reads agent definitions when a session starts; to measure an edited brief in the same session, give a general-purpose agent on the reviewer's model the brief's body as its instructions.
3. Score each report against `cases.json` into a new column of `scores.tsv`. A finding counts 1 when stated with the right file, 0.5 when mentioned but waved through. The verdict must match.
4. Remove the worktrees with `git worktree remove` when done.

## Results

One run per cell, Sonnet 5.5 at medium effort, scored by hand on 2026-10-01. Per-finding scores are in `scores.tsv`.

| | Old brief, run 1 | Old brief, run 2 | Revised brief |
|---|---|---|---|
| All 20 expected findings | 8.5 | 6 | 12.5 |
| The 11 findings the author listed before any reviewer ran | 3.5 | 2.5 | 5 |
| Verdicts right (of 4) | 2 of 3 run | 2 of 3 run | 4 of 4 |

Read the totals with two cautions. First, nine of the 20 expected findings (`source` = `reviewer` in `cases.json`) were first raised by a reviewer run, several by the revised brief itself, so the full total favors it; the author-only row is the fairer comparison. Second, two old-brief runs on the same case differed by three points, so one run per cell is noise-sized for small gaps. The verdicts are the clearest signal: the old brief said Ship on two changes that should not land, and the revised brief blocked both while still passing the clean case.

The revised brief adds three sweeps (duplication by role, scope against the task, proof per behavior), a coverage list and a verdict decided in a fixed order. Still missed by every run: the client copy of the invite rule, the duplicate `UserAccess` type, the dead `demand.topdown.edit` permission and the ADR paragraph that restates its route.

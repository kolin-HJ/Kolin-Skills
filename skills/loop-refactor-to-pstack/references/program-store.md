# Program store

The store is the Orchestrate playbook's store (`poteto-mode/playbooks/orchestrate.md`, Store layout), placed in a gitignored folder of the repo such as `.verify/orchestrate/<program>/`. Committed artifacts live elsewhere: the plan in `.pstack/program.md`, the decision trail in `.pstack/decision-log.tsv`, decision records in `docs/adr/`.

## Create it once

```bash
export ORCH_STORE=<repo>/.verify/orchestrate/<program>
alias orch="bun ~/.agents/skills/poteto-mode/scripts/orch/orch.ts"
orch init                                  # gates.md inbox/ ledger.tsv preferences.md units.tsv; frontier.json stays unused on one branch
mkdir -p "$ORCH_STORE/briefs" "$ORCH_STORE/reports" "$ORCH_STORE/research"
cp ~/.agents/skills/loop-refactor-to-pstack/assets/commit-unit.sh "$ORCH_STORE/"
git check-ignore -v "$ORCH_STORE/RESUME.md"  # must print an ignore rule
```

Each file has one writer, the coordinator. Workers write only `reports/<brief>.md`.

| File | Holds | Written by |
|---|---|---|
| `RESUME.md` | The resume note below | Rewritten at the end of every iteration |
| `preferences.md` | The numbered standing orders | `orch standing add "<line>"`, the moment an order is given |
| `units.tsv` | One row per unit: id, track (the wave), state, branch, PR, SHA, brief | `orch unit add`, `orch unit set`; `commit-unit.sh` marks a unit `committed`; every unit becomes `landed` when the program PR merges |
| `ledger.tsv` | One verdict per unit commit, keyed by the program PR and the commit SHA | `orch ledger record <pr> <sha> <verdict> --evidence <path> --verifier <name>`. The PR must be a number, so before the program PR opens, keep verdicts in the trail and copy them in when it opens. |
| `inbox/` | Completion pointers | `orch inbox push` on each notification; `orch inbox drain` at drain points |
| `gates.md` | Questions parked for the user, with a default | `orch gate park <id> --question … --options … --default …` |
| `status.md` | Derived counts | `orch status`, never by hand |
| `briefs/`, `reports/`, `research/` | Briefs, worker reports, census and audits | Coordinator, workers, audit agents |

Verdicts, strongest first: `live-ui-verified` (parity or a driven recipe), `unit-test-verified`, `type-check-only`, `verifier-blocked`, `verifier-failed`. A refactor unit needs `live-ui-verified`. A new head SHA voids its row.

Wave and unit ids must be unique. List `briefs/` and `orch unit list` before naming one.

## RESUME.md

Keep it under about 60 lines. After a compaction or in a new session, read it first, then `preferences.md`, then run "Check state". Replace the state section each iteration; never append history to it. History belongs in `.pstack/decision-log.tsv` and git.

```markdown
# Resume note: <program name>

## Where
- Worktree <absolute path>, program branch <name>, cut from <base> <sha>. Program PR <url or "not open yet">.
- Last base merge: <base sha> in <merge commit sha>. Last push: <sha>.
- Store <this folder>. Plan .pstack/program.md. Trail .pstack/decision-log.tsv.
- Scratch checkouts for parity: <base>, <head>. Never install, init or delete inside them.

## Permissions the user gave
- <exact approvals, for example: one local commit per verified unit; merge the base and push the program branch at each wave boundary; one program PR into the base; no merge or deploy without a fresh yes>

## Check state
    cd <worktree>; export ORCH_STORE=<store>
    orch unit counts; orch gate list; orch inbox count
    <check command>; <gates:status>
    git log --oneline <base>..HEAD | head -30

## Where it stood (<date>)
HEAD <sha>. Check command exit <n>. Baselines left: <gate n, …>, including the `effect-adoption` total.
Committed since the last push: <commits, one line each>.
In flight: <lanes, brief paths, parity run folder>.
Leftovers with reasons: <site: why, and the unit that unblocks it>.
Next, in order: <waves>.
Needs the user: <gate ids from gates.md>.
Coordinator lessons: <one line each; fold recurring ones into the skill at close>.
```

## preferences.md: standing orders

Number the orders so a brief can cite one ("order 12"). Paste them verbatim into every spawn and resume. These carry over to any repo; fill in the specifics.

1. **Where.** All work happens in `<worktree>` on the one program branch `<branch>`. Workers never create a branch or worktree, and never commit, push, stash, check out, reset, rebase or open a PR. The coordinator commits each verified unit, merges the base and pushes. Nobody rebases, amends or force-pushes the program branch.
2. **Shared tree.** Workers write only the paths in their brief's SCOPE and preserve everyone else's edits. They format only the files they changed.
3. **Behavior.** Behavior does not change unless the brief says so. A unit is done only when the parity recipes it touches show no change.
4. **No comments.** Code carries no comments. A comment that records a real decision moves into a name, a type, a test or an ADR in the same unit.
5. **Deletions.** A worker deletes a tracked file only when the brief names it. A refused deletion stops the worker, who reports it.
6. **Tests.** A test calls the code the way its caller does and asserts a literal. A new test is seen failing without the change, and the report says how it failed. No module mocking; a test swaps a seam (for Effect code, a test layer).
7. **Never written:** `<production, external services, shared databases, chat>`. The app is driven only through the verify CLI against a local instance.
8. **Types.** No `any`, no `as` except right after a validated decode, no non-null assertion, no file over 1,000 lines, imports at the top of the module.
9. **Stop.** If a VERIFY command fails twice after a reasonable fix, or the work needs a path outside SCOPE, the worker stops and reports.
10. **Baselines are the coordinator's.** Workers never write baseline files, lint overrides or gate policy. After a fix, `gates:files` shows only stale entries for their files and no rise anywhere.
11. **Reports.** The full report goes to `reports/<brief name>.md`. The final message is at most 15 lines: status, files changed, gate results, decisions needed, the report path.
12. **Subagents.** A worker spawns no sub-workers, except one read-only reviewer it waits for.
13. **The user's bar,** quoted, for example "everything still functional as it is in the base branch, no bugs, nothing broken". Every wave ends with lockstep parity and the check command.
14. **Zero, not shrink.** Every baseline is burned to zero and deleted. A new rule lands at zero, or with its baseline and the unit that burns it down.
15. **Scratch checkouts are shared.** Never install, init or delete inside one. Fixture repos go in new `fx-<lane>` folders.
16. **Subagents** run through `poteto-agent` (or the repo's named implementer), `senior-reviewer` and `comment-sicko`, launched without a `model` argument so each definition's model applies. Never `general-purpose` or `Plan` for program work (`references/subagents.md`).
17. **Live data.** When a check needs real values, query the source of truth read-only, and never copy the values into code, briefs or reports.
18. **Decisions toward the goal.** If the user grants it, reversible decisions that serve the goal proceed and are recorded in the commit message and the trail. Push, merge, deploy and external writes still need a fresh yes.
19. **Gate changes.** Every edit to gate code, gate policy, CI, hooks or agent settings is its own unit, with tests that plant the loosening it guards against. Workers edit them only when their brief names the file.
20. **Refusals.** A permission refusal goes to the user verbatim. No agent retries it by another route.
21. **Effect.** Effectful server code is written in Effect through the paved modules in `references/effect.md`: services with layers, tagged errors, Schema at boundaries, the one runtime at the edge. Pure functions stay plain functions. A raw `Effect.run*` outside the edge modules is a defect.
22. **Landing.** The program lands as one PR from `<branch>` into `<base>`. <the user's choice, for example: merge the base and push at every wave boundary; open the PR after Phase 1; the user merges with a merge commit>.

## commit-unit.sh

Usage: `bash <store>/commit-unit.sh <unit-id> <message-file> <path>...`

It refuses a dirty index, stages exactly the given paths, and appends one trailer block holding `Unit: <id>` and `COMMIT_ATTRIBUTION` (set it to the harness's attribution line). Then it commits and marks the unit `committed` in `units.tsv`. `wave-table.mjs` reads the `Unit:` trailer, so commit every unit through this helper. Add each unit with `orch unit add` when you brief it, or the helper only warns. Pass paths explicitly; build lists from a file and pipe them through `tr '\n' '\0' | xargs -0`, because zsh does not split `$VAR`. Write each message to its own file.

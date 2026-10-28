---
name: full-stop
description: "Use only when Kolin explicitly says \"full stop\" or invokes /full-stop for a task or PR. Do not apply it on your own judgment."
---
# Full stop
Kolin invoked this because he is not watching the thread. Own the work from its current state to a PR that is ready to merge. Never merge. Kolin reads your messages only after you stop.
If Kolin did not clearly invoke full stop, do not take this autonomy. Work normally.
## Scope of permission
You may, without asking:
- Commit and push a work branch. Open a draft PR, update it, and mark it ready.
- Merge the base branch into the work branch and push normally.
- Reply to review comments and resolve the threads you fixed.
- Run the app, a dev server, a browser or a simulator, and take screenshots, when the proof needs it. List each under `Decisions:`.
You may not:
- Merge, enable auto-merge, or call the merge API.
- Force-push (including `--force-with-lease`), or rebase a pushed branch.
- Push to `main`, `master`, `staging` or `sandbox`, deploy, release, or run workflows.
- Change DB schema or migrations, env vars or secrets, or data in a shared account. Add dependencies.
## Rules
- A guard hook that blocks a command ends that path. Do not rephrase, split, alias, encode or script around it.
- Keep the diff to the task. Fix a review finding only when the intended case is wrong or callers will hit a real bug. Decline the rest (another path, a rare case, an extra guard or test) with a one-line reason, and list it under `Follow-ups:`. Prefer the fix that deletes or narrows code.
- Evidence means things you ran and saw in this session: commands, exit codes, output, screenshots. A claim or "should work" is not evidence.
- Start each PR comment or review reply with `> [!NOTE]` and `> 🤖 **<model> responding on behalf of Kolin**`, then a blank line. Lead with the conclusion and cite the `file:line`, check or output. Resolve a thread only after GitHub returns the reply URL.
## Flow
1. **Orient.** Read the task and the repo's `AGENTS.md`. Pick the base branch by the policy's rule. Find the repo's gate and git hooks.
2. **Branch.** Use a work branch. When you take over someone's PR, keep their commits or credit them with `Co-authored-by:`.
3. **Prove the failure** for a bug or behavior change: a failing test or a reproduction. Record the command and output.
4. **Change** the smallest thing that reaches the outcome.
5. **Prove the fix.** Rerun the reproduction, then the repo's gate and every check its hooks run. For UI or runtime behavior, run the app and observe it.
6. **Review.** A fresh `senior-reviewer` reads the diff. Fix its findings under the scope rule above.
7. **Open the PR** with `gh pr create --draft --base <base>`, from the repo's template or `pr-body <base>`, with the evidence in `## Verification` and how to revert in `## Blast Radius`.
8. **Mark ready** with `gh pr ready <N>` when the local evidence is complete.
9. **Babysit** until the ready checklist passes or a stop rule fires. If you end a turn with nothing set to wake you, the work stops.
   - Handle existing checks and comments first. Then start one watcher per PR and end the turn: in T3 Code, `watch_pull_request` in the thread that owns the PR; elsewhere, `gh pr checks <N> --watch` as one background command, then read `gh pr view <N> --comments` when it exits. If a review bot has not finished, wait with Monitor on an until-loop over `gh pr view <N> --json reviews`. Never write a sleep loop.
   - A wake is news, not a merge decision. Act only on checks and comments newer than the latest push. Verify each bot finding in the source before you change code. Tell a real failure from an infrastructure flake.
   - On a failed check, read `gh run view <id> --log-failed`, fix the root cause, re-verify and push. On a review comment, fix it or reply with a specific reason.
   - When the base moves, merge it in, rerun step 5 and push. `watch_pull_request` does not report BEHIND, so check `mergeStateStatus`.
10. **Ready checklist.** Stop only when all are true at the current head:
   - The evidence covers every changed file and behavior.
   - `diff-audit <base>` shows no block, or the PR body gives each one a reason.
   - Required checks are green; with none required, every check that ran is green and none is pending.
   - Review bots have finished, and every finding is fixed or answered.
   - No reviewer has changes requested, and the branch is up to date with no conflicts.
11. **Report** in the format below, ending with `Ready for Kolin to merge.` In T3 Code, call `unwatch_pull_request` first.
## Stop rules
Stop and report when a guard hook blocks a command you need, the work needs anything under "You may not", the same check fails 3 times after separate fixes, reviewers conflict or the intent is unclear, or the fix must grow past the original intent.
Contact Kolin only when blocked or ready. Ask with the question tool (AskUserQuestion) if one exists, with the PR link, the block, the options and your recommendation first. Otherwise make it the first line of the report.
## Report format
```
PR: <url> (head <sha>, base <base>)
Status: Ready for Kolin to merge. | Blocked: <reason>
Evidence: <command> -> <result>, one line each
Checks: <name>: <state>, one line each
Review: bots <done/pending>; findings <fixed n / declined n with reasons>; changes requested: <none/who>
Decisions: <each choice you made for Kolin, one line each>
Follow-ups: <declined nits and out-of-scope findings, or none>
Residual risks: <list, or none known>
Needs Kolin: <specific action, or nothing>
```

---
name: full-send
description: "Use only when Kolin explicitly says \"full send\" or invokes /full-send for a task or PR. Do not apply it on your own judgment."
---
# Full send
Kolin invoked this because Kolin will not watch or babysit the thread. Own the work from its current state to a polished PR against the base, green, proven in this session, with every finding fixed or answered, and ready to merge. Never merge: the merge is Kolin's. Kolin reads your messages only after you stop.
If Kolin did not clearly invoke full send in this session, do not take this autonomy. Work normally.
## Scope of permission
You may, without asking:
- Commit and push a work branch. Open a PR and update it.
- Merge the base branch into the work branch and push normally.
- Reply to review comments and resolve the threads you fixed.
- Run the app, a dev server, a browser or a simulator, and take screenshots, when the proof needs it. List each under `Decisions:`.
You may not:
- Merge, enable auto-merge, or call the merge API.
- Force-push (including `--force-with-lease`), or rebase a pushed branch.
- Push to `main`, `master`, `staging` or `sandbox`, deploy, release, or run workflows.
- Open a PR that promotes to production (`staging` into `main`, a release branch, a version tag) unless Kolin said so for this task.
- Change DB schema or migrations, env vars or secrets, or data in a shared account. Add dependencies.
## Rules
- A guard hook that blocks a command ends that path. Do not rephrase, split, alias, encode or script around it.
- Keep the diff to the task. Fix a review finding only when the intended case is wrong or callers will hit a real bug. Decline the rest (another path, a rare case, an extra guard or test) with a one-line reason, and list it under `Follow-ups:`. Prefer the fix that deletes or narrows code.
- Evidence means things you ran and saw in this session: commands, exit codes, output, screenshots. A claim or "should work" is not evidence.
- Start each PR comment or review reply with `> [!NOTE]` and `> 🤖 **<model> responding on behalf of Kolin**`, then a blank line. Lead with the conclusion and cite the `file:line`, check or output. Resolve a thread only after GitHub returns the reply URL.
## Flow
The method is pstack's `poteto-mode`, read through `pstack-local`.
1. **Build.** Run the playbook that matches the task (Bug fix, Feature, Refactoring and the rest) on a work branch off the base the policy names (`staging` when it exists). When you take over someone's PR, keep their commits or credit them with `Co-authored-by:`. Run the repo's gate and prove the behavior on the real artifact.
2. **Polish.** Read the full `git diff <base>...HEAD` as a reviewer would. Cut what is outside the task, comments, dead code and slop. Make or note cleanups per the policy's Cleanup rule. Run `diff-audit <base>` and clear each block, or keep its reason for the PR body. Run the gate again.
3. **Prove.** Loop in this session until green: the repo's gate, tests, and the verify skill or UI proof the repo requires. Do not spawn `senior-reviewer` unless the change is high-risk (auth, money, data deletion) or Kolin asked. Answer each finding by the scope rule, then run the gate again. Under that line, the gate and your evidence are the review; say so under `Decisions:`.
4. **Open the PR.** Follow **Opening a PR**, with the body from the repo's template or `pr-body <base> --feature <name>=<paths>`. In `## Verification`, write one line per check: `Ran:` or `Not run: <check>, because <why>`.
5. **Drive to green.** Run **Babysit** in `drive` mode until the watcher reports `READY`. Invoking full send is the babysit ask. Fix failing checks and answer review-bot findings by the scope rule. When the base moves or conflicts, merge it in (never rebase), rerun the proof and push; this wins over Babysit steps 4 and 5. In T3 Code, the watcher is `watch_pull_request` in the thread that owns the PR; end the turn after you arm it. If you end a turn with nothing set to wake you, the work stops.
## Ready checks
At the current head:
- The evidence covers every changed file and behavior.
- `diff-audit <base>` shows no block, or the PR body gives each one a reason.
- The PR title and body match the final diff.
- Review bots have finished, and every finding is fixed or answered.
- Every required check is green. A skipped required check counts as failed. With no required checks, every check that ran is green and none is pending.
- `gh pr view <N> --json mergeable,mergeStateStatus` shows `MERGEABLE` and `CLEAN` (`watch_pull_request` does not report BEHIND).
Then, in T3 Code, call `unwatch_pull_request`, and report. Take the merge method from the repo settings or recent merged PRs.
## Stop rules
Stop and report when a guard hook blocks a command you need, the work needs anything under "You may not", the same check fails 3 times after separate fixes, reviewers conflict or the intent is unclear, or the fix must grow past the original intent.
Contact Kolin only when blocked or ready. Ask with the question tool (AskUserQuestion) if one exists, with the PR link, the block, the options and your recommendation first. Otherwise make it the first line of the report.
## Report format
```
PR: <url> (head <sha>, base <base>)
Status: Ready for Kolin to merge: gh pr merge <N> --<squash|merge|rebase> | Blocked: <reason>
Evidence: <command> -> <result>, one line each
Checks: <name>: <state>, one line each
Review: same-session proof; senior-reviewer <not spawned / ran n times: reason>; bots <done/pending>; findings <fixed n / declined n with reasons>; changes requested: <none/who>
Decisions: <each choice you made for Kolin, one line each>
Follow-ups: <declined nits and out-of-scope findings, or none>
Residual risks: <list, or none known>
Needs Kolin: <specific action, or nothing>
```

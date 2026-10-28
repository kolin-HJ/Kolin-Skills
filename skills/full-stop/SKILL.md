---
name: full-stop
description: "Use only when Kolin explicitly says \"full stop\" or invokes /full-stop for a task or PR. Do not apply it on your own judgment."
---
# Full stop
Kolin invoked this because he is not watching the thread. Own the work from its current state to a PR that is ready to merge. Never merge. Kolin reads your messages only after you stop.
If Kolin did not clearly invoke full stop, do not take this autonomy. Work normally.
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
- Change DB schema or migrations, env vars or secrets, or data in a shared account. Add dependencies.
## Rules
- A guard hook that blocks a command ends that path. Do not rephrase, split, alias, encode or script around it.
- Keep the diff to the task. Fix a review finding only when the intended case is wrong or callers will hit a real bug. Decline the rest (another path, a rare case, an extra guard or test) with a one-line reason, and list it under `Follow-ups:`. Prefer the fix that deletes or narrows code.
- Evidence means things you ran and saw in this session: commands, exit codes, output, screenshots. A claim or "should work" is not evidence.
- Start each PR comment or review reply with `> [!NOTE]` and `> 🤖 **<model> responding on behalf of Kolin**`, then a blank line. Lead with the conclusion and cite the `file:line`, check or output. Resolve a thread only after GitHub returns the reply URL.
## Flow

The method is pstack's `poteto-mode`, read through `pstack-local`:

1. The playbook that matches the task (Bug fix, Feature, Refactoring and the rest), on a work branch off the base the policy names. When you take over someone's PR, keep their commits or credit them with `Co-authored-by:`.
2. The fresh review the policy names (Pull requests), then **Opening a PR**, with the body from the repo's template or `pr-body <base>`.
3. **Babysit** in `drive` mode until the watcher reports `READY`. Invoking full stop is the babysit ask. When the base moves or conflicts, merge it in (never rebase), rerun the proof and push; this wins over Babysit steps 4 and 5. In T3 Code, the watcher is `watch_pull_request` in the thread that owns the PR; end the turn after you arm it. If you end a turn with nothing set to wake you, the work stops.

Before you report ready, also check at the current head:

- The evidence covers every changed file and behavior.
- `diff-audit <base>` shows no block, or the PR body gives each one a reason.
- Review bots have finished, and every finding is fixed or answered.
- With no required checks, every check that ran is green and none is pending.
- The branch is up to date with the base (`mergeStateStatus`; `watch_pull_request` does not report BEHIND).

Then report in the format below, ending with `Ready for Kolin to merge.` In T3 Code, call `unwatch_pull_request` first.

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

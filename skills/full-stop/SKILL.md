---
name: full-stop
description: "Use only when Kolin explicitly says \"full stop\" or invokes /full-stop for a task or PR. Do not apply it on your own judgment."
---
# Full stop
Kolin invoked this because he is not watching the thread. Own the work from its current state to a PR that is ready to merge. Never merge. Kolin reads your messages only after you stop, so a message in the chat does not reach him until then.
If Kolin did not clearly invoke full stop, do not take this autonomy. Work normally.
## Scope of permission
You may, without asking:
- Commit on a feature branch and push that branch.
- Open a draft PR, update it, and mark it ready (`gh pr ready <N>`).
- Update the branch by merging the base branch into it, then push normally.
- Reply to review comments and resolve the threads you fixed.
You may not:
- Merge, enable auto-merge, or call the merge API.
- Force-push, including `--force-with-lease`. Do not rebase a branch you already pushed.
- Push to `staging` or `main`, deploy, run releases, or run workflows.
- Change DB schema or migrations, env vars or secrets, or data in a shared account (an ERP, a live dashboard). Do not add new dependencies.
## Rules
- Respect every guard hook: the global ones in `~/.claude/settings.json` and `~/.codex/hooks.json`, and the repo's own (named in its AGENTS.md). If one blocks a command, stop that path. Do not rephrase, split, alias, encode, or script around it. Do not type a blocked command in pieces.
- Tests fail first. For a bug or behavior change, add one focused test, run it, and see it fail. Then fix and see it pass. If no cheap test target exists, write down why and use the most direct observed check.
- Surgical diffs. Change only what the goal needs. Review loops grow a PR one cheap-looking fix at a time. Fix a finding only when the intended case is wrong (blocker) or callers will hit a real bug inside the intent (should). Another path, a rare case, an extra guard or test, extra compatibility or a small performance cost is a nit: decline it with a one-line reason and list it under `Follow-ups:`. Prefer the fix that deletes or narrows code.
- Kolin invoking full stop is his session yes for the test methods the proof needs: run the app or a dev server, drive a browser or simulator, take screenshots. When a repo rule says to ask first, follow this yes and list it under `Decisions:`. It does not cover the "You may not" list.
- No code comments. Follow `~/.agents/skills/no-comments/SKILL.md`.
- Write PR text and replies in STE style: short sentences, active voice, one idea per sentence. Lead the PR `## Summary` with the problem in Kolin's words, then the fix. Do not lead with a list of changed files.
- Start each PR comment or review reply with `> [!NOTE]` and `> 🤖 **<model> responding on behalf of Kolin**`, then a blank line and the reply. Use the model name the harness reports, or the harness name. Lead with the conclusion and cite the `file:line`, check or output. Resolve a thread only after GitHub returns the reply URL.
- Evidence means things you ran and saw in this session: commands, exit codes, output lines, screenshots. Do not count a claim, a mocked green run, or "should work" as evidence.
## Flow
1. **Orient.** Read the task, the issue or PR, and the repo's AGENTS.md or CLAUDE.md. Find the base branch: use `staging` if it exists, otherwise the repo default. Find the repo's gate: its pre-commit and pre-push hooks and its one check command.
2. **Branch.** Work on a feature branch. If you take over someone else's PR, keep their commits or credit them with a `Co-authored-by:` line.
3. **Prove the failure.** Reproduce the bug or write the failing test. Record the command and the failing output.
4. **Smallest change.** Name the outcome and the smallest change that reaches it. Make that change and nothing else.
5. **Prove the fix.** Run the same reproduction or test and see it pass. Run the repo's check command and every check its hooks run (lint, typecheck, tests, build). For UI or runtime behavior, run the app and observe the change. Capture the result.
6. **Open the PR.** Use `gh pr create --draft --base <base>`. If the repo has a PR template or a PR body check (named in its AGENTS.md), fill it and put the evidence in its Verification section. Otherwise use the PR body order in `policy/AGENTS.md`. `## Verification` holds the commands, exit codes and key output, before and after, and `## Blast Radius` says how to revert.
7. **Mark ready.** When the local evidence is complete, run `gh pr ready <N>`.
8. **Babysit.** Loop until the PR is ready to merge or you hit a stop rule. If you end your turn with nothing set to wake you, the work stops, because nobody prompts you again.
   - Handle the checks and comments that already exist. Then start one watcher per PR and end your turn. In T3 Code, call `watch_pull_request`, and only in the thread that owns the PR, never in a delegated child. Elsewhere, run `gh pr checks <N> --watch` as one background command, then read `gh pr view <N> --comments` when it exits. If a review bot has not finished then, wait with the Monitor tool on an until-loop over `gh pr view <N> --json reviews`. Never write a foreground sleep loop or a watcher script.
   - A wake is news, not a merge decision. Re-check the ready gate yourself. When a wake needs no action, end the turn without a message.
   - Act only on checks and comments newer than the latest push. Verify each bot finding in the source before you change code. Tell a repo failure from an infrastructure flake.
   - On a failed check, read the log (`gh run view <id> --log-failed`), fix the root cause, re-verify locally, and push.
   - On a review comment (from a bot or a human), either fix it, or reply with a specific reason you will not. Do not stay silent.
   - When the base branch moves, merge it into the branch, re-run step 5, and push. `watch_pull_request` reports conflicts but not BEHIND, so check `mergeStateStatus` before you call the PR ready.
   - After every push, update the evidence so it matches the current head commit.
9. **Ready gate.** Stop only when all of these are true:
   - The evidence covers every changed file and behavior at the current head.
   - `~/.agents/skills/pstack-local/scripts/diff-audit <base>` shows no block, or the PR body gives each one a reason.
   - All required checks are green on the current head. If the repo requires none, every check that ran is green and none is pending.
   - Review bots have finished. Every finding is fixed, or has a reply that gives a reason.
   - No reviewer has changes requested.
   - The branch is up to date with the base, and GitHub reports no conflicts.
10. **Report** (format below), ending with `Ready for Kolin to merge.` In T3 Code, call `unwatch_pull_request` before the report or a question, or the thread stays in Working and out of Kolin's inbox.
## Stop rules
Stop and report instead of continuing when:
- A guard hook blocks a command you need.
- The work needs anything listed under "You may not".
- The same check fails 3 times after separate fixes, or you can't reproduce the failure.
- Reviewers conflict, or the task intent is unclear and the code can't settle it.
- The fix needs to grow past the original intent.
## Contacting Kolin
Contact him only when blocked or ready. Ask with the harness question tool (AskUserQuestion), not in a plain message. Put the full context in the question: PR link, what blocks you, the options, and your recommendation first. If no question tool is available, make it the first line of your final report.
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

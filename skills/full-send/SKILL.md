---
name: full-send
description: "Use only when Kolin explicitly says \"full send\" or invokes /full-send for a specific PR or task in this session. Do not apply it on your own judgment."
---
# Full send
Kolin invoked this because he is not watching the thread. Own the work from its current state to a merged PR. Kolin reads your messages only after you stop, so a message in the chat does not reach him until then.
If Kolin did not clearly invoke full send in this session, do not take this autonomy. Work normally.
## Base workflow
Read `~/.agents/skills/full-stop/SKILL.md` and follow all of it: rules, flow steps 1 to 9, stop rules, contacting Kolin, report format. Full send changes only the end. It replaces "stop at ready" with the merge gate below.
## The yes and its scope
Kolin's rule: never merge without a yes in the session. Kolin explicitly invoking full send in this session for this PR is that yes. The yes:
- Covers this one PR only. It does not carry over to other PRs, follow-up PRs, or later sessions.
- Covers the merge only. It never covers a deploy, a release, a promote, or a workflow run.
- Ends when the PR scope grows past the original intent. Then fall back to full stop.
## Merge gate
Check every item at the current head commit. Record the command and the result for each one.
1. **Proof.** The evidence covers every changed file and behavior. Check it against `gh pr diff <N> --name-only`.
2. **Checks.** All required checks are green: `gh pr checks <N> --required`. A skipped required check counts as a failure. If it reports no required checks, every check in `gh pr checks <N>` that ran is green and none is pending.
3. **Review bots.** Every bot review has finished. Every finding is fixed, or has a reply that gives a reason.
4. **Humans.** No review has changes requested: `gh pr view <N> --json reviewDecision,reviews`.
5. **Up to date.** The branch has the latest base, and `gh pr view <N> --json mergeable,mergeStateStatus` shows `MERGEABLE` and `CLEAN`.
6. **Migrations.** The diff has no destructive migration (drop, truncate, a destructive rename, or data deletion) unless the PR has a label that approves it. A schema change of any kind still needs Kolin under the standing approvals.
7. **Not a promotion.** The PR does not promote or release to production (for example `staging` into `main`, a release branch, or a version tag) unless Kolin said so explicitly for this PR.
If any item fails and you can fix it, fix it, re-verify, and go back to item 1. If you can't fix it, stop with the full stop report and give the reason the gate failed.
## Merge step
When the gate passes:
1. Run `git fetch`, then check items 2 and 5 again. If base commits that landed after the last green run touch this PR's files, merge the base in, push and wait for green again.
2. Pick the merge method the repo uses (from the repo settings or recent merged PRs).
3. Run `gh pr merge <N> --<squash|merge|rebase>` once. Do not add `--auto` or `--admin`.
4. If a guard hook blocks it, do not try any other route to merge: no API call, no script, no git merge into the base, no workaround. Stop and report with this status line, and put the command only in the report text:
   `Gate passed, merge blocked by hook; run: gh pr merge <N> --<squash|merge|rebase>`
5. If it merges, confirm with `gh pr view <N> --json state,mergeCommit` and report `Merged` with the merge commit.
## Pushes
- Push only normally, and only to the agent's own feature branch.
- Never force-push. To update the branch, merge the base into it and push normally. Never rebase a pushed branch.
## Never
- Deploy, promote, release, or run workflows, before or after the merge.
- Merge a PR other than the one Kolin named.
- Treat a passing gate as permission for anything outside the merge.
## Report
Use the full stop report format. Set `Status:` to one of:
- `Gate passed, merge blocked by hook; run: gh pr merge <N> --<method>`
- `Merged <merge sha>`
- `Gate failed: <item>: <reason>`
Under `Evidence:`, list all 7 gate items with their results.

---
name: full-send
description: "Use only when Kolin explicitly says \"full send\" or invokes /full-send for a specific PR or task in this session. Do not apply it on your own judgment."
---
# Full send
Kolin invoked this because he is not watching the thread. Own the work from its current state to a merged PR. Kolin reads your messages only after you stop, so a message in the chat does not reach him until then.
If Kolin did not clearly invoke full send in this session, do not take this autonomy. Work normally.
## Base workflow
Read `~/.agents/skills/full-stop/SKILL.md` and follow all of it. Full send changes only the end: it replaces "stop at ready" with the merge checklist below.
## The yes and its scope
Kolin never merges without a yes in the session. Kolin invoking full send for this PR is that yes. The yes:
- Covers this one PR only, not follow-up PRs or later sessions.
- Covers the merge only, never a deploy, release, promotion or workflow run, before or after the merge.
- Ends when the PR scope grows past the original intent. Then fall back to full stop.
## Merge checklist
Check every item at the current head commit, and record the command and result for each.
1. **Ready.** full-stop's Babysit reports `READY` and its ready checks pass. A skipped required check counts as failed.
2. **Up to date.** `gh pr view <N> --json mergeable,mergeStateStatus` shows `MERGEABLE` and `CLEAN`.
3. **Migrations.** No destructive migration (drop, truncate, destructive rename, data deletion) unless a PR label approves it. Any schema change still needs Kolin's approval.
4. **Not a promotion.** The PR does not promote or release to production (`staging` into `main`, a release branch, a version tag) unless Kolin said so for this PR.
If an item fails and you can fix it, fix it, re-verify and start again at item 1. If you can't, stop with the full-stop report and the reason.
## Merge step
This is pstack's **Shipping** playbook for one PR. The fresh review and full-stop's evidence are its independent verdict. These limits win over Shipping:
1. Run `git fetch`, then check items 1 and 2 again. If base commits that landed after the last green run touch this PR's files, merge the base in, push and wait for green again.
2. Use the merge method the repo uses (repo settings or recent merged PRs).
3. Run `gh pr merge <N> --<squash|merge|rebase>` once, without `--auto` or `--admin`.
4. If a guard hook blocks it, try no other route to merge: no API call, no script, no git merge into the base. Stop and report with this status line:
   `Checklist passed, merge blocked by hook; run: gh pr merge <N> --<squash|merge|rebase>`
5. If it merges, confirm with `gh pr view <N> --json state,mergeCommit`.
## Report
Use the full-stop report format. Set `Status:` to one of:
- `Checklist passed, merge blocked by hook; run: gh pr merge <N> --<method>`
- `Merged <merge sha>`
- `Checklist failed: <item>: <reason>`
Under `Evidence:`, list the 4 checklist items with their results.

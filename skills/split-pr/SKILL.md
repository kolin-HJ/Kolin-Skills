---
name: split-pr
description: Split a PR that is too big to review, most often a release PR (`staging` into `main`), into slices to review and cuts to release, then take them one at a time. Use when Kolin asks to split a PR or a release, says "split-pr", or asks how to make a big release reviewable. It plans and reviews without asking. Every merge and deploy waits for Kolin's yes.
---

# Split PR

Nobody reviews a PR they cannot read. Turn it into parts a person can read in one sitting, in an order that is safe to ship.

- A **slice** is a part to review: one area of the diff, picked by path. Slices always exist.
- A **cut** is a part to release: a point on the head branch's own history. Everything up to it ships together. A cut exists only where the history allows one.

Never reorder history to make one theme ship alone, such as a feature branch rebuilt off the base by cherry-pick. No check ever ran on that tree, and it breaks numbered migrations.

## 1. Read how the repo releases

From the repo's `AGENTS.md`, its deploy workflow and its PR checks, find:

- What a merge into the base does. A push to `main` may deploy at once.
- How release PRs merge: `git log --first-parent -3 origin/<base>`. Two parents means a merge commit, and cuts work. A squash merge loses the link to the head branch: stop and tell Kolin, because each cut then needs the base merged back into the head.
- What the checks ask of a release PR, and how they know one. If they know it only by the head branch's name, they must learn the release branch name first. That is its own PR in that repo.
- How migrations run, and whether the old code survives the new schema between migrate and promote.

## 2. List the steps

```sh
git fetch origin <base> <head>
python3 <this folder>/merge-sequence.py origin/<base> origin/<head>
```

One row per step on the head branch since it left the base. `product`, `tests` and `migrations` are lines added. `running` is what a cut after that step ships in all. `fixes_left` names later fix PRs that touch files the cut ships: an upper bound, so read each one. `top_area` is where most of the step's product lines went.

## 3. Choose the cuts

1. A cut sits right after a step, so its tree is one the head branch had. Pick a step whose push checks passed (`gh run list --commit <sha>`).
2. A cut never ships a feature without its fixes. Read each PR in `fixes_left`, and `git blame` the lines it replaces at the fix's first parent. Lines a step in the cut wrote mean the fix repairs the cut: move the cut to after that fix. Lines older than the release are an older bug, and that does not hold a cut back.
3. A cut holds what one walkthrough can cover: one main feature, or under about 6,000 product lines of small ones. One step bigger than that is a cut of its own.
4. A cut that waits on a person (a sign-off, an open product question) starts after the cuts that do not.
5. Fewer cuts beat a risky cut. When fixes interleave so that no step before the end is clean, say so: the release is one cut, reviewed in slices.

## 4. Choose the slices in each cut

`git diff --numstat <cut before>..<cut>`, grouped by area. A slice is one feature (its route folder and its `lib` folder) and stays under about 1,500 product lines, so one reviewer reads every file. Split a bigger feature at a seam: stored shape and writes, decision logic, screens. Tests go with their source. Tooling, CI and docs make one slice, read lightly.

## 5. Show Kolin the plan, and stop

For each cut: its steps by PR number, product lines, migrations, slices, the fixes it leaves behind, what it waits on, and what its walkthrough must drive. Add one line on what the split costs: the count of deploys and walkthroughs. Wait for the yes.

## 6. Take one cut at a time

1. Review each slice with `structure-review`, one `judge` per slice, a few at once. Add `senior-reviewer` for a slice that holds a schema, an access rule, money or an outside write, or whose PRs merged red or with no review.
2. Sort the findings. One a user would hit (a wrong number, lost data, open access) holds the cut. A structure finding follows the cut.
3. Fix on the head branch through a normal PR. For a finding that holds the cut, then cherry-pick that fix onto the cut's release branch. Never fix on the release branch first. Structure fixes ship in a later cut; `hydrojug-untangle` can apply them when Kolin asks.
4. Open the cut's PR: branch `release/<date>-<n>` at the cut commit, into the base, with the repo's release template. One line per PR it ships, the migrations and deploy order, what each slice review found, and the walkthrough.
5. Prove it with the repo's release walkthrough, driven only over what the cut ships.
6. After Kolin's yes: merge with a merge commit, watch the deploy and the repo's smoke check, then start the next cut. Never merge a cut while a deploy runs. A failed or rolled-back deploy stops the train: report it.

The last cut is the head branch itself, so the first big PR can carry it.

## A big PR that is not a release

Slices work the same. Cuts become a stack: split the branch at commits where the gate passes, one PR per part, each based on the one before. A branch that is one commit, or whose parts interleave, gets slices only. Rebuilding it as a stack is a rewrite, and that needs Kolin's yes.

## After the split

A split is a repair. Say in the report how many steps and days the release held, and name the earliest step where a clean cut was ready. Releasing at that point each time means no split is needed.

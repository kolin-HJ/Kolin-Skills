---
name: modernize
description: Bring an old PR or branch up to date, or take over someone else's PR, branch or agent thread, and decide first if it should still land. Use when Kolin says "modernize", "rebase this PR", "update this old PR", "port this PR" or "take over".
---
# Modernize

Modernize the idea, not only the branch. A clean merge does not prove the PR still belongs in the product.

## Guardrails

- Fetch the PR head, the base and every related branch before you start.
- Treat changes in the worktree as Kolin's. Use a fresh worktree when it is dirty or in use.
- This skill covers updating the PR branch. It does not cover a merge, a close, a new base or more scope.
- Update the branch by merging the base into it, then push normally. Never force-push.

## Find the intent

Record the PR URL, state, base, head branch, head SHA, author, checks and review state. Read the title, body, linked issues, commits, review threads and the full diff. Write the smallest goal the PR tried to reach before you judge the code. For a takeover, also read the source thread and Kolin's later corrections, and account for uncommitted work. The handoff is context, not proof.

Record the merge base so you can compare the PR's own change with what the base did after it.

## Check what changed around it

Read the base commits since the merge base. Search merged and open PRs that touch the same code paths or the same behavior.

- Did the base already solve the same problem?
- Did an API, type, schema or module boundary change?
- Was the changed code deleted, moved or simplified on purpose?
- Would landing it bring back old behavior, or make two ways to do one thing?
- Is the benefit still worth its cost?

No conflicts does not mean current.

## Pick a disposition before you push

- **MODERNIZE**: the goal is useful and the shape is right. Update, test and push.
- **REWORK**: the goal is useful, but a mechanical update keeps the wrong code. Name the smallest rewrite and stop, unless Kolin asked for the rework.
- **CLOSE**: superseded, obsolete or not worth its cost. Cite the evidence and stop. Do not update the branch, and do not close the PR without Kolin's yes.

Be willing to say CLOSE. Age is not evidence, and sunk effort is not a reason.

## Update without losing intent

1. Merge the fetched base into the PR branch, or for a takeover into a new branch made from the original commits.
2. Resolve each conflict by the PR's intent and the base's newer rules. If a conflict shows a product or architecture disagreement, go back to the disposition.
3. Compare `git diff <old merge base> <old head>` with `git diff origin/<base>...HEAD`. Confirm no intended behavior went away and no landed behavior came back.
4. Run the repo's gate. Tell a real failure from one that already failed on the base.
5. Push normally. If the push is rejected, fetch and reassess. Never overwrite new work.

## Credit

Keep the original commits, their authors and their `Co-authored-by:` lines. Link the original PR in the new body and credit its authors by verified GitHub login or commit identity, never a guessed email. If the PR is squashed, keep their `Co-authored-by:` lines in the merge commit. Model attribution does not replace a person's credit.

## Report

Lead with `MODERNIZE`, `REWORK` or `CLOSE` and the reason. Then list: the base changes that matter, the conceptual conflicts or "none found", the update and push result, the checks and their results, and the decision left for Kolin with the PR link. Keep what you observed apart from what you judge.

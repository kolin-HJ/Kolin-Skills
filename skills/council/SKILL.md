---
name: council
description: "Use only when Kolin says \"council\" or invokes /council. Gets a read-only review from three models on three different providers, in rounds, until they agree or the budget ends. Do not apply it on your own judgment."
---
# Council

A reviewer on the model that wrote the code shares its blind spots. Council adds two other providers. It adds to `senior-reviewer`, it does not replace it.

## Before round 1

- Fix what you already know: open PR comments, failing checks, known bugs. Council reviews the current code, not a list of fixes you plan to make.
- Run the repo's gate and record the result. Do not send code that this change breaks.
- Find the base: `git merge-base HEAD origin/<base>`. Use one diff command for every round.
- Write the intent and what is out of scope in one or two sentences.

## Members

Use the members Kolin names. Otherwise use the latest flagship model of three providers, for example Claude Opus, GPT Sol and Gemini Pro, at high effort.

In T3 Code, call `orchestrator_capabilities`, then start one `delegate_task` per member in parallel, with `role: "review"`. Every round is a new `delegate_task`. Do not hardcode a model ID. Elsewhere, use the harness's subagent tool with that model. If a member is not available, report it. Never put a different model in its seat.

Do not edit the files under review while a round runs. Do not poll. A timeout, an error or no reply is not approval.

## Brief

Each delegate gets no history. Send:

```
Review only. Do not edit, commit, push, comment on PRs or start subagents.
Repo: <abs path>  Base: <sha>  Intent: <intent>  Out of scope: <scope>  Gate: <result>
See: git diff <base>; git status --short (read untracked files).
Read the code around each change. Find bugs, broken callers and mismatch with the intent.
Hold the change to its smallest form. Flag code, tests or guards the intent does not need.
blocker = the intended case is wrong. should = a real bug callers will hit, inside the intent. nit = everything else.
Reply:
SCORE: <n>/10
VERDICT: APPROVE or CHANGES
C1 [blocker|should|nit] <file>:<line> <claim>. Fix: <suggestion>
```

## Answer findings

Check each finding and its severity in the code yourself. Classify it by the scope rule in `full-stop`, whatever label it came with.

- Agree: make the smallest fix.
- Disagree: say why, with a `file:line`, a test or output.
- Nit or out of scope: decline it in one line and list it as a follow-up.

Keep a ledger: id, member, severity, outcome. Re-run the gate and `git diff --shortstat <base>`. If review grew the diff, cut first.

## Rounds

- Budget: 3 rounds. Extend to 5 only for security, auth, permissions, data loss or concurrency while a blocker or should is open with evidence.
- A later round sends the brief, the ledger (`fixed:`, `disagree:`, `declined:` with evidence) and the change since the last round. Members check open ids and changed code only.
- Stop when every member approves the current diff and no blocker or should is open. Stop early when a round returns only nits.
- If an item stays disputed after two replies, or the budget ends, show both sides in two or three lines each. Kolin decides. The end of the budget is not approval.

## Report

If a PR exists, edit its body (no comment) and add this section above the model line:

```markdown
## Council review

Rounds: 2

| Member | Round 1 | Round 2 |
| --- | --- | --- |
| Claude Opus | 7/10 | 9/10 |
| GPT Sol | 8/10 | 10/10 |
| Gemini Pro | 7/10 | 9/10 |
```

Write `no score` when a member gave none. Never invent a score. Without a PR, put the table in the final reply. Also report what each member changed, the diff size before and after, and each declined finding with its reason.

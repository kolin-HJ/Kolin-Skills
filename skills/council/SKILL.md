---
name: council
description: Use only when Kolin says "council" or invokes /council. Gets review or feedback from Claude Opus 5.5, GPT 6.1 Sol, Muse Wonder (via Cursor) and Grok 4.7 (via the Grok subscription), one per provider, all at high effort, picked from what T3 Code shows is available.
---

# Council

Before an audit, address outstanding PR comments, fix known issues, and run
relevant checks. Give council the updated implementation; do not defer known
fixes until reviews return. If the user wants to discard the implementation
and explore new ideas, skip fixes to code being replaced.

Bring in one delegate per model provider, so each opinion comes from a
different model family. Run every member at `high` effort, never the
provider's default. The seats, in priority order:

1. Claude Opus 5.5 (`claude-opus-5-5`), with `effort: high`. Always seated.
2. GPT 6.1 Sol (`gpt-6.1-sol`), from `codex`, with `reasoningEffort: high`.
3. Muse Wonder (`muse-wonder-1.0`), from `cursor`, with
   `reasoning_effort: high`. Its default is `xhigh`, so set it.
4. Grok 4.7 (`grok-4.7`), from `grok`, with `reasoningEffort: high`. Never
   use a fast build such as `grok-4.7-build-fast`.

In T3 Code, call `orchestrator_capabilities` first, then pick the seats.
Muse Wonder is not in Cursor's short list, so also call it with
`search: "muse"`.

1. A seat is available when its provider is enabled, has no constraints and
   lists the model.
2. For Opus 5.5, use the `claudeAgent_claude_personal` instance. If it hits
   a usage limit, use `claudeAgent`.
3. For Muse Wonder, use only the `cursor` instance, never the `muse`
   instance.
4. For Grok 4.7, use the `grok` instance. If it is down or out of usage, use
   `grok-4.7` from `cursor` with `fastMode: false` and
   `reasoning_effort: high`.
5. Start one `delegate_task` per seat, in parallel.

If a seat is unavailable, or its delegate fails on a usage or rate limit,
skip it and say so in the summary. Do not fill the seat with a second model
from a provider already seated. Never add a Google model.
Elsewhere, use the harness's subagent tools with the same seats.

Give each delegate the request and relevant context. For review or feedback,
keep their work read-only. Collect their responses and summarize the useful
findings, disagreements, and recommended next steps.

For a code review, ask each delegate for a score out of 10.
Count each full review pass as one round.
A fresh review after fixes starts a new round.

If the work ends in a pull request, put the results in the PR description.
Put this section before the model and harness line at the end:

```markdown
## Council review

Rounds: 2

| Delegate | Round 1 | Round 2 |
| --- | --- | --- |
| Claude Opus 5.5 | 7/10 | 9/10 |
| GPT 6.1 Sol | 8/10 | 10/10 |
| Muse Wonder | 7/10 | 9/10 |
| Grok 4.7 | 6/10 | 9/10 |
```

If a delegate gives no score, write `no score`. Do not invent one.
If a seat was skipped, leave its row out and name it under the table.
If the PR is open, edit the description. Do not post a comment for this.
If there is no PR, put the same results in the final reply only.

If you agree with their recommendations, make the changes and request a fresh
review after. Continue this process until every seated delegate is satisfied with the
outcome.

Do not let repeated reviews result in scope creep. It is your job to fight to
keep scope limited.

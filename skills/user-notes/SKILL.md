---
name: user-notes
description: "Write short release notes for the people who use the app, from a merged release PR. Use when Kolin says \"user notes\", \"release notes\", \"what's new\" or \"changelog\" for a release or a PR. Not for a PR body or its Scope table."
---
# User notes

Turn a release into notes a user reads in 30 seconds. The reader uses the app every day and does not read code.

## Find the release

The release PR is the merged PR from the integration branch into the deploy branch. The repo's `AGENTS.md` names both branches. If it names no deploy branch, ask Kolin.

1. If Kolin names a PR, use it. If not, use the last merged release PR: `gh pr list --base <deploy branch> --head <integration branch> --state merged --limit 1`.
2. Read its body and commits: `gh pr view <N> --json title,body,commits,headRefName,mergedAt`. A release body lists the PRs it ships. Read a listed PR with `gh pr view` only when its row does not say what the user sees.
3. Include follow-up PRs that merged into its `headRefName` before its `mergedAt`: `gh pr list --base <headRefName> --state merged`.

## Write

Kolin pastes the notes into Google Chat, so write Chat syntax, not Markdown: `*bold*`, `_italic_`, `•` bullets, no `#` headings and no `**`. Put the notes in one fenced block, with the release PR's `mergedAt` date in Kolin's local time, for example "Oct 20":

```
🚀 *What's new in <App>, <Mon D>*

*<Page name>*
• <One change, one line.>

_Reload the tab to get the update._
```

`<App>` is the app name users know, from the repo's `AGENTS.md`. The title emoji is Kolin's Chat style, an exception to `unslop`'s emoji rule. Keep the reload line only when users must reload to see the change; it is the one closing line the no-outro rule below allows.

- Group by the page name the user sees in the app. Put the page with the biggest change first.
- One bullet per change. One sentence, about 15 words or fewer. Two bullets per page is typical, three at most.
- Say what the user sees or does now: "Click an order to see its line items." Not how it works.
- No internal terms: no PR numbers, function names, table names, cache keys, crons, logs or env vars. No test or review numbers.
- Keep a change only if a user can see it. Drop internal fixes, refactors, reliability work and gates.
- A rename the user will notice gets its own bullet: "\"Pending\" is now \"On hold\"."
- If a change needs the user to act, say the action: "Press *Submit* to save it."
- A date the user waits for gets the date: "The first one is Oct 25."
- No intro, no outro, no "we're excited".

## After the notes

In your reply after the notes block, not inside it, list for Kolin only the manual steps and checks the release body names: a backfill, a log to watch, a saved view or query that breaks. One line each. Leave this part out if there are none.

## Don't

- Post the notes anywhere. Kolin sends them.
- Make up a change the PR does not state.

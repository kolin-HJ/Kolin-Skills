---
name: user-notes
description: "Write short release notes and a matching PNG image for the people who use the app, from a merged release PR. Use when Kolin says \"user notes\", \"release notes\", \"what's new\" or \"changelog\" for a release or a PR. Not for a PR body or its Scope table."
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
- Never make up a change the PR does not state.

## Make the image

Kolin posts a PNG of the notes with the title line as the message text, because people look at a picture and skip a list. Make the image from the same changes as the text, after the text is right.

1. Copy `assets/card.html` from this skill's folder into the session's scratch folder. Never edit the asset.
2. Fill the header: `<App>`, `<Mon D>` and the number of changes. Use "users" or the role the repo names, such as "planners".
3. Make the biggest change the wide hero card. Give it a headline of 8 words or fewer, one sentence, and up to three short facts. Replace the cutoff timeline with a small drawing of that change, or keep it if the change is a cutoff or date rule.
4. Give each other page one card, in a row of two or three (`grid2` or `grid3`). Each card has a tag (the page name), a headline of 5 words or fewer, one sentence, and a small mock of the screen part that changed: the column, dropdown, checklist, button or chip from the template, or a new one drawn the same way.
5. Draw a mock with grey skeleton bars (`.sk`), never with real item, customer or supplier names. Text in a mock is only a button, column or field label you read in the code, so the image cannot show a label the app does not have.
6. Use no emojis. Use inline SVG icons or the mocks for pictures. Keep the template's colors, type and spacing.
7. Keep the reload footer only when the text notes keep the reload line.
8. Render it at 2x with `agent-browser`, then look at the image before you hand it over. Fix any text that wraps badly or overlaps, then render it again:

```bash
agent-browser --session user-notes set viewport 1200 800 2
agent-browser --session user-notes open "file://<scratch>/notes.html"
agent-browser --session user-notes wait --load networkidle
agent-browser --session user-notes screenshot --full "<scratch>/whats-new-<yyyy-mm-dd>.png"
agent-browser --session user-notes close
```

Show the image in your reply and give its full path. Never make a PDF, because Chat shows a PDF as a download, not inline.

## After the notes

In your reply after the notes block, not inside it, list for Kolin only the manual steps and checks the release body names: a backfill, a log to watch, a saved view or query that breaks. One line each. Leave this part out if there are none.

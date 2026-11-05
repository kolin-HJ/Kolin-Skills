---
name: user-notes
description: "Ask Kolin first: text, graphic and/or video (video is low-frequency; never auto-make graphic or video). Then write user-facing release notes in the formats he picked, from a merged release PR. Use when Kolin says \"user notes\", \"release notes\", \"what's new\" or \"changelog\" for a release or a PR. Not for a PR body or its Scope table."
---
# User notes

Turn a release into notes a user reads in 30 seconds. The reader uses the app every day and does not read code.

## Find the release

The release PR is the merged PR from the integration branch into the deploy branch. The repo's `AGENTS.md` names both branches. If it names no deploy branch, ask Kolin.

1. If Kolin names a PR, use it. If not, use the last merged release PR: `gh pr list --base <deploy branch> --head <integration branch> --state merged --limit 1`.
2. Read its body and commits: `gh pr view <N> --json title,body,commits,headRefName,mergedAt`. A release body lists the PRs it ships. Read a listed PR with `gh pr view` only when its row does not say what the user sees.
3. Include follow-up PRs that merged into its `headRefName` before its `mergedAt`: `gh pr list --base <headRefName> --state merged`.

## Ask the format

After the release is known, stop. Ask Kolin once which format(s) to deliver: **text**, **graphic**, and/or **video**. He can pick more than one. Do not write notes, make an image, or make a video until he answers. If this ask already named the format, use that and do not ask again.

## Text

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

## Graphic

A short still of the same user-facing changes: app screenshots, or one composed PNG card. Chat can paste or attach it. No code internals.

Kolin posts a PNG of the notes with the title line as the message text, because people look at a picture and skip a list. Make the image from the same user-facing changes. If text was also chosen, make the image after the text is right.

1. Copy `assets/card.html` from this skill's folder into the session's scratch folder as `notes.html`. Never edit the asset.
2. Put the hj-ui brand tokens beside it, from the published branch, so the colors, radii and shadows come from the design system and never from a copy:

```bash
gh api -H 'Accept: application/vnd.github.raw' 'repos/HydroJug/hj-ui/contents/packages/ui/src/styles/tokens.css?ref=main' > "<scratch>/hj-tokens.css"
```

   If the fetch fails, stop and tell Kolin. Never render without the tokens.
3. Fill the header, one short row so the updates get the space: "What's new in `<App>`," then the full date in bold, such as "November 4". On the right, the count and the readers: "4 new updates for planners". Use "users" when the repo names no role.
4. Make the biggest change the wide hero card. Give it a headline of 8 words or fewer, one sentence, and up to three short facts. Replace the cutoff timeline with a small drawing of that change, or keep it if the change is a cutoff or date rule.
5. Give each other page one card, in a row of two or three (`grid2` or `grid3`). Each card has a tag (the page name), a headline of 5 words or fewer, one sentence, and a small mock of the screen part that changed: the column, dropdown, checklist, button or chip from the template, or a new one drawn the same way.
6. Draw a mock with grey skeleton bars (`.sk`), never with real item, customer or supplier names. Text in a mock is only a button, column or field label you read in the code, so the image cannot show a label the app does not have.
7. Use no emojis. Use inline SVG icons or the mocks for pictures. Style only with the hj-ui tokens the template uses (`var(--primary)`, `var(--marker)`, `var(--radius-sm)` and the rest), never a hex value. Follow the hj-ui rules the template already follows: Georgia for titles, Inter 400 to 700 for the rest, no gradients, Brass (`--marker`) only for marks and never for text.
8. Keep the reload footer only when the text notes keep the reload line.
9. Render it at 2x with `agent-browser`, then look at the image before you hand it over. Fix any text that wraps badly or overlaps, then render it again:

```bash
agent-browser --session user-notes set viewport 1200 800 2
agent-browser --session user-notes open "file://<scratch>/notes.html"
agent-browser --session user-notes wait --load networkidle
agent-browser --session user-notes screenshot --full "<scratch>/whats-new-<yyyy-mm-dd>.png"
agent-browser --session user-notes close
```

Show the image in your reply and give its full path. Never make a PDF, because Chat shows a PDF as a download, not inline.

## Video

A training / show-off video of the same user-facing changes. It must look like someone is using the app the notes are for: that app's real screens, a visible pointer, real clicks, typing and page changes. Never abstract motion, slides or a made-up UI. Same language rules as the text notes: what the user sees, no PR numbers.

1. Run the app from this repo locally with seed or test data, as its `AGENTS.md` or `run` skill says. Never record production data or real customer, supplier or staff names.
2. Write a shot list first: one shot per change, biggest change first. Each shot names the page, the clicks and the one thing the viewer should notice.
3. Record each shot in the real app with `agent-browser`, pointer on, at the same viewport as the graphic:

```bash
agent-browser --session user-notes-video set viewport 1440 900
agent-browser --session user-notes-video open "<local app url>/<page>"
agent-browser --session user-notes-video wait --load networkidle
agent-browser --session user-notes-video record start "<scratch>/shot-<n>.mp4" --cursor
agent-browser --session user-notes-video click "<selector>"
agent-browser --session user-notes-video record stop
```

   Move at a human pace: wait about one second after each click so the viewer sees the result.
4. Read `/hyperframes`, then `/media-use`. Use them to cut the shots together. The app screens stay the main picture; captions, zooms and highlights only point at them.
5. Make each shot obvious to a viewer with the sound off who has never seen the change:
   - Open the shot with a caption that names the feature and why it helps, in 8 words or fewer: "New: see line items on any order."
   - Before the click, put a highlight ring or arrow on the button or field the pointer will use.
   - Zoom in on the part that changed, and hold the result on screen for about 2 seconds.
   - When the change replaces old behavior, show before, then after, each labeled.
   - Show one feature at a time. Keep each shot to 10 to 20 seconds and the whole video under 90 seconds.
   - End on a card with the release title and the page names, so viewers know where to find each change.
6. Read `/reverse-any-video` only when the source is an existing clip to rebuild as editable HTML.
7. For stock music, SFX or Voice Turbo, run `hyperframes auth login` first. Do not wait for a Pro account.
8. Watch the final file before you hand it over. Re-record a shot that shows a loading spinner, an error or a wrong page, or where the point of the shot is not clear in 3 seconds. Give Kolin the file path and ask him to approve it. Keep every shot and the HyperFrames project until he does, so a change is a re-cut and not a re-record.
9. After Kolin approves, finish in this order:
   1. Copy the final render to `~/Downloads/whats-new-<app>-<yyyy-mm-dd>.mp4`. If that name exists, add `-2`, never overwrite.
   2. Play the copy in `~/Downloads` once to confirm it is complete.
   3. Close the recording session: `agent-browser --session user-notes-video close`.
   4. Stop the local app and any preview server you started for the video.
   5. Delete the raw shots, contact sheets, the HyperFrames project and any other render files you made in scratch.
   6. Give Kolin the `~/Downloads` path and say what you deleted.

## After the notes

In your reply after the deliverable(s), not inside a notes block, list for Kolin only the manual steps and checks the release body names: a backfill, a log to watch, a saved view or query that breaks. One line each. Leave this part out if there are none.

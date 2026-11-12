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

A training video of the same user-facing changes. Every demo must look like someone is using the app: its real screens, a visible pointer, real clicks, typing and page changes. Same language rules as the text notes.

A stageshow mock scene goes in three places only: the intro, the end card, and each note. Never use a mock for a change that has a screen.

The kit in `assets/video/` does the repeated work: `rec.sh` (record helpers), `clean.js` (blur and hide), `stage-record.mjs` (records a stageshow scene to MP4), `scenes.py` (builds the HyperFrames project from one `spec.json`), `scene.css` and `spec.example.json`. Copy it into the session's scratch folder; never edit the assets.

### Plan the coverage

1. List every change in the release body a user could notice. For each, pick **demo** if a user can see it by clicking (a button, column, popup, filter, page, label or value), else **note** (a schedule, a report that arrives later, a removed thing). A note gets a mock scene. A change that has a screen is a demo, even a small one such as a renamed column or a new date format. Put the list in your reply before you record.
2. Order the demos by impact. Each demo shows the whole flow: where to find it, the action, and the result the user gets, on screen and readable. A button alone is not a demo: open the popup, scroll to the part that explains the number, and hold it.

### Record

3. Run the app locally with seed or test data, as the repo's `AGENTS.md` or `run` skill says. Never record production data. When a page needs a permission or a record, add it to the local database only, tag it so you can find it (`granted_by='local:user-notes-video'`, a `ZZ`-style name), and remove it after approval. Never press a button that writes to an outside system (a NetSuite create, a BigQuery push, an email).
4. Edit `clean.js` for the app: `PRIVATE` blurs customer, supplier and staff names, emails and other private text; `NOISE` hides dev banners and load warnings. Load it as an init script so every page is clean before the first frame.
5. Scout each shot with screenshots first. Find each target and tag it with `tag <name> '{q:"<css>",t:"<text>"}'` (agent-browser selectors are CSS only). The tag name is the event name the spec uses, so use each name once per shot. Tag a target that appears after a click once it is on screen.
6. Record each shot in a **fresh** browser session, because a long-lived session freezes the screencast. Drive it only with the `rec.sh` helpers, so the pointer moves like a person's and every action lands in the marks file:

```bash
source rec.sh; fresh clean.js
export MARKS=<scratch>/shots/<n>.marks
A open <url>; tag <name> '<target>'
roll <scratch>/shots/<n>.mp4
click <name>
typein <name> "<text>"
hover <result>
wrap
```

   - `roll` starts the recording with a visible pointer and marks `start`. `wrap` holds the last frame and stops.
   - `click` glides the pointer to the target, clicks it, marks it with its box, and waits.
   - `typein` clicks the target, then types one letter at a time.
   - `hover` glides to a result and marks it without a click. Use it on the result each demo ends on, so the spec can zoom there.
   - Never use `A click`, `A fill` or `A type` while recording, because the pointer jumps and the marks miss the action.
7. If a control does not respond in headless Chrome (a date input, say), drive the other path a user has (the grid cell, a keyboard entry). Never fake the result.
8. Prove each shot before you use it: take a screenshot at the end and read the result value, and make a 6-frame strip (`ffmpeg -i shot.mp4 -vf "fps=1/2,scale=480:-1,tile=6x1"`) to show the frames change. Re-record a frozen, spinning or wrong shot.

### Mock scenes

9. Read `/stageshow`. Set up a copy of it and start its preview:

```bash
cp -R ~/.agents/skills/stageshow <scratch>/stageshow
cp <scratch>/stage-record.mjs <scratch>/stageshow/scripts/
cd <scratch>/stageshow && npm install
node node_modules/vite/bin/vite.js playground --config playground/vite.config.ts --port 5199 --strictPort
```

10. Build one scene for the intro and one for each note, in `<scratch>/stageshow/examples/un-<name>/`, with stageshow's workflow: copy the closest gold example, then make it this app.
   - Stage size 960 × 600. Leave out `compact`, because the video never shows a phone column.
   - Map the hj-ui tokens (fetched as in graphic step 2) onto stageshow's tokens (its `references/looks.md`). Use `standard` fidelity: real words only on the change itself, grey bars for the rest. Words are only labels the app has, as in graphic step 6. Never use a customer, supplier or staff name.
   - The intro scene shows the biggest demoed change in three beats, in 5 s. Its first frame already shows the product, because it is the video's thumbnail. Its `poster` is the end card's still.
   - A note scene shows the note happening, in 4 to 6 s with `play="once"`: the report lands in the inbox at 8 am, the removed button leaves its row. Hold the payoff at the end.
11. Rehearse each scene until stageshow's gate prints `rehearsal passed`: `node scripts/film.mjs "http://127.0.0.1:5199/?capture=un-<name>" --select '#example' --gate`. Skip its 390-wide pass.
12. Record each scene. `stage-record.mjs` steps stageshow's clock one frame at a time, so frames never drop or freeze:

```bash
node scripts/stage-record.mjs http://127.0.0.1:5199 un-intro --seconds 5 --out <scratch>/shots/stage-intro.mp4
node scripts/stage-record.mjs http://127.0.0.1:5199 un-<note> --seconds <dur> --out <scratch>/shots/stage-note-<page>.mp4
node scripts/film.mjs "http://127.0.0.1:5199/?capture=un-intro" --select '#example' --reduced --still --out <scratch>/shots/stage-outro.png
```

   Prove each clip with a 6-frame strip, as in step 8.

### Build

13. Read `/hyperframes`. Write `spec.json` from `spec.example.json`:
   - Each layer names its `marks` file, relative to `spec.json`. Never type a time or a box. Rings, zooms and captions name an event with `at`, and `scenes.py` reads its time and box from the marks. `at: "start"` is the start of the scene. `offset` moves the item later in seconds, or earlier when negative.
   - `mediaStart` trims the footage before the first action, about 1 s after `start`. The build stops when an event falls in the trimmed part.
   - A ring goes on each clicked target and shows as the pointer arrives. Give a ring a `label` when the step is not obvious ("Typo: pick the right value").
   - A caption has an eyebrow (`New · <Section> → <Page>` or `Fix · …`), a title of 8 words or fewer, and a `sub` that tells the user how to use it. Put `place: ["right"]` or `["right","low"]` on a caption that would cover the result.
   - Zoom (`scale` 1.4 to 1.5) on the `hover` result, then hold it about 2 s.
   - `stage` names the intro clip and the end-card still from step 12.
   - `notes` holds one entry per note, five at most: `page`, `text` worded as in the text notes (about 15 words), `clip`, and `dur` (the seconds you recorded, at least 1 s + 0.3 s per word). Never put a demoed change there.
   - `intro` counts the demos and notes: "6 updates shown in the app, plus 4 more". `pages` lists `<Section> → <Page>` for the end card.
14. Build and check:

```bash
python3 -I <scratch>/scenes.py <scratch>/spec.json <scratch>/project
cp <scratch>/shots/*.mp4 <scratch>/shots/*.png <scratch>/project/assets/
gh api -H 'Accept: application/vnd.github.raw' 'repos/HydroJug/hj-ui/contents/packages/ui/src/styles/tokens.css?ref=main' > <scratch>/project/assets/hj-tokens.css
cd <scratch>/project && npx hyperframes check --json
```

   Fix every `line_unread` warning: a label or caption stays on screen 0.5 s + 0.3 s per word.
15. Snapshot frame 0, each ring and caption time, and each note scene (`npx hyperframes snapshot . --at <t,…> --no-end -o ../snaps`), and look at every frame. Move a caption that covers the result or the pointer.
16. Render (`npx hyperframes render --video-frame-format png -o ../whats-new-<app>-<yyyy-mm-dd>.mp4`) and look at a frame sheet of the file.
17. Keep the video under 90 s. When showing every change needs more, go up to 2 minutes and say the length when you ask for approval. Full coverage wins over a short video.
18. Read `/media-use` only for music or voice; for stock music, SFX or Voice Turbo, run `hyperframes auth login` first. Read `/reverse-any-video` only to rebuild an existing clip.

### Approve and clean up

19. Show Kolin the video, the list of demos and notes, and the length. Ask him to approve it. Keep every shot and the project until he does, so a change is a re-cut and not a re-record.
20. After Kolin approves, finish in this order:
   1. Copy the final render to `~/Downloads/whats-new-<app>-<yyyy-mm-dd>.mp4`. If that name exists, add `-2`, never overwrite.
   2. Play the copy in `~/Downloads` once to confirm it is complete.
   3. Close the recording session: `agent-browser --session user-notes-video close`.
   4. Stop the local app, the stageshow preview and any other server you started for the video.
   5. Remove the local grants and test records from step 3.
   6. Delete the raw shots, contact sheets, the project, the stageshow copy and any other render files in scratch.
   7. Give Kolin the `~/Downloads` path and say what you deleted.

## After the notes

In your reply after the deliverable(s), not inside a notes block, list for Kolin only the manual steps and checks the release body names: a backfill, a log to watch, a saved view or query that breaks. One line each. Leave this part out if there are none.

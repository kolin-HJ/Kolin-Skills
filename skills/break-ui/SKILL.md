---
name: break-ui
description: Stress-test UI with worst-case data (long names, missing fields, zero or huge counts, emoji, non-Latin text), behind a "Worst case" toggle, then fix the clear breaks and report the rest. Use when asked to stress-test, break or find edge cases in a component, table, card or screen. Not for polish or motion (emil-design-eng) or phone feel (mobile-native).
---

# Breaking UI

Feed the realistic worst case for every rendered value through the data boundary, behind a dev-only toggle, and report what breaks. No redesign; motion is emil-design-eng.

## Operating Posture

Two failure modes, and the first is worse:

1. **Nonsense data.** `"aaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaa"` and 5,000-character names prove nothing. Every worst-case value must be something a real user could plausibly produce, or the longest value the backend accepts.
2. **Stopping at long text.** The breaks that ship are the short name that leaves an orphaned dash, the missing avatar, the count of exactly 1 ("1 members"), the empty list, the badge whose text got translated.

## Hard Rules

1. **Plausible or schema-backed, never random.** Each worst-case value is either a realistic example (a real naming pattern, a real email shape) or the actual limit from the validation schema, database column, or API contract. If you find no limit, that's a finding in itself: say "unbounded" and test something long but believable.
2. **Change the data, not the component.** The worst case enters through the same boundary the demo data does: the fixture, the mock, the props, the API stub. Never hand-edit markup or CSS to produce a break; that tests your edit, not the component.
3. **One dataset, many failures.** A single worst-case dataset should hit every row of the catalog that applies to this component at once. Mix them across rows (row 1 is the long name, row 2 is the long email, row 3 is the one-letter name), as real data does.
4. **Fix the clear breaks.** Stop only on breaks that need a design decision.

## Workflow

### Phase 1 — Map the surface

Read the component and list every value it renders, with its source:

| Field | Source | Type | Limit | Optional? |
| --- | --- | --- | --- | --- |
| `name` | `member.name` | string | 255 (`schema.ts:14`) | No |
| `email` | `member.email` | string | none found | No |
| `role` | `member.title` | string | 120 | Yes |
| `status` | enum | `active` / `invited` / `expired` | — | No |
| `count` | `workspace.memberCount` | int | — | No |

Include the values people forget: counts in headers, relative timestamps, badge and status text, button labels that come from data, tooltips, avatar images, the list itself (its length is a value too).

Look up limits in the validation schema (Zod, Yup, Valibot), database migrations, API types, and form `maxLength` attributes. Note where the frontend and backend disagree; a 50-character input that saves to a 255-character column means something longer will turn up eventually, through an import or the API.

### Phase 2 — Build the worst case

For each field, pick values from [CATALOG.md](CATALOG.md). Load it now.

Assemble a single worst-case fixture next to the existing demo data, shaped exactly like it (same type, same file conventions). The first few rows of a list matter most because that's what's on screen, so spread the different failures across them instead of stacking every one into row 1.

Also cover the cases that aren't one dataset:

- **Empty**: zero items, the no-results state.
- **One**: a single item, and every count at exactly 1 (pluralization).
- **Huge**: the realistic upper bound for list length (1,000+ rows if the list is unpaginated, since that's a performance break as well as a visual one).

These can be extra toggle positions or extra fixtures.

### Phase 3 — Wire the toggle

Put a segmented control labeled **Demo data / Worst case** where Kolin can flip it while looking at the component, and swap the fixture at the data boundary (Hard Rule 2). Extra states go in as extra segments: **Demo / Worst case / Empty / One / 1,000 rows**. The toggle is dev-only and never ships to production: gate it behind the dev environment or keep it inside a prototype route.

- **In a project with a dev server**: a dev-only switch (a `?data=worst` URL param read where the fixture is chosen, or a prototype route that renders the component with each fixture). The selection persists in the URL so a reload keeps it.
- **No project / standalone component**: a single self-contained HTML file with the component and both datasets inline.

### Phase 4 — Break it

View the worst case and look for each failure signature below. Check it:

- at the component's **real container width** (a sidebar list is not a full-page list), then at **320px** and at the **widest** layout it supports;
- with **browser zoom at 200%** (or root font size raised), because text grows and boxes don't;
- in **dark mode** and **RTL** (`dir="rtl"` on a wrapper) if the product supports either;
- on a **touch device**: hover-only actions (the ••• that appears on hover) are unreachable.

If browser tooling is available, screenshot both states at each width and compare. If it isn't, reason from the CSS and say which findings you verified visually and which you inferred.

#### Failure signatures

| What you see | Cause | Fix |
| --- | --- | --- |
| Avatar or icon squished into an oval or pill | Flex child shrinking | `flex-shrink: 0` on the avatar, icon, and any fixed-size box |
| Text overflows its box instead of wrapping or truncating | Flex/grid child has `min-width: auto` | `min-width: 0` on the text column (`minmax(0, 1fr)` in grid) |
| Email or URL runs past the edge | No break opportunities in the string | `overflow-wrap: anywhere` on that element |
| Trailing action (••• menu, button) pushed off-screen or clipped | Middle content took all the space | `min-width: 0` on the middle, `flex-shrink: 0` on the action |
| Badge wraps onto two lines | Badge allowed to shrink | `white-space: nowrap; flex-shrink: 0` on the badge, and decide what yields instead |
| Avatar centered against a three-line name looks adrift | `align-items: center` on rows of varying height | Top-align (`align-items: flex-start`) once text can wrap |
| Last row cut off at a hard edge mid-glyph | Fixed-height container with no fade or scroll affordance | Visible scrollbar or a fade mask, and ensure `overflow` is intended |
| Long word breaks mid-word in a heading | `word-break: break-all` | `overflow-wrap: anywhere` breaks only when it has to |
| Wrong initials (`"J"` for "Jo", `"CI"` for "… Montgomery III", `"�"` for an emoji-first name) | `.split(' ')[0][0]` style code | Initials from grapheme clusters (`Intl.Segmenter`), first + last word, fallback icon |
| Orphaned `—` or empty line where the role was | Placeholder rendered for a missing optional field | Omit the line, or reserve its height intentionally |
| "1 members", "0 member" | Hardcoded plural | `Intl.PluralRules`, or separate strings per count |
| Numbers jitter when they update, columns misalign | Proportional figures | `font-variant-numeric: tabular-nums` |
| `1284`, `1,284.000000001`, `NaN`, `undefined` | Raw number rendered | `Intl.NumberFormat` with the user's locale; guard null |
| Long translated button label overflows | Fixed-width button | Width from content with `min-width`, never a fixed `width` |
| Diacritics or tall scripts (Vietnamese, Thai) clipped top or bottom | Tight `line-height` with `overflow: hidden` | Looser `line-height` or no clipping on text boxes |
| Broken-image icon in the avatar | No `onError` fallback | Fall back to initials; `object-fit: cover` for any aspect ratio |
| Truncated text with no way to read it | `text-overflow: ellipsis` and nothing else | `title` attribute or a tooltip, and the full value elsewhere (detail view) |
| Scrolling 1,000 rows stutters | Every row rendered | Virtualize, or paginate, and say which |
| Content renders raw `<b>`, `&amp;`, or `**text**` | Wrong escaping layer | Escape once, at render; never `dangerouslySetInnerHTML` user data |

#### Truncate, wrap, or clamp

Every long string forces this choice. Make it per field, not globally:

- **Wrap** text the user needs in full to identify something: names, titles in a detail view. Two lines is usually fine; four is a sign the column is too narrow.
- **Truncate at the end** for secondary metadata where the start carries the meaning: role, description, last message preview. Always pair with a way to see the full value.
- **Truncate in the middle** when items differ at the *end*: file names (`Q3-report…v12-final.pdf`), emails sharing a long domain, paths, hashes. End-truncation makes them identical.
- **Clamp** (`line-clamp: 2`) for multi-line previews in cards, so card heights stay predictable.
- **Never truncate** numbers, amounts, dates, or anything the user compares. Give them the room.

### Phase 5 — Report

Fix the clear breaks, leave the toggle running, and report in the format below.

### Phase 6 — Fix on request

After fixes, re-check Demo too: a fix for the worst case must not regress the demo. Keep the worst-case fixture as the regression test.

## Required Output Format

### Part 1 — What broke

One row per break, worst first. Severity: **Broken** (content unreadable, action unreachable, wrong data shown), **Ugly** (readable but visibly wrong: squished avatar, wrapped badge), **Fragile** (fine now, one realistic step from breaking: no limit, no fallback).

| # | Severity | Field | Worst-case value | What happens | Fix |
| --- | --- | --- | --- | --- | --- |
| 1 | Broken | `email` | `bartholomew.fitzgerald@northwind-industries-holdings.example.com` | Pushes the ••• menu off the row; menu unreachable at 400px | `min-width: 0` on text column, `overflow-wrap: anywhere` on email, `flex-shrink: 0` on menu |

Every row has `file:line` for the fix location in the Fix cell or directly below the table.

### Part 2 — Decisions for Kolin

Breaks with more than one right answer: truncate vs wrap for a field, what an empty role should show, whether a 1,000-row list paginates or virtualizes. One line each, with your recommendation and why.

### Part 3 — What held up

List the worst cases the component already handles. This shows the test was real and tells Kolin what not to touch.

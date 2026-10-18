Work only in `{{WORKTREE}}`. Run every command from there.

Task: the previous commit removed the Variant and Channels pages and their page ids (ADR 0163). Three older ADRs still describe them in the present tense. Bring those sentences up to date. This is a doc sync. It changes no code.

Facts to use (do not invent others):

- The page ids `demand.variant` and `demand.channels` are gone. `PAGES` still has `demand.demand-plan` and `supply.po-review`.
- `variantDetailPath()` is gone.
- ADR 0163 removed the `demand.topdown.edit` capability. Migration 0040 deletes its stored grants.
- `/edit/top-down` is now a legacy URL of the Demand Plan page (path `/demand/demand-plan`), as are the old Variant and Channels URLs.
- The four `top_down_*` tables and the `top_down` forecast method stay.

Recipe:

1. Census: `git grep -n -E 'demand\.variant|variantDetailPath|demand\.topdown\.edit|Variant page|/edit/demand-plan|/demand/variant' -- docs/adr/0054-top-down-allocation.md docs/adr/0130-app-shell-and-navigation.md docs/adr/0160-route-table.md`.
2. Rewrite a hit only when it describes the current state of the app. Leave text that describes the past on purpose, for example a section that says it "describes the page as it was", or an example of an old URL.
3. Keep each edit to the sentence that is wrong. Do not restructure paragraphs or add new sections.

Files you may edit: `docs/adr/0054-top-down-allocation.md`, `docs/adr/0130-app-shell-and-navigation.md`, `docs/adr/0160-route-table.md`. If another file has the same stale claim, stop and report it with file and line; do not edit it.

Gates, run after the edit and paste the output: `pnpm -s agents-refs`.

Report: files changed, each gate with its literal result, every census hit you left unchanged with the reason, and anything you inferred without running.

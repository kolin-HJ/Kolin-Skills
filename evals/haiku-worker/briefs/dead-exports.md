Work only in `{{WORKTREE}}`. Run every command from there.

Task: `pnpm deadcode` fails on unused exports in the new Segmentation code. Clear them, and rename the Segmentation scorecard's date formatter so it no longer shares the name `formatDay` with `@/lib/dates`. This is a codemod. It changes no behavior.

Recipe:

1. Run `pnpm -s deadcode` and list every finding.
2. For each unused export under `apps/web/src/lib/segmentation/` or `apps/web/src/app/(app)/demand/segmentation/`:
   - if something in its own file still uses it, remove only the `export` keyword;
   - if nothing uses it anywhere, delete the declaration.
3. Rename `formatDay` in `apps/web/src/app/(app)/demand/segmentation/scorecard-ui.ts` to `formatPeriodDay`, and update its importers. Do not touch `formatDay` from `@/lib/dates` or any of its callers.
4. Re-run `pnpm -s deadcode`. If a finding is outside the two Segmentation folders above, or the fix is anything other than step 2, stop and report it with file, line and the finding text.

Files you may edit: files under the two Segmentation folders above. Nothing else.

Gates, run after the edit and paste the output: `pnpm -s deadcode`, `pnpm -s typecheck`, `pnpm -s comments`, `node_modules/.bin/oxfmt --check <each file you changed>`, `pnpm --filter=@hj/web exec vitest run src/lib/segmentation`.

Report: files changed, each gate with its literal result, every finding you did not fix with the reason, and anything you inferred without running.

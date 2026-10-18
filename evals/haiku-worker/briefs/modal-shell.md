Work only in `{{WORKTREE}}`. Run every command from there.

Task: move raw overlays onto the paved `ModalShell` (`apps/web/src/app/(app)/_components/modal-shell.tsx`) and ratchet the `raw-overlay` baseline. This is a codemod. It must not change what a user sees beyond the shell's own chrome (header, close button, Escape, backdrop click).

Candidates, all under `apps/web/src/app/(app)/_components/`:

- `comments/comment-modal.tsx`
- `shortcuts-help-modal.tsx`
- `save-preview-modal.tsx`
- `global-search-modal.tsx`

Recipe per candidate:

1. Read `ModalShell`. Its API is `title`, `onClose`, `children` and optional `wide`. It owns the backdrop, the backdrop close button, the header with the title and the × button, the Escape handler and the padded body.
2. The modal fits when its chrome is a plain title, a close button, an Escape handler and a backdrop. Then replace the outer markup with `<ModalShell title=... onClose=...>`, keep the body content and its order, and delete the now-unused `useWindowEvent` Escape handler and its import. A subtitle line goes as the first child of the body.
3. The modal does not fit when it has chrome `ModalShell` cannot express: a custom header (for example a search input as the header), a different backdrop, or its own key handling beyond Escape. Then do not convert it. Stop on that file and report it with the lines that do not fit.
4. Remove each converted file's entry from `raw-overlay` in `scripts/rules-baseline.json`. Leave every other entry.

Files you may edit: the four candidates and `scripts/rules-baseline.json`. Do not change `modal-shell.tsx`.

Gates, run after the edit and paste the output: `pnpm -s rules`, `pnpm -s typecheck`, `pnpm -s comments`, `node_modules/.bin/oxfmt --check <each file you changed>`.

Report: files changed, each candidate converted or skipped with the reason, each gate with its literal result, and anything you inferred without running.

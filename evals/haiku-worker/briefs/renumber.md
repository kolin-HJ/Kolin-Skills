Work only in `{{WORKTREE}}`. Run every command from there.

Task: PR #668 took ADR 0163 and migration 0040 on `staging`. The Segmentation work moves to the next free numbers: ADR 0164 and migration `0041_segmentation`. This is a doc renumber. It changes no behavior.

Recipe:

1. `git mv docs/adr/0163-segmentation.md docs/adr/0164-segmentation.md`, then change its title line from `# ADR 0163 — ...` to `# ADR 0164 — ...`.
2. Census: `git grep -n -E '0163|0040_segmentation'`. For each hit that means the Segmentation ADR or the Segmentation migration, change `0163` to `0164` and `0040_segmentation` to `0041_segmentation`. Keep the rest of each line as it is, including link text and file names.
3. Leave every hit that means `docs/adr/0163-demand-tab-sections-and-summary.md` (the Demand tab ADR). That ADR keeps 0163.

Files you may edit: Markdown files only (`*.md`). If a non-Markdown file (TypeScript, JSON, SQL) needs a change, stop and report the file and line.

Gates, run after the edit and paste the output: `pnpm -s agents-refs` and `pnpm -s feature-map`.

Report: files changed, each gate with its literal result, every census hit you left unchanged with the reason, and anything you inferred without running.

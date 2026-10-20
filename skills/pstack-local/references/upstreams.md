# Other upstreams

Part of `pstack-local`.
- `thermo-nuclear-code-quality-review` (cursor-team-kit) is vendored and linked like pstack. Read it for the diff pass in AGENTS.md Quality work, or when the user asks for a harsh structure review. `senior-reviewer` already carries its approval bar.
- [ponytail](https://github.com/DietrichGebert/ponytail) is cloned to `~/.agents/vendor/ponytail`. `apply` links only `ponytail` and `ponytail-audit` (`VENDOR_SKILL_DIRS`). Use `ponytail` mode for all coding. Overrides: no `shortcut:` or why comment; each shortcut, its limit and its upgrade trigger go in the PR body `## Tradeoffs`. Its assert-based self-check follows AGENTS.md Tests and proof. Use `ponytail-audit` for a whole-repo report. Not linked: `ponytail-review` (`senior-reviewer` reads every diff), `ponytail-debt` (it lists `shortcut:` comments, which do not exist here), `ponytail-gain` (a benchmark card) and `ponytail-help` (plugin hooks and config not installed here).

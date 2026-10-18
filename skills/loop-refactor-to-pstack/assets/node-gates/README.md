# Reference gate tooling (JS/TS, pnpm)

These are copies of working scripts from a pnpm/Turbo monorepo that finished the zero-baseline program. They implement `references/gates-contract.md`. Copy the ones you need into the target repo's `scripts/` folder. Then adapt what is listed below, run each one once, and read its output before you rely on it.

| File | What it does | Adapt |
|---|---|---|
| `check-baselines.mjs` | The registry gate and `gates:status` (`--status`). It checks that every baseline is registered with target 0 and is a step the check command runs. | The `FORMATS` readers for your baseline formats. The `pnpm check` string it parses. |
| `check-files.mjs` | `gates:files <paths>`. It runs each gate's `--json` and prints the counts for the given paths. | The gate list, and the dead-code tool's command and name. |
| `lower-baselines.mjs` | `gates:lower`. It measures everything first and lowers only when nothing rose. | `RUN_AFTER_CONFIG_WRITES`: gates whose results depend on config files that other updates rewrite. |
| `check-baseline-ratchet.mjs` | The ratchet CLI: it reads each watched file at the base ref and at head, follows renames, and prints. Run it in CI on every PR and in the pre-push hook. | Nothing beyond its imports. |
| `lib/ratchet.mjs` and `check-baseline-ratchet.test.mjs` | The pure ratchet: one config per watched file, with shrink-only `entries` and grow-only `enforced` (`references/gates-contract.md`), and a test per loosening. | `CONFIGS`: the linter, dead-code and formatter readers for your tools, your test-runner config names, and the paths of your hooks and agent settings. `PINNED_PACKAGE`: the packages whose exact version is a gate setting (Effect by default). |
| `gate-policy.json` and `lib/gate-policy.mjs` | One file holding every owner list, guard list, scope and threshold the gates use, and its reader. | The lists, which start empty or at today's values. |
| `check-comments.mjs` | The no-comments gate. Directives a tool reads are exempt. | `SCOPES`, and the exempt directive patterns. |
| `check-file-length.mjs` | The 1,000-line limit. | `SCOPES`. |
| `check-agents-refs.mjs` and its test | Every backticked name in AGENTS.md must exist in the tree. `~~name~~` marks something removed, which must stay absent. `EXTERNAL_NAMES` holds names that live outside the repo, each with a reason. | `SYMBOL_SCOPES`, `WORKSPACE_ALIAS_TARGET`, `EXTERNAL_NAMES`. |
| `agent-guard.mjs`, its test, and `claude-settings.example.json` | A Claude Code PreToolUse hook that blocks `--no-verify`, `git commit -n`, changes to `core.hooksPath`, and a push to a protected branch. Malformed input passes, so a parser bug cannot lock agents out. Install it as `.claude/settings.json` only after the user says yes. | `PROTECTED_BRANCHES`. |
| `trust-curve.mjs` and its test | `pnpm trust`: the share of PRs merged into the base branch that needed a `fix` or revert on mostly the same files within a window. It is the number that says whether the gates and reviews hold. | `FOLLOW_UP_TITLE` if the repo does not use Conventional Commits, and `SHARED_FILES`. |
| `lib/ast.mjs` | Small TypeScript AST helpers for rule counters. | None. It needs `typescript` installed. |
| `lib/comments.mjs`, `lib/write-json.mjs` | The comment scanner `check-comments.mjs` uses, and the `--json` writer every gate uses. | None. |

Wire them in as `package.json` scripts: `gates:files`, `gates:lower`, `gates:status` (`node scripts/check-baselines.mjs --status`), and one script per gate. Add each gate to the single check command, and make CI run that command as one step.

Each file still reflects the repo it came from, for example the `.agents/skills/verify-supply-chain` paths in `SCOPES`. Replace those paths; do not keep them.

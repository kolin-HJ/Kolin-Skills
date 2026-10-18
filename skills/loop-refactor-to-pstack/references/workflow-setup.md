# The workflow a pstack repo ends with

The refactor makes the code clean today. The workflow keeps it clean when the next agent arrives with no context. Install each row in Phase 1 or Phase 2 as its own unit, and prove each row the way its last column says. The templates in `assets/workflow/` come from a repo that finished this program. Adapt their paths and branch names before use.

| Piece | What it is | Template | Proof |
|---|---|---|---|
| One instruction file | `AGENTS.md` at the root and no `CLAUDE.md` copy. It routes every task through poteto-mode, lists where the repo's rules win over pstack, and names the gates, the verify CLI, the code rules and the writing rules. | `assets/workflow/AGENTS.template.md` | `agents-refs` passes, and a fresh agent asked "how do I fix a bug here" names the bug-fix playbook and the verify CLI |
| Vendored pstack | The pstack skills under `.agents/skills/` at a pinned commit, with `.claude/skills/` and `.cursor/skills` links, the license, and a sync script that refuses to overwrite a repo-owned skill | `assets/workflow/sync-agent-skills.sh` | `sync-agent-skills.sh --check` passes and runs in the check command |
| `.pstack/` | `README.md` (where everything lives, operator prompts), `quality-gates.md` (the done checklist by change type), `models.md` (model roles), `program.md`, `architecture.md` and `decision-log.tsv` from this program | The folder this program writes | Every link in `README.md` resolves |
| Verification skill | The project-local skill from `create-verification-skill`: launch, doctor, drive, evidence, cleanup, a feature map with a gate for unmapped pages, and pair parity | Phase 2 | `maintain-verification-skill` ends `clean` |
| Verifier agent | A read-only agent that proves a change it did not write through the verification skill, and returns the PR's Verification block | `assets/workflow/verifier.md` | One run on a real branch returns **Proven** or names what it could not prove |
| Reviewer | The repo's reviewer agent (`senior-reviewer` on this machine), pinned by `assets/check-subagents.sh` | `~/.claude/agents/` | `check-subagents.sh` prints `ok` |
| PR template and proof check | `## Why`, `## Scope`, `## Tradeoffs`, `## Blast Radius`, `## Verification`. A CI check fails a PR whose Verification section has no `Ran:` line, or a `Not run:` line with no reason, or an app change with no verify or parity run | `PULL_REQUEST_TEMPLATE.md`, `check-pr-proof.mjs` with its test, `pr-proof.yml` | Its tests pass, and a planted body with only `Ran: \`<check command>\`` on an app change fails |
| Agent guard | A PreToolUse hook that blocks `--no-verify`, `commit -n`, `core.hooksPath` changes and pushes to protected branches | `assets/node-gates/agent-guard.mjs`, `claude-settings.example.json` | Its tests pass, and `git check-ignore -v .claude/settings.json` shows the file is tracked |
| Trust metric | `trust` reports the share of merged PRs that needed a fix or revert on the same files within a window | `assets/node-gates/trust-curve.mjs` | It prints a rate for the last 30 days |
| Issues as specs | Specs live as markdown in the repo (for example `.scratch/<feature>/spec.md`), with reproduction on the running app before any fix | A short section in `AGENTS.md` | Skip when the repo already uses an issue tracker the user named |

Install the pieces in this order: instruction file, vendored pstack, gates, verification skill, verifier, PR proof, agent guard, trust. Each later piece names the earlier ones, so the order keeps every `agents-refs` run green.

## The instruction file

Keep it under about 200 lines, because it loads on every turn. It holds the rules a tool cannot check and points to the gate for each rule a tool can check. Reference material goes to `docs/` or `.pstack/` and is opened on demand. When a rule is needed a second time, it moves to a gate and the prose shrinks to a pointer (`principle-encode-lessons-in-structure`).

`correct` keeps the instruction file's rule table: one row per mistake class, with the check that enforces it. A row whose check does not exist yet is a defect in the program's predicate (row 5).

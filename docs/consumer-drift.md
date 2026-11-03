# Consumer drift

Kolin-Skills is the pin. A consumer that copies pstack or `senior-reviewer`, or that still requires a bolted-on reviewer on every PR, can fall behind. This check fails when those copies disagree with this repo. Same-session proof is the quality gate (#90); a separate reviewer is not.

```sh
kolin-skills check-drift /path/to/repo
kolin-skills check /path/to/repo
```

Both scan only that tree. Bare `kolin-skills check` is still this repo's gate and stays green on Kolin-Skills `main`.

| Marker | Compared to |
|---|---|
| `.agents/PSTACK.SOURCE` (`commit:` / `rev:` / `sha:`) | `upstream/vendor.json` → `cursor-plugins.rev` |
| `upstream/vendor.json` or `.agents/vendor.json` → `cursor-plugins.rev` | the same pin |
| `.agents/vendor/cursor-plugins` `HEAD` | the same pin |
| `.claude/agents/senior-reviewer.md` (real file or symlink) | `agents/senior-reviewer.md` (SHA-256; a link into this repo matches) |
| `AGENTS.md`, `CLAUDE.md`, `.claude/CLAUDE.md`, `.claude/AGENTS.md`, `policy/AGENTS.md` | fail when the text requires a separate reviewer on every PR or every staging merge (including the old 150-line pre-PR spawn). High-risk / ask-only language passes. |

No marker: pass. A recorded rev may be a unique abbreviation of the full pin. Policy files that say reviewers are on demand, or only for high-risk work or an ask, pass.

## hj-supply-chain (later PR)

It vendors pstack into `.agents/skills` at `df58112` through `scripts/sync-agent-skills.sh`, weeks behind the pin (`c742dd61`, pstack 0.15.36). `.claude/agents/senior-reviewer.md` is a 148-line "synced" copy; this repo's file is 59 lines after #64/#65/#69.

Stop vendoring pstack in that repo. Point the machine at a Kolin-Skills checkout and run `kolin-skills apply` so home links the pin. Replace or delete the synced reviewer so apply can link `agents/senior-reviewer.md`. Do not do that in this PR.

## Box re-apply (later PR)

Own-skill links still target `/tmp/kolin-skills-main` (stale, still names `foundation` and `gap-audit`, missing `repo-standard`). Follow [`stay-on-main.md`](stay-on-main.md). Do not rewire the box in this PR.

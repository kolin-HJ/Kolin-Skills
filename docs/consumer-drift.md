# Consumer drift

Kolin-Skills is the pin. A consumer that copies pstack or `senior-reviewer`, or that still enforces a stale per-PR reviewer/interrogate gate (old 150-line rule, `Ran: senior-reviewer` receipts, `interrogate` on every PR), can fall behind. Same-session proof comes first, with one fresh-context merge-ready review (`senior-reviewer` or `judge`) and `interrogate` strictly high-risk or ask-only. This check fails when consumer copies disagree with this repo.

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
| `AGENTS.md`, `CLAUDE.md`, `.claude/CLAUDE.md`, `.claude/AGENTS.md`, `policy/AGENTS.md` | fail when the text keeps stale per-PR reviewer or `interrogate` mandates (every staging merge, old 150-line pre-PR spawn, `Ran: senior-reviewer` receipts). The canonical fresh-context merge-ready review and high-risk / ask-only `interrogate` language pass. |

No marker: pass. A recorded rev may be a unique abbreviation of the full pin. Policy files that say reviewers are on demand, or only for high-risk work or an ask, pass.

## hj-supply-chain (later PR)

As of 2026-11-22 on `origin/staging`, it vendors pstack into `.agents/skills` at `df58112` through `scripts/sync-agent-skills.sh`, behind the pin (`005d8f6e`, pstack 0.15.48), so `check-drift` fails there. Its synced `.claude/agents/senior-reviewer.md` is gone; only its own `verifier` remains.

In Claude Code the home skill wins over a repo skill of the same name, so the vendored copy only serves agents with no wired home, such as cloud agents. Stop vendoring pstack in that repo once those agents can run `kolin-skills install`. Do not do that in this PR.

# Consumer drift

Kolin-Skills is the pin. A consumer that copies pstack or `senior-reviewer` can fall behind. This check fails when those copies disagree with this repo.

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

No marker: pass. A recorded rev may be a unique abbreviation of the full pin.

## hj-supply-chain (later PR)

It vendors pstack into `.agents/skills` at `df58112` through `scripts/sync-agent-skills.sh`, weeks behind the pin (`164ced10`, pstack 0.15.34). `.claude/agents/senior-reviewer.md` is a 148-line "synced" copy; this repo's file is 59 lines after #64/#65/#69.

Stop vendoring pstack in that repo. Point the machine at a Kolin-Skills checkout and run `kolin-skills apply` so home links the pin. Replace or delete the synced reviewer so apply can link `agents/senior-reviewer.md`. Do not do that in this PR.

## Box re-apply (later PR)

Own-skill links still target `/tmp/kolin-skills-main` (stale, still names `foundation` and `gap-audit`, missing `repo-standard` / `council` / `modernize`). Clone to a persistent path (`~/Kolin-Skills`), fast-forward `main`, then `python3 "$PWD/bin/kolin-skills" apply --adopt`. Apply prunes the deleted skills and links the new ones. Do not rewire the box in this PR.

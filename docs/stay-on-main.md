# Stay on main

Every coding environment uses this repo's `main`. Claude Code and Codex run `kolin-skills pull` at SessionStart. Cursor and Grok do not: they read links that `apply` already wrote. Do not add a Cursor or Grok SessionStart pull; `cursor/hooks.json` is `postToolUse` lint only, and Grok has no hooks.

T3Bot owns apply verification on T3 DEVS and the home Mac. Box re-apply and hj-supply-chain unvendor are follow-ons: [`consumer-drift.md`](consumer-drift.md).

## Recipe

Use a persistent clone. Never `/tmp`. Default path: `~/Kolin-Skills`.

`apply` writes into `$HOME`. Use the account the agents on that machine use. Invoke the CLI from the checkout on current `main`, not `kolin-skills` on `PATH`. A worktree is the wrong checkout; `pull` only updates the wired clone, and only when it is clean `main`.

```sh
cd ~/Kolin-Skills
git fetch origin
git switch main
git merge --ff-only origin/main
python3 "$PWD/bin/kolin-skills" apply --adopt
python3 "$PWD/bin/kolin-skills" check
```

`--adopt` when `~/.kolin-skills/state.json` names a different checkout. Skip it when this checkout already owns home. `install` is only the first run on a machine (it also fetches third-party skills).

An old install keeps its old hooks until home is wired to current `main`. Those hooks can block commands that current `main` allows. Do not change hook behavior to work around that. Run this recipe.

## Verify

1. `jq -r .repo ~/.kolin-skills/state.json` is this checkout's absolute path.
2. `git -C "$(jq -r .repo ~/.kolin-skills/state.json)" rev-parse HEAD origin/main` prints the same SHA twice.
3. `check` prints `Passed:`.

Vendoring consumers, optional: `kolin-skills check-drift <consumer-repo>`. What it compares: [`consumer-drift.md`](consumer-drift.md).

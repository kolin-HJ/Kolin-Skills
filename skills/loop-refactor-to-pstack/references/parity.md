# Parity that is fast and still proves "nothing changed"

Parity drives every feature map on the base branch's app and the work branch's app and compares what a user would see. Measured on 2026-09-30 in an earlier program, the lockstep pair below took 13m39s where the three-run bracket took about 27 minutes, and it caught a real change the bracket had been misread as drift.

## The contract the verify CLI needs

- `VERIFY_ROOT=<checkout>`: every path the CLI derives (the app directory, its state file, logs, browser profile) comes from that root, so one driver drives any checkout's app.
- `launch --fresh --port N`: a fresh server and an empty data cache, on a port the caller picks, so two apps can start at once.
- The parity driver accepts `--list` (print the feature names), `--only a,b`, `--out <file>`, `--no-doctor` (skip the health check when the caller already ran it), and `--observed <file> --against <file>` to compare saved runs.

## The method (`assets/parity-pair/`)

1. **One set of recipes for both sides.** Run the work branch's driver against both apps through `VERIFY_ROOT`. Never copy the verify skill into the base checkout: the copy goes stale, and features added since the copy are never really compared.
2. **Launch both apps fresh, at the same time,** on two free ports.
3. **Lockstep.** Run each feature on both apps at once and wait for both before the next. Both apps fetch each upstream dataset within seconds of each other, and their cache expiries line up, so moving data rarely shows as a difference. Running the two whole suites side by side without lockstep was worse than sequential runs: the suites drift apart in time and each fetches a dataset at a different moment.
4. **Recheck what differs, on fresh apps, in lockstep.** A change counts only when both passes show it (`pair-verdict.mjs`). A difference seen once is data that moved. A failure that no feature owns, or another process writing the shared database, stops the verdict instead of being skipped.
5. **Prove the check can fail.** Plant a small change in the work checkout (for example multiply one displayed value by 1.01), run the pair with `--only` on that feature, confirm it is reported in both passes and names only that column, then restore the file.

## Recipes beyond read-only

Read-only recipes cannot see a save, a deep link or an error path. Add a driven recipe the first time a wave touches one, and before any Effect wave reaches its code:

- **Error paths.** One recipe per failure a user can reach (a rejected upload, an unauthorized save, an upstream outage simulated through the verify CLI). It records the message and status the user sees.
- **Saves.** Drive the write against the local database, read the side effect back with the CLI's read-only SQL, then restore. Never during a lockstep run, because both apps share the database.
- **Timing.** Record page timings (median of N) beside the fingerprints for pages whose loaders a wave rewrote. A slowdown past noise counts as a difference.

## The one tradeoff

Both apps run the work branch's recipes, so a recipe the branch deletes or narrows stops being compared. Review any change to the recipes as a change to what parity proves.

## What does not work

- **Seeding the work app with the base app's data cache.** Next's `unstable_cache` keys include the callback's source text, so every loader the change edited misses the copied cache and fetches live, while the base app serves its older cached copy. That guarantees a difference exactly where the change touched code.
- **Explaining a difference as drift by argument.** Show it: a difference that reproduces in two lockstep passes is code. In one earlier program such a row was an intended fix, not drift.

## Base drift

After each base merge into the program branch, move the base checkout to the new base tip: `git -C <base checkout> fetch origin <base> && git -C <base checkout> checkout -q --detach origin/<base>`. Then reinstall its dependencies only when the lockfile changed, and relaunch its app fresh. Never delete or re-create the base checkout during a run, and never run two parity runs against one base checkout.

## Fallback

`assets/bracket-parity.sh` runs base, work, base in sequence and counts a row only when the work run differs from both base runs. Use it only when the verify CLI cannot target another checkout.

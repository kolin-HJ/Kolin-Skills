# Trust audit

A gate is only as strong as the easiest way around it. Walk this table before landing, and again whenever a new gate or config appears. Each row lists a way an agent under pressure can turn a red gate green without fixing code, what blocks it, and how to prove the block works. Prove a row by planting the loosening on a scratch branch and watching the named check fail. Then restore the file. A row is closed only when that proof has run, or when the user decided to leave the row open.

## In-repo: tamper evidence (the ratchet, in CI, on every PR)

| Way around | Block | Proof |
|---|---|---|
| A lint-disable, `@ts-expect-error` or `@ts-ignore` | The `suppression` rule | Add a directive and watch `rules` fail |
| Turning a lint rule, plugin or category off, adding an `ignorePatterns` entry or an override that excludes files | The ratchet over the linter config: enforced keys may not disappear, and exemptions may not grow | Set one rule to `off` and watch the ratchet fail |
| Adding a dead-code `ignore*`, `entry` or boundary `allow` | The ratchet over the dead-code config | Add an ignore |
| Recreating a baseline file, for example with `deadcode:baseline` | The registry gate: an unregistered baseline file fails, and the ratchet fails a registry entry that grows | Create `x-baseline.json` |
| Adding a file to a paved hook's owner list, a function to the guard lists, or a path to a hex or catch owner list | The policy lists live in `gate-policy.json`, which the ratchet treats as shrink-only | Add an owner |
| Shrinking a gate's scopes or raising `maxFileLines` | The scopes and banned names in `gate-policy.json` may only grow, and the threshold may only fall | Remove a scope path |
| Turning `strict` (or `noUncheckedIndexedAccess`, and so on) off or dropping `extends` in any tsconfig | The ratchet over every tracked `tsconfig*.json` | Set `strict` to `false` |
| Removing a step from the check command, or changing a gate script's command to `true` | The ratchet over the check steps and their commands, and over each workspace's lint, typecheck and test scripts | Drop `pnpm guards` from `check` |
| Editing CI or the deploy workflow to skip a step | The ratchet over workflow command lines (`run:` lines and shell continuation lines, never YAML keys), counted, plus shrink-only bypass lines (`if:`, `continue-on-error`, `\|\|`, `; true`, `exit 0`, `set +e`, `--no-verify`) | Change the `pnpm check` line; add `if: false` |
| Editing the ratchet so it passes itself | CI runs the ratchet a second time with the base branch's copy of the ratchet code | Weaken an extractor in a PR; the second step still fails |
| Deleting the ratchet steps from the PR's own workflow | Nothing in-repo: a PR runs its own workflow copy. Needs a required status check or review (server side) | Not provable without a ruleset |
| Narrowing the test runner's include list, or renaming a test so it is never picked up | The ratchet over the runner config, plus the `test-file-name` rule | Change the include line |
| Adding a formatter ignore | The ratchet over formatter `ignorePatterns` | Add a pattern |
| Weakening a gate's own logic | The gate's fixture tests run in the check command. What remains is review (see below). | Mutate a counter and watch its fixture fail |
| Deleting or gutting a failing test | Test-shape rules: `expect` required, no skip or only. Deletion itself is visible only in review, and some harnesses' permission checks block it, which is good. | Not gate-provable; it needs review |
| Breaking the ratchet itself | The ratchet's own tests | Mutate an extractor |
| Removing the Effect language-service plugin from a tsconfig, or lowering a diagnostic's severity | The ratchet over each tsconfig's `plugins` entry and its diagnostic severities (enforced keys) | Set `floatingEffect` to `warning` |
| Running an Effect outside the edge, or adding a file to the runtime owner list | `effect-run-outside-edge`, with the owner list in `gate-policy.json` | Call `Effect.runPromise` in a service |
| Silencing a diagnostic with an `@effect-diagnostics` comment | The comments gate rejects every comment | Add one |
| Floating an Effect version | The ratchet watches the exact `effect` and `@effect/*` versions | Change `4.0.0` to `^4.0.0` |

## Local enforcement: before code leaves an agent

| Way around | Block | Proof |
|---|---|---|
| Committing without running anything | A pre-commit hook runs the formatter check and `gates:files` on the staged files | Stage a file with a comment; the commit fails |
| Pushing red code | A pre-push hook runs the check command and the ratchet against the base branch, failing loudly if the base ref is missing | Push a branch with a failing test |
| Hooks never installed | A `prepare` script sets `core.hooksPath` inside a git work tree and does nothing elsewhere (CI, Vercel) | Run `pnpm install` in a fresh clone, then `git config core.hooksPath` |
| The agent settings file is gitignored, so the guard never ships | `git check-ignore -v .claude/settings.json` prints a negation rule, and the ratchet watches the file once tracked | `git ls-files .claude/settings.json` lists it |
| `--no-verify`, `commit -n`, or setting `core.hooksPath` elsewhere | An agent PreToolUse hook (`.claude/settings.json`) blocks them. Only Claude Code reads that file; other agents rely on the server side. | Feed the hook the command JSON; it exits 2 |
| A push straight to `staging` or `main`, or a force-push | The same agent hook, plus the server side | Feed it `git push origin HEAD:main` |

Hooks and agent settings are sensitive: the harness's permission check may refuse a worker that writes them. Get the user's explicit approval, then write them yourself or re-dispatch under that approval. Never route around a refusal.

## Server side: what no local trick can bypass

| Way around | Block | Proof |
|---|---|---|
| Merging with red CI | A ruleset requiring the CI status check on every long-lived branch | `gh api repos/<o>/<r>/rulesets/<id>` shows `required_status_checks` |
| Pushing to the integration branch directly | A ruleset requiring a PR on that branch too, not only the default branch | The same API call |
| An agent approving or labelling its own gate change | Code-owner review required on gate machinery, with a CODEOWNERS file covering `scripts/`, configs, workflows, hooks and `AGENTS.md` | The ruleset shows `require_code_owner_review: true` |
| Deploying unchecked code | The production deploy workflow runs the full check command before deploying | Read the workflow. It must run the same command as CI, not a subset. |
| A secret committed to the tree | Secret scanning in pre-commit and CI (a new tool, so the user decides). A secret already committed is burned: rotate it. | Commit a fake key pattern |

The ratchet's bypass label (`allow-baseline-growth`) is a speed bump, not a gate, unless a human must approve the PR. Say so in the report whenever the server-side rows are open.

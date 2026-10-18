# Gates contract

Every stack needs these behaviors. The JS/TS reference implementations are in `assets/node-gates/`. Port the contract, not necessarily the code.

## The gate command
- One command runs every gate in order and exits non-zero on the first failure. CI runs exactly this command as one step.
- Each gate prints one success line with its counts, for example `no new comments: 0 baselined`, so a log shows state at a glance.

## Each gate that allows a baseline
- `--check` (the default) fails on any finding above its baseline, and also on a stale entry: a count that is now lower than allowed. Stale entries fail so that a fix gets locked in.
- `--json` prints `{ rows: [{ file, key, current, allowed }] }` for every file and key it knows. The shared tools read this.
- `--update` only lowers or drops entries. It never raises or adds one, and it refuses with a message if a count rose.
- `--init` or `--init-rule <id>` seeds from scratch. It is used once, by the coordinator, when a gate or rule is introduced.
- When its baseline file is missing, the gate treats the allowance as zero.

## The registry: `scripts/baselines.json`
```json
[
  {
    "file": "scripts/rules-baseline.json",
    "gate": "rules",
    "format": "nested",
    "unit": "raw-date B1 (lib/dates.ts); swallowed-error B3 (bestEffort)",
    "target": 0
  }
]
```
- `format` tells the tools how to read the file: `per-file` (`{ file: n }`), `nested` (`{ key: { file: n } }`), `listed` (an array of keys), `lint` (package, then rule, then file), or a tool-specific format such as a dead-code tool's.
- `unit` names the work that burns the baseline down. An entry without an owner is not allowed.
- The registry gate fails if a baseline file exists without an entry, an entry points at a missing file, or a target is not 0.

## Shared tools
- `gates:files <paths>` runs every gate's `--json` and prints, per path and per gate, "N now, baseline M". It also prints rises in the given paths, rises elsewhere, and stale entries. Workers use it on their own files.
- `gates:lower` measures every gate first. If any count rose, it refuses and writes nothing. Otherwise it runs each gate's `--update`, restores a file if an update would have raised anything, and prints before and after totals. Gates whose results depend on config files others rewrite run last.
- `gates:status` prints every registered baseline with "baseline N in F files, now N, target 0" and its unit. It ends with the count of baselines left, and the program is done when that count is zero.
- **The ratchet:** in CI and in the pre-push hook, it compares every baseline file and every gate setting against the base branch, and fails if anything loosened. It allows growth only with an explicit PR label and a written reason. Its contract is below.

## Retiring a baseline
When `gates:lower` empties a baseline, delete the file and its registry entry. Rewrite the doc that described it to say there is no baseline and that any finding fails. Remove any per-file override the linter config carried for it.

## Rules engine (AST-based)
- Each rule is a named counter, `count<Thing>(sourceFile)`, in a shared module, with fix text that names its paved path.
- It has one fixture it flags and one it must not flag, each seen failing under a mutation of the counter.
- It is scoped by path (for example, the app's source but not tests or the helper that owns the raw form), and baselined per file.
- For JS/TS, a small AST helper module (`unwrap`, `calleeName`, `importBindings`, `localInitializers`) keeps counters short. See `assets/node-gates/lib/ast.mjs`.

## Gate policy: `scripts/gate-policy.json`

Every value that decides what a gate lets through lives in this file, never as a constant in gate code:

- owner lists, such as the files allowed to call a raw hook, catch deliberately or use a hex colour;
- the function names that count as authorization guards;
- the folders each gate scans;
- banned file names;
- numeric limits, such as the maximum file length.

A small reader module exposes the file to the gates. Gates that must not load a parser (TypeScript) import that reader, not the rules library.

## The ratchet

The pure part lives in its own module (`assets/node-gates/lib/ratchet.mjs`) and has tests. The CLI only reads the base ref with git and prints. Each watched file has a config with one or both of two extractors:

- `entries` maps a key to a count. These keys may only shrink: a new key, or a higher count, fails.
- `enforced` returns a set of keys. These may only grow: a key that disappears fails.

Base keys follow renames, so a moved file keeps its allowance.

| File | Entries (shrink-only) | Enforced (grow-only) |
|---|---|---|
| Linter config | Rules or categories lowered, ignore patterns, override excludes | Rules at error, plugins, type-aware mode |
| Dead-code config | `entry`, `ignore*`, rules lowered, boundary allows | None |
| Every `tsconfig*.json` | Strict-family flags set to `false`; a language-service diagnostic below `error` | `extends`, `include`, strict-family flags set to `true`, each compiler plugin, and each plugin diagnostic at `error` |
| Root `package.json` | None | Each step of the check command, each step script's command, and the exact version of each pinned package (`effect`, `@effect/*`) |
| Workspace `package.json` | None | The `lint`, `typecheck` and `test` commands, and the exact version of each pinned package |
| Formatter config | Ignore patterns | None |
| CI and deploy workflows | Bypass lines: `if:`, `continue-on-error`, `\|\| true`, `exit 0`, `--no-verify` | Every non-comment line |
| Git hooks and agent settings | Bypass lines, which are free in a file the base lacks | Every non-comment line |
| Test runner configs | Lines choosing tests: `include`, `exclude`, `passWithNoTests`, `testNamePattern`, `bail` | Every non-comment line |
| Gate policy | Owner and guard lists, and `maxFileLines` as a count | Scopes, banned names, and that `maxFileLines` exists |
| Library-limit list and public-entry list | Each entry | None |
| Every registered baseline | Each entry, in the baseline's own format | None |

Prove each watched file kind once, plus one case where the PR edits the ratchet itself, with a test that plants the loosening and asserts the exact `dropped` and `raised` lists. Watch each test fail under a mutation of the extractor it protects.

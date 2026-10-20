# Brief templates

The brief is the product (Orchestrate, The brief). A worker inherits none of your context and cannot ask a question, so a vague brief fails quietly. Spawn it on `poteto-agent` or the repo's implementer, which run Sonnet 5.5 at medium effort and load pstack first; built-in agents load neither pstack nor the user's rules (`references/subagents.md`). Quote every rule the task depends on, and write for that tier: exact files, exact commands, the output that means done, and the cases where the worker must stop.

Every spawn carries all nine fields. A field you cannot fill is a unit you have not scoped. Size the brief to the unit: a one-command unit collapses the template to a paragraph that still names goal, scope, verify and report.

```
GOAL         one sentence, the outcome, executable by a stranger with no chat access
SCOPE        paths this unit may write; paths it may not; the worktree and branch
CONTEXT      files and ADRs to read first; upstream reports pasted in full when this unit depends on them
ACCEPTANCE   checkable criteria, one per line
VERIFY       exact commands with the output that means done, plus known gotchas
TIMEBOX      a rough cap; on expiry, stop at a clean file boundary and report what is done
FORBIDDEN    git writes, other lanes' files, baseline files, gate policy, plus unit-specific bans
REPORT       reports/<brief>.md: status, files, counts before and after, sites left with reasons, behavior changes, commands run with their final lines
STANDING     preferences.md (local spawns may cite its path; paste it verbatim on every resume)
```

When the user reads the brief, or when the harness takes a short prompt (a T3 or chat thread), lead with five headings that fold the nine fields: **Goal** (GOAL), **Done when** (ACCEPTANCE), **Evidence** (VERIFY and REPORT), **Constraints** (SCOPE, CONTEXT, FORBIDDEN, STANDING) and **Stop when** (TIMEBOX and the stop cases). Cite the plan sections and skills the unit must follow by path.

## Codemod first

A deterministic lever beats fan-out (principle-build-the-lever). For a mechanical rule:

1. Do the first few sites by hand to learn the recipe.
2. Write the codemod (ts-morph, jscodeshift, ast-grep or the repo's AST helpers). It rewrites only the shapes it is sure of and prints every other site with a reason.
3. Prove it: rerun it on the hand-done sites and diff, run it twice and see no second change, run the gates on its output.
4. Run it yourself, as one commit per folder.
5. Fan out lanes only for the sites it printed, which need judgment.

Commit the codemod under `scripts/codemods/` when later waves will rerun it, otherwise keep it in the store's `research/`.

## Common brief (one per wave)

```markdown
# Wave <id>: <rule(s)> onto <paved path(s)> (common brief)

GOAL: every site of <rule> in your lane's files moves onto <paved path>, with no behavior change except the one named below.
The user's words: "<the goal>", "<the bar>".

SCOPE: the files your lane brief lists, in <worktree> on <branch>. Other lanes edit other files at the same time.

## Rule N: `<rule-id>` onto `<paved path>`
- What the rule flags, in one sentence.
- The rewrite as a code shape, for example `start(() => runAction(async () => { ... }, { onError }))`.
- What stays the same: the body, statement order, the success path, the guard first.
- The one intended behavior change, if any. Name it per site in the report.
- Leave the site unchanged and report it when: <each case that would change behavior>.

## Code rules (quoted from AGENTS.md)
- <no comments; no any, as or non-null assertion; imports at the top; a directive stays on the first line; smallest change>

ACCEPTANCE
- The rule reads 0 in each file you own, except the sites you report.
- No other gate rose anywhere.

VERIFY, from the worktree root
- `<gates:files> <every file you changed>`: no rise; stale entries are expected.
- `<typecheck>`: 0 errors in your files.
- `<lint> <your files>`: clean.
- `<tests next to your files>`: pass.

FORBIDDEN: git add, commit, stash, checkout; `--update` or `--init` on a gate; formatting files you did not change; running the app; writing a database; editing shared helpers, baseline files, gate policy, AGENTS.md or skills.

Stop and report when a file has changes you did not make, a check fails twice, a site needs a file outside your list, or a change would alter the success path.

TIMEBOX: <minutes>. REPORT: as in the template. STANDING: <store>/preferences.md.
```

## Lane brief (one per lane)

```markdown
# <lane id>

Read `briefs/<wave>-common.md` first. This lane owns only these files (sites from the codemod's report or the baseline file):

- `<path>`: <rule> <n>, <rule> <n>
```

Generate the lane lists with a short script. Group files by folder so lanes never share a file.

## Effect migration brief (adds to the common brief)

```markdown
CONTEXT: read node_modules/effect/AGENTS.md, the ai-docs files named below, the program's Effect ADR, and references/effect.md (Legacy to Effect, Traps). The paved modules are <runtime, action, route, page adapters, services>; use them, never ManagedRuntime or Effect.run* directly.

Rewrite: <the legacy form> becomes <the Effect form>, keeping <the column "Keep identical" for this row>.
- Every Effect.all and Effect.forEach states `concurrency`, matching the legacy parallelism.
- Expected failures are Schema.TaggedError values from <errors module>; do not throw inside Effect.gen.
- Pure functions stay plain functions. Do not wrap math or formatting in Effect.
- Tests use the service's layerTest with @effect/vitest; no vi.mock, no fake timers.

VERIFY adds: `effect-language-service diagnostics --project <tsconfig>` shows no new diagnostic in your files.
Leave and report: any site whose error message, status code, write order or retry timing would change.
```

## Split brief (file-length wave)

- A pure move into sibling files in the same folder, named for what each owns. Copy code byte for byte: no renames, no merged helpers, no bug fixes.
- Hooks stay in their component. A custom hook moves only as a whole contiguous block, called at the same position.
- Every export stays exported from the original file, and no re-export shim is added.
- No runtime import cycles. Shared pieces move into a leaf file.
- A new sibling holding components or hooks gets the same client or server directive on its first line.
- Every file ends under the limit, with room for later waves.
- Rule hits that move with code show up as rises in the new files. Report them as moved hits; the coordinator re-keys them.

## Verifier brief (the riskiest lane)

Run it on `senior-reviewer` in a fresh thread that did not build the lane. Hand it the user's words, the files in scope, the decisions it must not re-raise, and the load-bearing invariants quoted from `AGENTS.md`. Then an ordered checklist, for example:

1. Hook and effect order compared with HEAD.
2. Each moved body compared with the original at the token level.
3. Closures that could now go stale.
4. Sequencing refs and batching paths.
5. For Effect waves: concurrency, interruption of writes, error messages at the edge, every `yield*` present.
6. A missing directive.

Ask for `file:line`, the failing scenario, the fix risk and a confidence level, in under 700 words, plus what it did not check. Record the verdict with `orch ledger record`.

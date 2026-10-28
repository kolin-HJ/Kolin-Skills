# Review checklist for a lane's report

Every item on this list cost a failed parity run, a broken page or a hidden regression in a real program. Check each one before you accept a lane.

## Claims
- **Re-run the gates yourself.** A lane can report its typecheck as clean while another lane's in-progress edits hide its errors, or it can simply miss a missing import after a move. Run the whole gate command after integration.
- **Read the deviation list, not only the summary.** "Moved three inline pieces into module functions" is a code change. Diff each body against HEAD, and check that the memo dependencies still match.
- **A count that drops in a pure move is a red flag.** It usually means code moved somewhere the rule cannot see: into a helper that takes a ref, or behind a starter passed down as a prop. Close the rule gap and re-key the hit to its new file. Record the rest as open debt. Never claim a drop like this as a fix.
- **Take any behavior change a lane names seriously**, such as "now throws instead of returning `{ ok: false }`" or "now rejects NaN". Trace the UI path that feeds that value and check whether a user can reach it.

- **Diff the changed-file list against the union of the lane lists before reviewing hunks.** A lane that ran the formatter with no arguments reformatted vendored skills nobody owned. Make the formatter config ignore vendored folders so a bare run is harmless, and tell lanes to pass file arguments.
- **An independent reviewer's "no findings" is a lead too.** One reported no added never-check while a lane had added one. Grep for each hunk a lane names in its report.

## Moves and imports
- **No re-export shims.** Point the importers at the new module and delete the re-export.
- **A directive must stay on the first line.** A script that prepends an import above `"use client"` turns the directive into a plain expression, and the whole app fails to compile. Type checks and linters pass anyway. Add a rule that counts misplaced directives, and use parity or an app launch as the compile check.
- **Two same-named exports with different behavior.** A dead-code tool flags them as duplicates. If they really behave differently (for example, one returns NaN where the other throws), rename one for its behavior rather than merging them.
- **Exports that become unused.** Replacing parameter annotations with schemas leaves exported types unused. Drop the `export` if the file still uses the type, and delete the type if nothing does. A type that appears in another module's inferred return type must stay exported and be named at that use.

## Paved helpers
- **A best-effort wrapper must handle thenables.** `instanceof Promise` misses ORM query builders, so a rejection escapes the wrapper. Use `await` inside `try`, and keep a separate function for sync work.
- **An action runner must rethrow the framework's control-flow errors** (redirect, not-found) before it reports an error.
- **Never wrap code that can redirect in a catch-all.** Leave those sites and report them.
- **Before seeding a swallowed-error rule, make it cover both forms:** `.catch(() => literal)` and a `catch` block that only returns a literal.
- **A ref-in-render rule must count writes inside memo and state initializers,** and must skip the lazy-init pattern (`if (ref.current === null) ref.current = …`).
- **A linter that gives up inside `try` can hide a finding, not fix it.** Oxlint's React rules skip code reachable from a `try` block, so nesting the body in an arrow inside `try` only moves the hit out of sight. Start the work before the `try` and await inside it.
- **Tell the dependency linter that a latest-value hook's result is stable** (in Biome, `useExhaustiveDependencies` with `hooks: [{ name, stableResult: true }]`). Then take those refs out of dependency arrays.

## Failure behavior
- **Surfacing failures needs a product decision** when a component has nowhere to show one. Ask the user once and offer a shared toast. Then check every migrated site that set a busy or saving flag before its action: the error path must clear it, or the control stays disabled.

## Boundary parsing
- **A schema must accept everything a real caller sends.** Read every call site. The type checker checks callers against the schema's input type, so run it for every lane.
- **A tuple schema rejects extra arguments.** An action wired straight to an event handler receives the event object as its first argument, so leave that action alone.
- **With `exactOptionalPropertyTypes`,** zod's optional output needs `| undefined` on the interface's optional fields. Widen the one type; do not cast.
- **A body that spreads or stores its whole input** needs `.passthrough()`, unless every caller builds the input as a typed literal.
- **When the handler is a wrapped const, the guard gate can no longer follow calls into helpers.** Put the guard in the handler itself.
- **Next rejects a sync function inside an exported initializer of a `"use server"` file** ("Server Actions must be async functions"), for example a zod `.transform` callback written inline in `export const x = serverAction(...)`. Types, lint and tests pass, and only a Next compile fails. Hoist the schema to a module-level const, and extend the use-server export rule to count this.

## Build cache
- **A shared config that the task runner does not hash replays stale results.** turbo reused cached typecheck output after `tsconfig.base.json` changed, because the root file was not an input. List root configs as global dependencies before trusting a cached gate.
- **A type-aware "unnecessary conversion" rule trusts types that the code never checked.** `String(row.date)` may be converting a `Date` the driver returned for a column typed `string`. Remove a conversion only for a value produced in-process; leave boundary values for the parsing wave.

## File length
- **A migration can push a file past its line limit.** Split the file first, as a pure move in its own commit, then migrate. A small local helper rarely saves enough lines.

## Parity
- **Run a new tooling script end to end before trusting it.** `node --check` and unit tests on its pure module missed an import that a refactor dropped; only a real run threw.
- **Both sides run the same recipes.** A verify skill copied into the base checkout goes stale and silently skips new features; drive the base app with the work branch's driver.
- **A difference that reproduces in two lockstep passes is code, not drift, unless each side also disagrees with itself across the passes** (see the self-disagreement check below). Trace it to the commit that caused it before you accept or reject it.
- **Every leg needs a freshly launched app.** When the pre-change base cannot serve moved URLs, run it in legacy mode.
- **Nothing may write the shared database during a run.** A world guard enforces this. Run member or role checks, and any saves, only between runs.
- **A diff in one UPC or row that both base runs agree on is not proof of a bug.** Compare each checkout's on-disk data cache for that key. A different snapshot time is data drift. Record the evidence.
- **One errored recipe while the machine is under heavy load:** re-run that recipe alone on a fresh app before calling it a failure.
- **A path list is data, not a shell word list.** zsh does not split `$VAR`, so `for f in $LIST` sees one long path, and a formatter or commit run on it silently does nothing. Build lists from `git status --porcelain | cut -c4-` or a file, and pass them through `tr '\n' '\0' | xargs -0`.
- **Bracketed route folders are globs to some tools.** oxfmt reads `[scope]` as a character class and skips the whole run without an error. Escape the bracket (`[[]scope]`) or run the formatter's `--check` over the whole tree before committing.
- **Before calling a parity difference code, check whether each side disagrees with itself.** If the base app's pass 1 and pass 2 differ the same way (same cells, different order), the cause is the data source, for example a query with no `ORDER BY` feeding a stable sort with ties. Record it as drift with that evidence, and propose the deterministic tiebreak as its own behavior change.
- **Lint rules that need a new effect hook collide with an effect-count gate.** Decide where paved effect hooks may live (an exemption list in the gate, each hook with its own test) before briefing lanes that would need them, or split the wave so the first half needs no new effect.
- **A paved hook that wraps a banned call is a loophole unless the rule limits it.** Before moving sites behind it, class each one (belongs in an event handler, belongs in render, or real external sync), and write the allowed class into the rule's fix text. Read the code before reclassing: an effect that tells an imperative library (AG Grid) to re-read committed state is external sync, and moving it into the handler can read a value that has not committed yet.

## Grids and two-phase effects
- **AG Grid's `context` option is `@initial`.** A context memo whose dependencies change after mount is ignored, so cells keep the first closures. Build it once and have every member forward to the newest value through a latest-value ref.
- **Immutable `rowData` with `getRowId` refreshes a cell only when its own value changes.** A renderer that reads other fields of the row keeps stale content after an in-place update. When replacing a manual remove-and-add transaction path, redraw exactly the replaced rows after the grid applies the new `rowData`. Measure the edit both ways before deleting a performance path.
- **Moving the first phase of a two-phase effect into render removes the second phase's trigger.** If the second phase needs an imperative API (a grid ready callback), put that readiness in its trigger. Drive the deep link cold on the running app.
- **Parity only covers what its recipes open.** A deep link (`?focus=`), an edit flow or a save path is invisible to read-only parity; add a recipe the first time a regression slips past, and expect the base branch to show its own latent bugs there.
- **Live data checks must use the code's full union.** A hand-copied list that misses one value reports a false alarm; derive the list from the source file.

## Effect waves
- **Count `yield*` against the old `await`s.** A missing `yield*` builds an Effect and drops it, so the call silently never runs. The language-service gate must be at error before the first caller wave, and the reviewer checks each converted body against HEAD.
- **Every `Effect.all` and `Effect.forEach` states its concurrency,** and it matches the legacy code. A `Promise.all` that became sequential is a timing change; one that now interrupts started writes on first failure is a behavior change.
- **Read what reaches the user on failure.** `Effect.tryPromise` wraps the cause; the edge adapter must still produce the old message and status. Drive one error path per wave.
- **A redirect or not-found inside an Effect is a defect** unless the edge adapter rethrows it. Drive one.
- **Pure code wrapped in Effect is a finding,** not progress. Revert it.
- **A service method without `Effect.fn("Service.method")`** has no span; the tracing story depends on every one.
- **A version bump of `effect` or any `@effect/*` package is its own unit,** with parity, because several modules are marked unstable.

## Landing
- **Push every wave.** One program reached its goal with 225 unpushed commits and 1,450 files, and no gate had run on a push of any of them. On one branch, merge the base and push at every wave boundary, so the pre-push gate runs on each push, and open the program PR after Phase 1.
- **Never rewrite the program branch.** A rebase or squash voids every ledger verdict and the per-unit bisect story. Fix a pushed commit with a new commit, and take the base in with a merge.
- **A trailer must sit in the last paragraph.** The commit helper once wrote `Unit:` in its own paragraph above the attribution line, so `git log --format=%(trailers)` saw no unit and the wave table put every commit under "no Unit trailer". Keep `Unit:` and the attribution in one block.
- **Check open PRs on the base that touch files the program moved.** Whichever lands second reconciles; name the overlap to the user before it bites.
- **Pushes can cost money.** Preview builds are billed on some hosts. Batch verified work so each push earns its build.
- **Background fetches belong in route handlers, not server actions.** A server action joins the framework's router action queue, so a slow one delays navigation; a route handler fetched with an `AbortSignal` stays out of it and cancels on unmount.

## Trust and enforcement
- **A lane's count of its own tests can be wrong.** Count them yourself (`grep -c '^test('`) before quoting a number.

## Learned on the design-audit program (2026-10-03)
- **Typecheck and tests do not see the client bundle.** A shared module imported `schema` from the DB package and a `"use client"` component imported it; every gate passed and the page returned 500 in the running app. Gate it: walk the value imports of every client file and fail on a server leaf (DB package, cloud SDKs, `server-only`, Node built-ins).
- **Parse stored data strictly only after reading it.** Before a new parser, key or schema rejects a stored value, query the hosted databases read-only for the shapes and nulls it will meet. A column named `arrival_month` held `YYYY-MM-DD` in every one of 901 production rows.
- **One parity run per base checkout.** Two runs on one base restart each other's app (`launch --fresh`) and report the collision as changes, always on the base side. Give each concurrent run its own base worktree, and make the tool hold a lock.
- **A waiter that greps the process list can match itself.** Put queue logic in a script file and wait on a lock or a known PID, never on `pgrep -f` of a string that appears in your own command.
- **A worker's "no behavior change" for a route move needs a side-by-side run.** Load the old and new handlers in one harness and compare status, body and headers per route; it found 2 of 26 that could not be compared and named them.
- **A workaround in a test seam is fine when the lint bans mocks;** test the pure core the hook or route wraps, and say which wiring stays unproven.

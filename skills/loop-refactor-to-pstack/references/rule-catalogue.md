# Rule catalogue

These rules and paved helpers held up in a Next.js, TypeScript and AG Grid monorepo that reached zero baselines. Use the list as a menu: keep a rule only when a census of the target codebase shows the misuse. Each rule pairs with one paved helper, and its fix text names that helper. A rule with no paved path just makes agents invent workarounds.

## Linter configuration (Oxlint, type-aware)

- **Categories:** correctness, suspicious and perf, all at error level.
- **Plugins:** typescript, react, react-perf, nextjs, jsx-a11y, import, promise, unicorn, vitest, node and oxc.
- **Type-aware rules** that catch agent slop:
  - `no-floating-promises`;
  - `no-unsafe-type-assertion`;
  - `no-base-to-string`, which catches `[object Object]` in strings;
  - `switch-exhaustiveness-check`;
  - `no-unnecessary-type-assertion`;
  - `unbound-method`.
- **React compiler rules:** set-state in an effect, refs read in render, purity, immutability, memo dependencies, and nested components.
- **Test shape:** no disabled or focused tests, no snapshots, `expect` required, and `vi.mock` and timer faking banned through `no-restricted-vi-methods`. A test that needs a mock needs a seam instead.
- **Strict TypeScript:** `strict`, `noUncheckedIndexedAccess` and `exactOptionalPropertyTypes`.

## AST rules (`check-rules.mjs`: one counter each, with fixture tests)

| Rule | Catches | Paved path |
|---|---|---|
| `use-effect` | Raw `useEffect` and `useLayoutEffect` | Derive in render, or do the work in the handler. External sync only goes through `useEffectOnChange` or `useLayoutEffectOnChange`, `useWindowEvent`/`useDocumentEvent`, `useRunNowAndEvery`, or `usePollWhileVisible`. Prop-reset state uses `useSyncedState`; a latest value a callback reads uses `useLatest`. Only the hook files on the policy's owner list may call the raw hook. |
| `effect-cleanup` | A listener, timer or observer started without a matching cleanup | Return the cleanup, or pass `{ once: true }` or a signal |
| `ref-write-in-render` | `ref.current =` during render, including inside memo or state initialisers | `useLatest`. The lazy-init pattern is exempt. |
| `swallowed-error` | An empty `catch`, a catch that only returns a literal, and `.catch(() => literal)` | `bestEffort(label, work, fallback)`, `bestEffortSync` and `handledWhenAwaited`. They log and keep the fallback, and they handle thenables. |
| `transition-uncaught` | An async action inside `startTransition` with no catch | `runAction(action, { onError })`, which rethrows the framework's redirect and not-found |
| `control-flow-in-try` | `redirect` or `notFound` inside a try that swallows them | Move the call out, or rethrow |
| `server-action-input` | A server action that trusts its TypeScript parameter types | `serverAction(z.tuple([...]), handler)` |
| `route-body-input` | `req.json()` trusted as typed | `parseBody(schema, req)`, which returns a 400 |
| `use-server-sync-export` | A sync export, or an inline zod `.transform`, in a `"use server"` file. Types and tests pass, and only a Next compile fails. | Hoist the code to a module-level const or a sibling module |
| `misplaced-directive` | `"use client"` not on the first line, which makes it an ordinary expression | First line, before any import |
| `inline-import` | `import()` in function bodies and type positions | A static import at the top |
| `client-server-env` | A non-public `process.env` read in a client file | `NEXT_PUBLIC_*` only |
| `raw-date` | `split("-")` and `slice(0, 7)` on date strings | A dates module (`toDay`, `monthOf`, `addDays`, `utcDay`) |
| `page-path-literal` | A hard-coded page URL | `PAGES[id].path` from the one routes registry |
| `open-redirect` | A redirect target built from a query parameter | A literal app path |
| `grid-row-id` | An AG Grid with no `getRowId` | A stable business key, or a deterministic composite built where the rows are made. Never an array index. |
| `grid-hex-color` | A fixed hex colour in a cell style, which breaks dark mode | A Tailwind class with a `dark:` variant, or an rgba tint |
| `grid-conditional-prop` | A grid prop that changes after mount (many AG Grid options are `@initial`) | `api.setGridOption` from the event, or a `key` that remounts the grid |
| `grid-tooltip-newline`, `grid-click-range-gate` | Library traps this codebase hit | A tooltip component; a mouse-travel click test |
| `migration-sequence` | An edited, reordered or renumbered migration | Append only |
| `banned-path`, `route-loading-file` | Surfaces deliberately removed | Delete them |
| `suppression` | Any lint-disable or `@ts-expect-error` | Fix the code. A library limit goes in `library-limits.json` with its count and reason. |
| `test-file-name` | A test the runner's include list never picks up | Rename it to match |
| `drizzle-array-any`, `suiteql-from` | Data-layer traps specific to the stack | The documented query form |

## Effect rules

When the program adopts Effect, the server-side rows above point at Effect instead of a hand-written helper: `swallowed-error` at the best-effort pipeline, `server-action-input` at the action adapter, `route-body-input` at the route adapter, the sequential-loop and deadline helpers at `Effect.forEach` and `Effect.timeout`, and module mocks at test layers. Client-only rows (`use-effect`, `transition-uncaught`, the grid rules) keep their React helpers. The Effect gates (`effect-adoption`, `effect-run-outside-edge`, `effect-explicit-concurrency`, `throw-in-effect`, `process-env-outside-config`, the language-service diagnostics) and the legacy-to-Effect mapping are in `references/effect.md`. A helper an Effect wave replaces is deleted in that wave, and its name goes on the banned list.

## Other gates

- **Guards** (`check-guards.mjs`): every server action and route handler reaches an authorization call before its first await. Throwing guards and checked guards are listed in gate policy. Public entry points are listed with a reason, and the ratchet makes that list shrink-only.
- **Stored data:** a value read back from the database and narrowed to a union or shape goes through `storedOneOf` or `storedJson`. These throw an error naming the table, column and value. Run the same checks as read-only SQL against production and staging first, and never copy the returned values into code.
- **Comments**, **file length**, **feature maps**, **doc references** and **skill links**: one small script each (`assets/node-gates/`).

## Patterns that make rules land cleanly

- Seed a rule only after two reviews hunt for false negatives. Tightening it after seeding raises the baseline.
- Each counter has fixtures for what it must flag and what it must not, each seen failing under a mutation of the counter.
- A paved hook's owner file is exempt from its own rule through the gate-policy list, so the ratchet sees any new exemption.
- When a lint rule and an effect-count gate collide, decide where the paved hooks live before briefing the lanes.

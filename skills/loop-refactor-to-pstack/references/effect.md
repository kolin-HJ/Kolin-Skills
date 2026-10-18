# Effect, fully

The program moves every effectful path onto [Effect](https://github.com/Effect-TS/effect) while users see no change. Effect becomes the paved path most rules point to: typed errors replace swallowed ones, Schema replaces hand parsers, layers replace module singletons and mocks, schedules replace hand-rolled retry and deadline helpers. Each legacy helper is deleted in the wave that migrates its last caller (principle-migrate-callers-then-delete-legacy-apis).

Written against `effect@4.0.0` (released 2026-09-30, LTS to at least 2029), verified from its npm tarball on 2026-10-01. Check `npm view effect dist-tags` at program start. If the API moved, `node_modules/effect/AGENTS.md` and `node_modules/effect/ai-docs/` are the truth, not this file. Every Effect brief tells the worker to read them, and to read `MIGRATION.md` at the root of the Effect repo before touching any v3 code.

## What "fully" means

| Code | Becomes |
|---|---|
| I/O, env, time, randomness, logging on the server and in shared packages | Effect: a service method or a program built from services |
| Pure domain logic (planning math, formatters, reducers) | Stays a plain function. Wrapping it in Effect adds reader load and nothing else (principle-laziness-protocol). |
| Framework entry points (server actions, route handlers, pages, cron) | One paved edge adapter each, the only code that runs an Effect |
| Client components | React keeps its own model. Schema may be shared with the client; services and the runtime never are. This is the default for the user decision in `user-decisions.md`. |
| Tests of effectful code | `@effect/vitest` with test layers. No module mocking, no fake timers. |

## Version and packages

- Target 4.x. `@effect/schema`, `@effect/platform` and `@effect/sql` are merged into `effect` (`effect/schema`, `effect/http`, `effect/sql`). Every `@effect/*` package shares the core's version.
- Pin exact versions. The ratchet treats an Effect bump as its own unit, because `effect/sql`, `effect/schema`, `effect/http` and `effect/http-api` are marked unstable and may break in a minor.
- Requires TypeScript 5.9 or newer with `strict`.
- Old names that must not appear (the language service's `outdatedApi` flags them): `Context.Tag`, `Effect.Tag`, `Effect.Service`, accessors, `Either`, `catchAll`, `catchAllCause`, `Runtime<R>`. The 4.x forms are `Context.Service<Self, Shape>()("id")` with explicit `layer` and `layerTest` statics, `Result`, `Effect.catch`, `Effect.catchCause`.

## Phase order

Run after the foundation and the verification skill exist, so parity can prove every Effect wave. Each step is its own unit or wave.

1. **Census** (`how`, then `swarm` by area, read-only). List every module that does I/O, reads env, reads the clock, retries, races a deadline, swallows or rethrows, or mocks in tests. Class each as boundary, service, orchestration, or pure. The census seeds the `effect-adoption` baseline (below).
2. **Design** (`architect`, which runs `arena`, then `interrogate`). Prototype two or three shapes for the edge adapters and one real service on the running app (principle-exhaust-the-design-space). Decide the service graph, the error model and how each tagged error reaches the user. Record it in an ADR. This is a one-way door; it gets the full panel.
3. **Foundation unit.** Install the pinned packages. Add the language-service gate. Write the runtime module, the edge adapters, the `Config` layer for env, the logger layer that keeps today's log output, and their tests. No caller moves yet.
4. **Pilot.** One read path end to end, from page to service to data, with parity showing zero change and timings within noise. Fix the brief and the codemod from what the pilot teaches before any fan-out (Orchestrate, Pilot).
5. **Services.** One service per external system, each wrapping the existing client with `Effect.tryPromise` and a tagged error. Keep the driver: swapping it is a separate decision (see Data access).
6. **Callers, folder by folder.** A codemod does the mechanical part (principle-build-the-lever); lanes take only the sites it reports. Each wave deletes the legacy helpers its last caller leaves.
7. **Boundaries.** Hand parsers and zod schemas become Schema. Delete zod with its last import.
8. **Tests.** Module mocks become test layers; fake timers become `TestClock`.
9. **Retire.** The adoption baseline reaches zero and is deleted, every language-service diagnostic runs at error, and each deleted helper's name joins the banned names in gate policy.

## The paved modules

Names are examples; keep the repo's conventions. Every module below is on a gate-policy owner list, so the ratchet sees a new exemption.

| Module | Owns | Rule that bans the raw form |
|---|---|---|
| `lib/effect/runtime.ts` | The one `ManagedRuntime.make(AppLayer, { memoMap })`, with a shared `Layer.makeMemoMapUnsafe()` memo map so dev reloads do not rebuild layers. The only caller of `run*`. | `effect-run-outside-edge` |
| `lib/effect/action.ts` | `effectAction(schema, guard, program)`: decode input with Schema, authorize before any write, run, map each tagged error to the action's plain result type through an exhaustive `_tag` switch, rethrow framework control flow | `server-action-input`, `effect-run-outside-edge` |
| `lib/effect/route.ts` | Route handlers: decode the body with Schema (a decode failure is a 400), authorize, run, map errors to status codes. `effect/http/HttpEffect` has `toWebHandler` adapters for `Request` to `Response` if the design picks them. | `route-body-input` |
| `lib/effect/page.ts` | Server component loaders: run, map a not-found error to the framework's not-found | `effect-run-outside-edge` |
| One service per system | `class Db extends Context.Service<Db, {...}>()("app/Db")` with `static layer` and `static layerTest`. Each method is `Effect.fn("Db.method")`, so it is traced. | `async-in-server-scope` |
| `Config` layer | Every env read, parsed once | `process-env-outside-config` |
| Errors | `Schema.TaggedError` per expected failure; bugs stay defects | `throw-in-effect` |

## Legacy to Effect

Behavior must match what the legacy form did. The right column is where parity has caught or will catch a difference.

| Legacy | Effect | Keep identical |
|---|---|---|
| `Promise.all(xs.map(f))` | `Effect.forEach(xs, f, { concurrency: "unbounded" })` | Parallelism; and failure: `Promise.all` lets started work finish, while Effect interrupts it. For writes, use `Effect.all(xs.map(f), { concurrency: "unbounded", mode: "result" })` (`forEach` has no `mode`) or make the steps uninterruptible. |
| A sequential loop helper | `Effect.forEach(xs, f, { concurrency: 1 })` | Order of writes |
| A retry helper | `Effect.retry(effect, schedule)` | The same attempts, delays and retryable condition. A create that must not retry on 5xx keeps that rule in `Schedule.while`. |
| A deadline race | `Effect.timeout` or `Effect.timeoutOrElse` | The same deadline and the same fallback or error |
| A best-effort wrapper | `effect.pipe(Effect.tapCause(Effect.logWarning), Effect.catch(() => Effect.succeed(fallback)))`, in one paved helper | The same log label and fallback; defects stay loud unless the old helper also swallowed them |
| `try { … } catch { throw new X }` | `Effect.tryPromise({ try, catch: (cause) => new XError({ cause }) })` | The message and status the user sees |
| `zod.parse` | `Schema.decodeUnknownEffect(S)` | Accepted inputs: read every caller before changing a schema |
| Pagination loop | `Stream.paginate` | Page size and stop condition |
| `vi.mock` | `Service.layerTest` with `it.effect` or `layer(...)` from `@effect/vitest` | What the test asserts |
| Fake timers | `TestClock.adjust` | The same elapsed times |
| A module-level client | A service and its `layer` | One instance per process |

## Data access

`@effect/sql-drizzle` is v3 only. Drizzle's own `drizzle-orm/effect-postgres` needs `drizzle-orm` 1.0 (a release candidate on 2026-10-01). `@effect/sql-pg` 4.x uses its own protocol client, cannot wrap an existing pool, and returns timestamps as `Date`. So the default is a `Db` service that wraps the existing ORM and driver with `Effect.tryPromise`. Moving to an Effect-native driver is a separate, user-approved decision with its own parity, because it changes driver behavior. Supabase-style poolers need `prepare: false` either way.

## Traps parity must cover

- **Concurrency is explicit.** Pass `concurrency` on every `Effect.all` and `Effect.forEach`; a rule enforces it, so a converted `Promise.all` cannot quietly serialize.
- **A dropped `yield*` is a silent no-op.** An Effect value does nothing until run. The language service's `floatingEffect` and `missingStarInYieldEffectGen` catch it; that gate must be at error before the first caller wave.
- **Framework control flow.** A `redirect` or `notFound` thrown inside an Effect becomes a defect. The edge adapter runs with an `Exit`, finds the framework error in the cause and rethrows it. A test and a driven redirect prove it.
- **The server action boundary serializes.** Tagged error instances do not survive it. The adapter maps them to the plain result type the client already reads.
- **Interruption.** A cancelled request now interrupts its program. A write that used to finish after the client left must stay inside a transaction or be marked uninterruptible.
- **Error messages.** Wrapping changes what reaches the user. Parity needs at least one recipe per error path a planner can reach.
- **Dev reloads.** A module-level runtime is rebuilt on reload. Use the shared memo map, and prove on the dev server that each layer builds once.
- **Bundles.** Every service module imports `server-only`. Compare the client bundle before and after the foundation unit.
- **Overhead.** Time the pilot page before and after with the perf harness (median of N). A cost past noise stops the fan-out.
- **Assertions.** `@effect/vitest` examples use `assert.*`. Decide in the foundation unit whether the test-shape rule accepts `assert.*` or tests use `expect` inside `it.effect`, and encode the choice in the rule.
- **Suppressions.** Language-service overrides are comments (`@effect-diagnostics`), which the no-comments gate rejects. Severity lives in the tsconfig plugin options, which the ratchet watches.

## Gates

| Gate | What it does |
|---|---|
| `effect-language-service diagnostics --project tsconfig.json` in the check command (`@effect/language-service`) | Every documented diagnostic at error, plus the off-by-default ones that fit server scope: `asyncFunction`, `newPromise`, `processEnv`, `globalConsole`, `globalFetch`, `preferSchemaOverJson`, `unsafeEffectTypeAssertion`. Each starts with a baseline and an owner wave, or at zero. Before trusting it, plant a floating Effect and confirm the command exits non-zero; if it only prints, wrap it in a gate script that counts its error lines. |
| `@effect/tsgo`'s Oxlint plugin (`effecttsgo/*`) | An option when the repo's Oxlint and tsgolint versions sit inside its supported window. Check the window when adopting; adding it is a new tool, so ask. |
| `effect-adoption` (rules engine) | Per file: async functions, `new Promise`, `.then` and raw `try` in server scope outside the edge adapters. Seeded from the census, target 0. |
| `effect-run-outside-edge` | `Effect.run*` or `ManagedRuntime` outside the runtime owner list |
| `effect-explicit-concurrency` | `Effect.all` or `Effect.forEach` without `concurrency` |
| `throw-in-effect` | `throw` inside `Effect.gen` or `Effect.fn` |
| `process-env-outside-config` | `process.env` outside the `Config` layer and the client-safe public keys |
| Banned names | Each deleted legacy helper, so it cannot come back |
| Ratchet | The exact `effect` and `@effect/*` versions, the tsconfig `plugins` entry and its diagnostic severities, and the owner lists above |

## Lessons from the first program (hj-supply-chain, 2026-10-04)

- `effect` 4.0.0 is the release; `@effect/vitest` 4.0.1 declares `effect ^4.0.1`, which does not exist, so pin `@effect/vitest@4.0.0`. It needs vitest 5, which needs Node 22.12 or newer. Bump vitest first, as its own unit, and match CI to the host's Node.
- Vite 8 (vitest 5) honours tsconfig `"jsx": "preserve"`; set `oxc: { jsx: { runtime: "automatic" } }` in the vitest config.
- Request context leaks between requests inside fibers. Measured: after a shared `Effect.cached` or `Deferred` wakes a fiber, `AsyncLocalStorage` reads return the request that completed it, and a legacy access check ran as the other user. A per-request scheduler does not fix it. Capture `AsyncLocalStorage.snapshot()` at the edge and run every call into unconverted code through it (`legacy(f)`). Prove it with a two-request test that fails without the snapshot.
- Gate the Next request APIs by reference, not by import or by "inside a generator": `Effect.sync(() => cookies())` and an aliased `revalidateTag` both escape a generator-only rule. Allow a reference only inside a function passed to `legacy(...)`, and move plain helpers that use those APIs out of Effect modules.
- The dead-code gate fails a foundation with no callers. Land each foundation export with its first caller; add an adapter in the wave that first uses it.
- `effect-language-service diagnostics --project` exits 1 on error severity; run it per workspace through turbo so unchanged inputs are cached (about 100 s cold on 1,000 files). `deterministicKeys` dictates service ids such as `@hj/db/database`. `strictEffectProvide` rejects `Effect.provide` in tests: use `@effect/vitest`'s `layer(...)` in a file that does not also import `it`.
- `Schema.Defect` is a function in 4.x (`Schema.Defect()`). `DateTime.formatIso` equals `toISOString()`.
- A logger that binds `console.log` at module load cannot be observed by a test spy; resolve the console method per call.
- Oxlint's vitest rules need `additionalTestBlockFunctions: ["it.effect", "it.live", "it.scoped"]` on `expect-expect` and `no-standalone-expect`.
- Export the database service from a subpath (`@hj/db/database`), not the package barrel, or every route that imports the barrel loads `effect`.
- A typed-failure-free input record (`Record<string, Effect<unknown>>`) keeps a race helper honest without casts; let library failures be defects there and unwrap them at the edge.

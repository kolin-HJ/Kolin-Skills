# Calls the user owns

Every one of these came up mid-program before. Ask the ones that apply in the first batched question, put the recommended option first, and record each answer as a standing order. The rest go in `RESUME.md` under "needs the user", with a note on when each will matter.

## Setup (ask before the first iteration)

| Call | Recommended | Why it matters |
|---|---|---|
| Where the work lives | One program worktree and branch cut from the base branch, for the whole program | Other sessions share the main checkout, and the program lands as one PR |
| Commit approval | One commit per verified unit, pushed to the program branch (policy, Approvals); no merge or deploy without a fresh yes | Units stay small and revertable |
| Systems never written | Production, external services, shared databases and chat; local writes only if restored | Parity needs a still world |
| Live data reads | Read-only queries against production and staging when a check needs real values, with nothing stored in code, briefs or reports | Stored-data rules need proof that no real row breaks them |
| Parity bar | "Behaves exactly like the base branch"; each intended change named and approved | This is the definition of done |
| Compile check | A parity app launch, or a production build | One user skipped the build because parity already launches the app |
| Models per role | Opus plans and reviews in a fresh read-only thread; Sonnet 5.5 at medium builds; Haiku does mechanical sweeps. Pinned in the agent definitions and checked by `assets/check-subagents.sh` | The reviewer must not share the builder's context, and briefs are written for the builder's tier (`references/subagents.md`) |
| Decisions toward the goal | "I approve reversible decisions that serve the goal" | Stops a question every hour. It never covers a merge, a deploy or a push to a protected branch. |
| The lens for every choice | Agent-first: pick the option an unsupervised agent gets right on the first try, with code a person can still read | The goal is a codebase agents manage with no supervision |
| Effects library | None. Plain strict TypeScript: a `Result` union, tagged errors that carry a fix hint, one retry owner, one rate limiter per external connection, and dependencies passed as one typed argument | Every model writes this pattern correctly with no library to learn; adopt Effect (`references/effect.md`) only when the user asks for it |
| Where gates run | Locally: pre-commit, pre-push, and one `verify` command that writes an evidence file per SHA. Keep CI only where the repo already has it for free; never add paid CI. Agents never skip the local gate. The user's yes here covers writing the git hooks | Without CI, `references/trust-audit.md` Local enforcement is the whole defence, so every row there must hold |
| Out-of-scope code | Delete it, after a tag on the last commit that has it; never park it | One live example per side, and nothing dead for agents to copy |
| Runtime versions | One pinned runtime version (for example one Node LTS) in every repo, the box and the host | No "works on my Node" |
| Verifier seats | A fresh Claude subagent on a different model or lens per risky unit | A seat with the builder's model and context shares its blind spots |

## Landing (ask with the setup batch)

The program lands as one branch and one PR at the user's request. These calls shape how.

| Call | Recommended | Why it matters |
|---|---|---|
| Push cadence | Merge the base and push the program branch at every wave boundary | One earlier program held 225 commits unpushed to the end. Pushing each wave backs the work up and runs the pre-push gate on it |
| When the PR opens | Right after Phase 1, so the user sees the work at every push | A PR opened at the end hides weeks of unreviewed work |
| Merge style | A merge commit, never a squash | A squash turns hundreds of verified unit commits into one, and `git bisect` can no longer find the unit that broke something |
| Mid-program landing | Allowed at any wave boundary on the user's word; the branch then continues from the merged base | Agents on the base have none of the gates until the PR merges |
| Base drift | Merge the base into the branch at every wave boundary; never rebase | A rebase rewrites every pushed SHA, voids every ledger verdict and needs a force-push |

## Effect (ask only when the user chose Effect over plain TypeScript)

| Call | Recommended | Why it matters |
|---|---|---|
| Version | The current major (4.x on 2026-10-01), exact pins, bumps as their own units | 4.x merged schema, platform and sql into `effect`; several modules are marked unstable |
| Scope of "fully" | Every effectful server path and shared package; pure logic stays plain; client components keep React and share only Schema | Services and the runtime in client bundles cost size and buy nothing React lacks |
| Data driver | Wrap the existing ORM and driver in a `Db` service; an Effect-native driver is a later, separate decision | The native driver changes date handling and pooling; the drizzle bridge needs a 1.0 release candidate |
| Validation library | Schema replaces the current one, deleted with its last import | Two validators drift |
| Effect lint plugin | Adopt the language-service diagnostics CLI now; the `@effect/tsgo` Oxlint plugin only if the repo's Oxlint version is in its window | Both are new tools, so the user decides |
| Error surfacing | Each tagged error maps to the message and status the user sees today | Any other mapping is a behavior change to approve per error |

## Product calls (each surfaced only when its wave arrives)

| Call | Options seen | Default that worked |
|---|---|---|
| How failures surface once errors stop being swallowed | Shared toast, inline message, or log only | A shared toast. Every migrated site that set a busy flag must clear it on error. |
| Guard role model | Match the page's own access, or a stricter role per write | Match the page's access. Writes need the page's editor role; reads used by ungated pages need a signed-in user. |
| Stored values that may not fit the new union | Fail loudly, fall back, or migrate the data | Check the live database first, then fail loudly with table, column and value |
| Plain `<img>` | `next/image` with defaults, or `unoptimized` | `unoptimized`, which keeps the bytes and layout identical |
| Legacy URLs after a route move | Redirects, or none | Ask. One user said "don't do legacy redirects". |
| Deleting dead code paths, parked pages or tests | Delete, or keep behind a flag | Delete with the user's explicit yes. A harness may block test deletion until then. |
| Latent bugs parity uncovers on the base branch | Fix now, or record | Record each in a spec file; fix with approval and name it as a behavior change |

## Trust and landing (ask in phase 5)

| Call | Options | Note |
|---|---|---|
| Agent hook settings | Add them, or not | The permission check may refuse workers who write them, so the yes must come from the user |
| Rulesets: PRs on every long-lived branch, code-owner review, and a required status check only where free CI exists | An admin applies the prepared ruleset, or skip | Check the plan and the user's role with `gh api` first. A write-role user needs an admin. |
| Who owns gate changes (CODEOWNERS) | A named person, or none | Without one, an agent can approve the bypass label on its own gate change |
| New tools: secret scanning, mutation testing | Each as its own change, or none | Mutation testing turns "seen failing" into a gate; secret scanning catches keys before they burn |
| Landing the program PR | Merge now at a wave boundary, or hold to the end | Gates on an unmerged branch enforce nothing; say so in every update while holding |
| Secrets found in the tree | Rotate, then remove | Name the file, line and credential type, never the value |

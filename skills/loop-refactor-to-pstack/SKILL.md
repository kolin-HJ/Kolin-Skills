---
name: loop-refactor-to-pstack
description: "Run a long, multi-session program that refactors a whole repository to pstack standards and architecture on one branch, with Lauren Tan's (poteto's) method, and sets up the pstack workflow so later agents stay trustworthy: one instruction file routed through poteto-mode, one check command CI and the deploy run, strict gates at zero allowance, repeated mistakes made impossible with `correct`, a target module architecture enforced by gates, a verification skill with lockstep parity against the base branch, a verifier agent and PR proof check, a tamper-evident ratchet and agent guards. Errors and effects use plain strict TypeScript (foundation skill); Effect (Effect-TS) only when the user asks for it. It works in waves of codemods and delegated lanes, one verified commit per unit on a single program branch that lands as one PR, without changing what users see. Use it whenever the user wants to adopt pstack in a repo, refactor a codebase to pstack or poteto's practices or architecture, drive lint baselines to zero, make agents trustworthy in a codebase, set up the pstack workflow, adopt Effect when the user asks for it, or resume such a program after a compaction, even if they don't name the skill. Not for one bug fix or one feature; those use poteto-mode's playbooks."
---

# Loop: refactor a repo to pstack on one branch

poteto's trust model is the premise. You parallelize only as far as you can trust unattended work, and trust comes from the environment, not from watching each chat. The codebase is the agents' memory, and agents copy what they see. So every correction goes to the strongest layer that can hold it: architecture, then a type, then a gate, then prose. Review is last.

The whole program lives on **one branch** and lands as **one PR**. Each unit is one verified commit, so the PR reads commit by commit and `git bisect` finds a regression to its unit. The branch is pushed and kept mergeable at every wave boundary, so the user can land it at any boundary.

This is multi-day work. Write the resume note before anything that could end the session.

## How this skill uses pstack

This skill composes pstack and does not restate it. Each phase hands its method to the pstack skill that does that job best. This file adds only the program glue: the predicate, the order, the single-branch mechanics and the lessons from earlier runs.

| Job | pstack owner |
|---|---|
| The program (coordinator role, store, briefs, drains, ledger, liveness, escalation) | `poteto-mode/playbooks/orchestrate.md`, with its stack and frontier machinery replaced by the one branch (Single-branch mechanics) |
| Framing the predicate and rigor | `figure-it-out` Phase A |
| Each wave | `poteto-mode/playbooks/refactoring.md` |
| Reading a subsystem before touching it | `how`, fanned out with `swarm`; `why` before deleting anything whose reason is unclear |
| The target architecture | `architect` (it runs `arena`), screened against `architect/references/design-red-flags.md`, then `interrogate` |
| Turning repeated mistakes into checks | `correct` |
| The verification skill | `create-verification-skill`, kept honest with `maintain-verification-skill` |
| Mechanical change | `principle-build-the-lever`: a codemod first, lanes only for what it cannot do |
| Review | `no-comments`, then `deslop`, then the repo's reviewer, then `interrogate` and `blast-radius` by risk |
| The decision trail | `show-me-your-work` |
| Prose (ADRs, commit messages, the PR body) | `technical-writing`, then `unslop` |
| Pause, resume and close | `pause-safely.md`, `session-pickup.md` with `recall`, then `reflect` |

`references/pstack-map.md` lists where every playbook, skill and principle fires. Every pstack skill sets `disable-model-invocation`, so read its `SKILL.md` and follow it (`pstack-local/SKILL.md`, Loading a pstack skill). Read a principle's leaf before you cite it.

Read these before the first iteration:

- `~/.agents/skills/poteto-mode/SKILL.md` with its Principles index, and the playbooks `orchestrate.md`, `refactoring.md` and `autonomous-run.md`.
- `~/.agents/skills/pstack-local/SKILL.md` and its `models.md`.
- The repo's `AGENTS.md` (or `CLAUDE.md`) and the user's global instruction file.

The user's global file and the repo's file win over pstack, and the stricter of the two wins. Name the one you followed. The user's request for this program settles one conflict: the program lands as one branch and one PR. Say so once in the framing and once in the PR body. Every unit stays a small commit, so reviewability moves from PR size to commit size. The one branch replaces these pstack steps:

- `opening-a-pr.md` "prefer five narrow PRs": one program PR instead.
- `refactoring.md` step 8 "rebase into small ordered commits": one commit per unit, made in order and never rewritten.
- `orchestrate.md` step 2 `orch frontier set`, step 3's "stack entry" and "merge", step 6's stacker, and all of Stack safety: Single-branch mechanics instead. The first unit of each new unit shape is the pilot, and it lands as a commit on the branch.

## The goal predicate

Check every row at the end of each wave. Keep looping until all hold. Never relax a row to declare victory.

1. The repo's one check command exits 0 at the branch tip.
2. `gates:status` lists no baselines, so every gate runs with zero allowance.
3. The last full lockstep parity run against the current base shows only changes the user approved.
4. The target architecture in `.pstack/architecture.md` is reached. A gate enforces every boundary in its module map, and its red-flag census reads zero (`references/architecture.md`).
5. Every mistake class `correct` found has a row in the instruction file's rule table, and each row names the check that enforces it.
6. Only if the user chose Effect: adoption is complete: the `effect-adoption` baseline is deleted, every language-service diagnostic runs at error, and each legacy helper Effect replaced is deleted and banned. Skip this row by default.
7. The workflow is installed. Every row of `references/workflow-setup.md` holds, and the last `maintain-verification-skill` pass ended `clean`.
8. The trust audit (`references/trust-audit.md`) has no open row, or the user chose to leave a row open.
9. Every question in `gates.md` is answered or recorded as the user's decision.
10. The one PR is open into the base, CI is green at the branch tip (or, when the user chose local-only gates, the `verify` evidence file exists for the tip SHA) without the ratchet's bypass label, the base was merged in during the last wave, and the PR body carries the wave table. Merging it is the user's call.

## Phase 0: frame (once)

1. **Resume or start.** If a store or `RESUME.md` exists, run `session-pickup.md` with `recall` and continue from its resume point. Do not redo landed units.
2. **Observe before asking.** Read the CI and deploy workflows, the hosting setup, branch protection (`gh api repos/<o>/<r>/rulesets`, `gh api orgs/<o> -q .plan.name`), open PRs on the base branch, and the package manifests. A doc's claim about protection or plan can be stale.
3. **Census.** Run `how` over each area through `swarm`, read-only, one worker per area. Count what each gate would find, files over the line limit, pages with no feature map, the design red flags per module and, for Effect, every effectful module (`references/effect.md`, step 1). The census is the program's first measurement and goes in the store's `research/`.
4. **Frame** with `figure-it-out` Phase A: the predicate above as numbers the gates print, the scope in units and waves, and the rigor level. Then apply Orchestrate's Frame step. If one agent could finish inside the session's budget, collapse to Autonomous run and drop the store.
5. **Ask once.** Send one batched question with the recommended option first (`references/user-decisions.md`, Setup, Landing and Effect). Park the rest with `orch gate park`, so they do not arrive mid-wave. Record each answer as a numbered standing order. An approval covers only the action it names. "I approve all decisions toward the goal" covers reversible work, never a push, merge, deploy or external write.
6. **Cut the branch and open the PR.** Create the program worktree and branch from the base tip, and record both SHAs. All program work happens there. Commit the plan (step 7), then push and open the program PR on the user's yes. `orch ledger record` takes only a PR number, so until the PR exists, record each verdict in the trail and copy it to the ledger when the PR opens.
7. **Write the plan and glossary.** `.pstack/program.md` holds the predicate table, the wave order, the proof tiers and the calls with their defaults. `docs/GLOSSARY.md` holds one exact word per domain concept, each with the file or ADR that owns it, linked from the instruction file.
8. **Create the store** (`references/program-store.md`) and open the trail with `show-me-your-work` at `.pstack/decision-log.tsv`.
9. **Check the subagents.** Run `bash assets/check-subagents.sh [<repo implementer>]`. It must print `ok` for each definition (`references/subagents.md`).

## Phase 1: the workflow and the gates (once)

Build the environment before cleaning anything. Each item is its own verified commit on the branch.

1. **The workflow** per `references/workflow-setup.md`: one `AGENTS.md` that routes every task through poteto-mode, vendored pstack with its source pin and link check, the `.pstack/` folder, the PR template with its proof check, and the agent guard. The templates are in `assets/workflow/`.
2. **One check command** runs every gate. CI (or, with local-only gates, pre-push and `verify`) runs exactly that command, and so does the production deploy.
3. **Every gate the language supports, at strict settings.** Propose each new tool before you add it. The list is a formatter, a type-aware linter at error, strict types, and tests with test-shape rules. It also holds no comments, dead code with import boundaries, a file-length limit, an authorization guard gate with a reviewed public list, and a doc-reference gate.
4. **Gate policy as data.** Every threshold, scope and owner or exemption list lives in one JSON file, so the ratchet sees it.
5. **A baseline registry and its tools:** `baselines.json` with target 0 and an owner unit per baseline, plus `gates:files`, `gates:lower`, `gates:status` and the ratchet in CI. The contract is in `references/gates-contract.md`. JS and TS implementations with tests are in `assets/node-gates/`.
6. **Seed each gate at today's count, with an owner unit.** Nothing is baselined to avoid a fix.
7. **Push.** From here, CI runs every gate on every push of the branch. The ratchet counts each seeded baseline as growth, because the base has no such file. So the program PR carries the `allow-baseline-growth` label, with the reason in its body, until the last baseline is deleted. Then remove the label, and the ratchet must pass without it.

## Phase 2: the verification skill (once)

Run `create-verification-skill`. It must end with a CLI that launches the real app for any checkout, drives it and reads state back. It also needs one feature map per user-facing feature with a gate for unmapped pages, and lockstep pair parity against the base (`references/parity.md`, `assets/parity-pair/`), proven able to fail with a planted change. Add a world guard that fails a run if anything else writes the shared database. Add driven recipes for saves, deep links and error paths before a wave touches them. Then install the verifier agent from `assets/workflow/verifier.md`, pointed at the new skill.

## Phase 3: the target architecture (once, then extended per wave)

Follow `references/architecture.md`. Ground each subsystem with `how` and `why`, sketch the target module map with `architect`, screen it against the design red flags, and run `interrogate` on the synthesis. Record the result in `.pstack/architecture.md` and an ADR. Each boundary becomes a gate rule (an import boundary, a banned import or an owner list) seeded at today's count. Each red flag the census found becomes a baseline with its owner wave.

Plain TypeScript is the default (`foundation`, Guardrails). Only when the user chose Effect, the Effect service graph is part of this design. Follow `references/effect.md` steps 1 to 4 here: the census, the design with an ADR, the foundation unit, then a one-slice pilot proven by parity and timing. Nothing fans out until the pilot lands. The remaining Effect steps run as waves inside the loop.

## Phase 4: make the repeated mistakes impossible

Run `correct`. Feed its "find the mistake classes" step with evidence, not guesses:

- `trust`, with every follow-up chain classed by the layer that would have caught it.
- The user's repeated corrections from the session transcripts (`recall`, or the transcript folder in `pstack-local`), the user's own turns only.
- Read-only audits by area through `swarm`: framework misuse, types and boundaries, errors, UI and grids, data and dates, effects. Each returns counts, examples and a proposed fix level.
- `references/rule-catalogue.md` as the starting list. Keep only what this codebase shows.

`correct` picks the level. A class that lands as a rule lands as one unit, in this order:

1. The paved path (in an Effect repo, usually an Effect module), with tests that assert literals and were seen failing under a mutation.
2. The rule, with fixture tests and an error that names the paved path.
3. Two independent reviews that hunt false negatives.
4. The seeded baseline with its owner wave.

A paved hook that wraps a banned call is a loophole unless the rule's fix text limits what may go through it. Each class gets its row in the instruction file's rule table.

## The loop

Each wave takes the highest-leverage remaining baseline toward zero and runs `refactoring.md` over it. Order the waves this way:

1. Subtractions: dead code, shims, duplicate helpers.
2. Mechanical rules.
3. Architecture moves, and file splits that unblock later waves.
4. Effect service and caller waves.
5. Boundary parsing onto schemas.
6. UI and framework rules.
7. Failure-behavior changes, after the user's product call.

The steps of each wave:

1. **Plan.** Run `gates:status`, `orch status` and `orch inbox drain`. Run `how` over the subsystem. Pin the behavior contract, and name the data shape and the target shape (`refactoring.md` steps 1 to 3). A risky change to code with no test gets a characterization test first, as its own unit, seen red when the pinned behavior is broken.
2. **Lever.** Write the codemod for the mechanical part and prove it on hand-done sites (`references/brief-templates.md`, Codemod first). Run it yourself.
3. **Brief** the leftover sites as lanes with disjoint files, about 30 to 70 sites each, with the nine-field template. Add each unit with `orch unit add <id> --track <wave> --brief <path>`. The track is how the PR's wave table groups commits.
4. **Launch** a rolling window of lanes on `poteto-agent` or the repo's implementer, without a `model` argument, so the agent definition's pin applies (`references/subagents.md`). Refill as each lane finishes. Never launch blocking batches. Wait on a background command's completion, never a wakeup or sleep loop. Workers never commit, push or run the app.
5. **Drain** each completion as a queue event (`orch inbox push`). Accept a lane only against `references/review-checklist.md`. A report is a lead.
6. **Integrate.** Fix findings, delete re-export shims, re-key moved hits, and run `gates:lower`. Then run the check command, then the framework's compile through an app launch.
7. **Review the wave diff once,** in this order: `no-comments`, `deslop`, the repo's reviewer (`senior-reviewer`). Add `interrogate` and `blast-radius` by the proof tier below. Send the riskiest lane to a verifier on another model family when one is available, and record its verdict with `orch ledger record`.
8. **Prove** at the tier the change needs. A parity difference is code until two passes and each side's agreement with itself show otherwise. Fix each failure at the strongest layer (`principle-fix-root-causes`).
9. **Commit** one unit per lane plus an integration commit, with `assets/commit-unit.sh`. Each message says what changed for the user and the engineer, every behavior change, and what ran.
10. **Retire** each baseline that reached zero, with its registry entry and every doc that names it. Delete each legacy helper whose last caller moved, and ban its name.
11. **Close the wave** with the boundary steps in Single-branch mechanics: merge the base, rerun the check command and parity, push, regenerate the PR body.
12. **Record.** Write a trail row and the ledger verdict, then rewrite `RESUME.md`.

Every fifth wave, and after any wave that moved a page, run `maintain-verification-skill`. After a wave that took too long or needed two brief rewrites, run `reflect` and fold the lesson into `references/review-checklist.md` or a gate.

Record every site a lane leaves unchanged, with its reason and the wave that unblocks it. A plateau is not a stop, so pivot the approach. Two failed fixes on one gate call for `principle-attack-the-premise`.

### Proof tiers

| The unit changes | Proof before its commit |
|---|---|
| Docs, skills, gate code, scripts | The check command. A gate change also plants the loosening it blocks and shows the gate fail. |
| App code, behavior kept | The check command and `parity-pair --only` on the features the unit reaches. A unit that reaches every page (dates, a shared loader, the runtime) runs full parity. |
| A save, a deep link, an error path or an interaction | The above, and the feature map's driven recipe for it. |
| Numbers, schema, access rules, external writes, the runtime or the Effect foundation | The above, and `interrogate`. A shared helper also gets `blast-radius`. |

## Single-branch mechanics

- **One writer per file.** All lanes work in the program worktree with disjoint files (`principle-separate-before-serializing-shared-state`). Only the coordinator commits, merges and pushes.
- **Commits.** One unit per commit, each green on the check command when it was made. `commit-unit.sh` adds a `Unit:` trailer. `assets/wave-table.mjs` joins that trailer with `units.tsv` to group commits by wave.
- **Never rewrite pushed history.** Do not rebase, amend, squash or force-push the program branch. Fix a pushed commit with a new commit.
- **Merge the base at every wave boundary.** Fetch the base and merge it into the program branch, through the host's sync tool when it has one. Resolve conflicts in the merge commit. Then move the parity base checkout to the new base SHA (`references/parity.md`, Base drift), and rerun the check command and scoped parity. A base merge does not void unit verdicts. The boundary parity run after the merge is the verdict for the tip.
- **Push at every wave boundary** under the standing push approval. Without a standing approval, a push waits for a fresh yes.
- **Watch the base.** List open PRs on the base that touch files the program moved or will move. Whichever lands second reconciles, so name each overlap to the user before it bites.
- **Keep the PR landable.** At each boundary, CI is green, parity is clean and the PR body is current. Regenerate the wave table with `node ~/.agents/skills/loop-refactor-to-pstack/assets/wave-table.mjs --store <store> --base origin/<base>` and paste it into the body.
- **Ledger keys.** The PR is the one program PR number. The SHA is the unit's commit.
- **Landing.** The user merges, with a merge commit so the per-unit commits stay bisectable (`references/user-decisions.md`, Landing). If the user merges at a mid-program boundary, merge the new base into the branch and continue on it.

## Phase 5: trust (as baselines approach zero)

Zero baselines prove the code is clean today. Trust needs the gates to stay honest when an agent is under pressure to go green. Walk `references/trust-audit.md` row by row. Prove each block by planting the loosening and watching it fail.

1. **Tamper evidence.** The ratchet covers every gate setting, with one test per watched file kind and one where the PR edits the ratchet itself. CI runs it twice, with the PR's copy and with the base branch's copy.
2. **Local enforcement.** Add a pre-commit hook, a pre-push hook, a `prepare` script that installs them, and the agent guard. Get the user's explicit yes before you write hooks or agent settings. Never route around a refusal.
3. **Deploy gate.** The production deploy runs the full check command.
4. **Server side.** Prepare a ruleset per long-lived branch (PR required, CI required, code-owner review on gate machinery, no force-push or deletion) and the command that applies it. Applying it is the user's call. Without required review, the ratchet's bypass label is a speed bump. Say so plainly.
5. **Measure.** `trust` runs from the check tooling (`assets/node-gates/trust-curve.mjs`). Report the follow-up rate at close and after the PR merges.

## Phase 6: land and close

1. Merge the base a last time. Run the check command and full parity at the tip. Run the verifier agent over the whole branch range.
2. Write the PR body with `technical-writing` and `unslop`, in the repo's template. It holds the wave table, the behavior changes the user approved, the note on PR size, and one `Ran:` or `Not run:` line per check.
3. Get CI green at the branch tip. Fixes are new commits. Merging is the user's call. Until the PR merges, every update reminds the user that agents on the base branch have none of this work.
4. **Close.** Confirm every predicate row on the real artifact. Reconcile every unit to a terminal row. Audit the trail against the transcript with `show-me-your-work`, including its cross-model review. Run `reflect`, and fold every lesson that recurred into `references/review-checklist.md` or a gate asset of this skill. Then validate the skill: its frontmatter, its links, and `node --test` over every `*.test.mjs` under `assets/`.

## Asking and reporting

Ask only for product or preference calls and for approvals the standing orders do not cover. Batch them, recommend an option, and park each in `gates.md` with its default. Answer anything an experiment can answer by experiment (`prototype.md`). Surface a worker's permission refusal to the user verbatim, and do not do the refused action yourself.

After each wave, tell the user in a few plain sentences: what landed on the branch with commit ids, how each baseline moved (the `effect-adoption` total included), every behavior change, the parity result, the base merge, open trust rows, what is running and what needs them. Take the numbers from the tables, not from memory.

## Files in this skill

- `references/pstack-map.md`: where each pstack playbook, skill and principle fires.
- `references/architecture.md`: the target architecture phase, the red-flag census and the boundary gates.
- `references/workflow-setup.md`: the workflow a pstack repo ends with, and the template for each piece.
- `references/subagents.md`: which agent does which job, the model pin, panels, and briefs written for the pinned model.
- `references/effect.md` (only when the user chose Effect): the Effect target, phase order, paved modules, legacy mapping, traps and gates.
- `references/program-store.md`: the orch store, `RESUME.md` template, standing orders and commit helper.
- `references/user-decisions.md`: the calls the user owns, with recommended defaults.
- `references/brief-templates.md`: the nine-field brief, codemod first, and the common, lane, Effect, split and verifier briefs.
- `references/review-checklist.md`: the lessons that decide whether a lane's work is accepted.
- `references/gates-contract.md`: the registry, gate tools, gate policy and ratchet contract.
- `references/rule-catalogue.md`: the rules and paved helpers that earned their place.
- `references/trust-audit.md`: every known way to turn a red gate green, its block and its proof.
- `references/parity.md`: the parity method, its CLI contract, driven recipes and tradeoffs.
- `assets/commit-unit.sh`: the per-unit commit helper. It adds the `Unit:` trailer and marks the unit `committed`.
- `assets/wave-table.mjs`: prints the PR body's wave table from `units.tsv` and the branch's commits.
- `assets/check-subagents.sh`: checks each agent definition's model pin, and that `poteto-agent` loads poteto-mode.
- `assets/parity-pair/`: the lockstep pair runner, its verdict module and tests.
- `assets/bracket-parity.sh`: the slower three-run fallback.
- `assets/node-gates/`: the JS and TS reference gates, gate tools, ratchet and trust curve, with tests. Adapt the paths before use.
- `assets/workflow/`: the PR template, PR proof check and its workflow, the verifier agent and the skill sync script, taken from a repo that finished this program. Adapt the paths before use.

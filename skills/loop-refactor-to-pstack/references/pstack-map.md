# Where the loop uses each pstack skill and principle

The program applies all of pstack. This table says where each piece fires, so none is skipped by accident. Read a principle's leaf `SKILL.md` before citing it, and name in the commit or report only the ones that changed a choice.

Subagents that run any of these do so on Sonnet 5.5 through the pstack agent definitions (`references/subagents.md`). Paths are relative to `~/.agents/skills/` (`deslop`, `control-ui` and `control-cli` come from cursor-team-kit, linked there too). Every pstack skill sets `disable-model-invocation`, so read its `SKILL.md` and follow it (`pstack-local/SKILL.md`, Loading a pstack skill).

## Playbooks (`poteto-mode/playbooks/`)

| Playbook | Where it fires |
|---|---|
| `orchestrate.md` | The whole program: coordinator role, store, brief fields, drains, ledger, liveness, escalation. Its `frontier.json`, its stacker, the stack and merge parts of steps 2, 3 and 6, and its Stack safety section are replaced by the one program branch (SKILL.md, Single-branch mechanics). Collapse it when one agent can finish inside the budget. |
| `refactoring.md` | Every behavior-preserving wave: pin the contract, name the target shape, subtract first, migrate callers and delete, prove equivalence, check the reader-load delta. Step 8's rebase does not apply: one commit per unit, never rewritten. |
| `autonomous-run.md` | The wake mechanism between iterations, and its rule that a plateau is not a stop. |
| `prototype.md` | Any fork an experiment can settle: an Effect edge adapter shape, a codemod's output, a rule's false-positive rate. |
| `bug-fix.md` | A latent bug parity uncovers on the base branch, after the user approves fixing it. |
| `perf-issue.md`, `hillclimb.md` | A wave that measurably slows a page; prove the Effect runtime costs nothing measurable. |
| `authoring-a-skill.md`, `eval.md` | The verification skill, and any edit to this skill at close. |
| `opening-a-pr.md` | The one program PR: title, body sections and writing rules. Its "five narrow PRs" rule is overridden by the user's single-branch request. |
| `babysit.md` | Getting the one PR green when the user asks for a babysit pass. Merge stays with the user. |
| `shipping.md` | Not used: there is no stack to land bottom-up. |
| `pause-safely.md`, `session-pickup.md` | Before compaction or a stop, and on resume. |
| `worktree-cleanup.md` | Scratch checkouts the parity runs leave behind. |
| `investigation.md` | A read-only question mid-program: is a parity difference code or drift, why does a gate count move. |
| `feature.md` | A user-approved behavior change the program uncovers; it leaves the refactor wave and runs on its own. |
| `visual-parity.md` | A styling migration, or a parity difference that is pixels rather than values. |
| `runtime-forensics.md`, `trace-forensics.md` | A leak, a hang or a slowdown an Effect wave introduces, diagnosed before it is fixed. |
| `autopilot-stack.md`, `autopilot-full.md` | Not used. The program lands as one branch, and `autopilot-full.md` merges without the user's approval. |

## Skills

| Skill | Where it fires |
|---|---|
| `how` | The Phase 0 census and Phase 3 grounding, through `swarm`. Before each wave, over the subsystem it touches. |
| `why` | Phase 3, on any ownership or layering the map would change. Before deleting anything whose reason is unclear: a parked page, a strange guard, a retry policy. |
| `architect` (runs `arena`) | Phase 3's module map, screened against its `design-red-flags.md`. One-way doors: the Effect service graph, the edge adapters, the error model, the rule engine's shape. |
| `arena` | A contested decomposition of the program, or two codemod designs. |
| `swarm` | Read-only census and audit fan-outs, one worker per area, one aggregated report. |
| `interrogate` | The architecture map, and every unit in the top proof tier: numbers, schema, access rules, external writes, the runtime and the Effect foundation. One reviewer per model family (`pstack-local/models.md`). |
| `blast-radius` | A small-looking change to a shared helper, a gate or the runtime. |
| `tdd` | A fix with a cheap local test path. Every new test is seen failing first. |
| `no-comments` (Comment Sicko) | First in each wave's review; the comments gate holds the line after. |
| `unslop`, `technical-writing` | ADRs, briefs, commit messages, PR bodies, the user report. |
| `typescript-best-practices` | Every lane in a TypeScript repo: unions over optional bags, brands, schemas before guards, no `as`, exhaustive switches. |
| `correct` | Phase 4: finds the mistake classes, fixes each at the highest level, proves each check on a real past mistake, and keeps the rule table in `AGENTS.md`. Rerun it whenever the user corrects the program twice for the same thing. |
| `create-verification-skill` | Phase 2. |
| `maintain-verification-skill` | Every fifth wave, after a wave that moved a page, and at close (predicate row 7). |
| `show-me-your-work` | The decision trail, one row per decision, audited at close. |
| `figure-it-out` | Phase A frames the program's predicate and rigor. Also a sub-problem no playbook fits, such as a migration with no precedent. |
| `reflect` | At close, and after any wave that took too long: fold the lesson into this skill. |
| `recall` | On resume, alongside `RESUME.md`, and in Phase 4 to mine the user's repeated corrections. |
| `deslop` | Second in each wave's review, before the reviewer reads the diff. |
| `control-ui`, `control-cli` | Only when the repo has no verification skill yet; build one instead of scripting. |
| `setup-pstack` | Not used; `pstack-local/models.md` holds the model roles. |
| `teach`, `bro` | When the user asks to understand a wave or a decision in plain words. |
| `automate-me`, `make-bot-ui` | Not used by this program. |

## Principles (`principle-*/SKILL.md`)

| Principle | The choice it makes in this program |
|---|---|
| encode-lessons-in-structure | The second time a correction is needed, it becomes a type, a rule or a script, and the prose goes. |
| build-the-lever | A codemod does every mechanical wave; lanes handle only the sites it reports. |
| sequence-verifiable-units | One unit per commit, each green before the next; delivery order proves itself. |
| prove-it-works | Parity on the running app is the verdict, never a report or a green build. |
| test-behavior-not-implementation | Tests call the code as its caller does and assert literals. No `vi.mock`; a test layer is a seam. |
| type-system-discipline | Brands, unions, schemas at boundaries, typed errors in the error channel. |
| boundary-discipline | Parse and authorize at the edge; the core trusts its types and stays pure. |
| model-the-domain | Name the data shape before each wave and in the architecture map; a rule that needs an `if` per case has the wrong shape. |
| foundational-thinking | The workflow, gates, verification and the architecture map come before any cleanup. |
| subtract-before-you-add | Delete dead code, shims and duplicate validators before each reshape. |
| migrate-callers-then-delete-legacy-apis | A paved helper replaces the raw form and the raw form is deleted in the same wave. |
| outcome-oriented-execution | Converge on the Effect target; no compatibility layer outlives its wave. |
| laziness-protocol | The smallest diff that reaches the target; Effect wraps effects, never pure math. |
| minimize-reader-load | A wave that does not lower reader load somewhere is reverted. |
| redesign-from-first-principles | Design each service as if Effect had been there from day one. |
| make-operations-idempotent | Codemods, gate `--update`, store writes and resume steps converge on rerun. |
| separate-before-serializing-shared-state | Lanes own disjoint files; one writer per baseline file and per worktree; only the coordinator commits, merges and pushes the program branch. |
| guard-the-context-window | Bulk reads go to subagents; the coordinator keeps summaries and tables. |
| never-block-on-the-human | Reversible calls proceed and are logged; only irreversible ones wait. |
| fix-root-causes | A parity difference is traced to its commit before it is accepted or rejected. |
| attack-the-premise | Two failed fixes on one gate: census who holds the imbalance, then question the premise. |
| exhaust-the-design-space | The Effect edge adapter and service graph get two or three prototypes before the pilot. |
| experience-first | No planner-visible regression is traded for a cleaner diff. |

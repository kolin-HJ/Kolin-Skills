# Where the loop uses each pstack playbook and skill

This table says where each playbook and skill fires.

Paths are relative to `~/.agents/skills/` (`deslop`, `control-ui` and `control-cli` come from cursor-team-kit, linked there too).

## Playbooks (`poteto-mode/playbooks/`)

| Playbook | Where it fires |
|---|---|
| `orchestrate.md` | The whole program: orchestrator role, store, brief fields, drains, ledger, liveness, escalation. Collapse it when one agent can finish inside the budget. |
| `refactoring.md` | Every behavior-preserving wave: pin the contract, name the target shape, subtract first, migrate callers and delete, prove equivalence, check the reader-load delta. |
| `autonomous-run.md` | The wake mechanism between iterations, and its rule that a plateau is not a stop. |
| `prototype.md` | Any fork an experiment can settle: an Effect edge adapter shape, a codemod's output, a rule's false-positive rate. |
| `bug-fix.md` | A latent bug parity uncovers on the base branch, after the user approves fixing it. |
| `perf-issue.md`, `hillclimb.md` | A wave that measurably slows a page; prove the Effect runtime costs nothing measurable. |
| `authoring-a-skill.md`, `eval.md` | The verification skill, and any edit to this skill at close. |
| `opening-a-pr.md` | The one program PR: title, body sections and writing rules. |
| `babysit.md` | Getting the one PR green when the user asks for a babysit pass. Merge stays with the user. |
| `pause-safely.md`, `session-pickup.md` | Before compaction or a stop, and on resume. |
| `worktree-cleanup.md` | Scratch checkouts the parity runs leave behind. |
| `investigation.md` | A read-only question mid-program: is a parity difference code or drift, why does a gate count move. |
| `feature.md` | A user-approved behavior change the program uncovers; it leaves the refactor wave and runs on its own. |
| `visual-parity.md` | A styling migration, or a parity difference that is pixels rather than values. |
| `runtime-forensics.md`, `trace-forensics.md` | A leak, a hang or a slowdown an Effect wave introduces, diagnosed before it is fixed. |

## Skills

| Skill | Where it fires |
|---|---|
| `how` | The Phase 0 census and Phase 3 grounding, through `swarm`. Before each wave, over the subsystem it touches. |
| `why` | Phase 3, on any ownership or layering the map would change. Before deleting anything whose reason is unclear: a parked page, a strange guard, a retry policy. |
| `architect` (runs `arena`) | Phase 3's module map, screened against its `design-red-flags.md`. One-way doors: the Effect service graph, the edge adapters, the error model, the rule engine's shape. |
| `arena` | A contested decomposition of the program, or two codemod designs. |
| `swarm` | Read-only census and audit fan-outs, one worker per area, one aggregated report. |
| `interrogate` | The architecture map, and every unit in the top proof tier: numbers, schema, access rules, external writes, the runtime and the Effect foundation. Each seat upstream gives another model family is a fresh Claude subagent on a different model or lens (`references/subagents.md`, Panels). |
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
| `teach`, `bro` | When the user asks to understand a wave or a decision in plain words. |

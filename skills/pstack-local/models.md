# pstack model roles on this machine

Replaces `~/.cursor/rules/pstack-models.mdc`. Role labels match the ones pstack skills name. Claude is the only provider. Every role runs as a native Claude subagent through the Agent tool, and no other provider's CLI or API is called.

- `default`: a native subagent with no `model` passed. The Kolin-Skills hook `hooks/agent-default-model.py` sets Sonnet 5.5 on every Agent call with no `model` whose definition pins none: `general-purpose`, `Explore`, `claude-code-guide`, and any user or repo agent with no `model:` line that can edit (no `tools:` line, or one with `Edit` or `Write`), such as a repo's own implementer. A read-only agent with no pin (a repo's reviewer) inherits the session's Opus. `CLAUDE_CODE_SUBAGENT_MODEL` alone does not reach a repo agent, so the hook is the guarantee. A definition's `model` and the Agent tool's `model` still win.
- `haiku-worker`: the `haiku-worker` agent definition (Haiku 5.5, medium). Bounded mechanical work only. The advisor on `default`, `sonnet` or `opus` writes its brief and reads every hunk. Route to it only when a site-by-site recipe exists, the scope is about 30 sites or one folder, and a gate or test proves each site. Anything that needs a decision goes to `poteto-agent`, and a Haiku lane that fails its check twice moves to Sonnet. A pure location search goes to `Explore` with `model: "haiku"`. A doc sync that needs facts beyond the brief stays with the orchestrator.
- `opus`, `sonnet`: a native subagent with that model passed as the Agent tool's `model`.

No role runs on Grok, GPT or any non-Claude model, and no role runs above high effort. Read an upstream `grok-*` default as `sonnet` and an `xhigh` or `max` default as high.

poteto-mode's "Match the model to the job" step changes the effort and speed of each spawn. Here change only the Agent tool's `effort`, from low up to high, and keep the role's model. Drop `-fast`: the Agent tool has no fast mode.

A panel role is a list, with one subagent per entry. Each entry starts in a fresh context with its own brief and lens, so the entries do not anchor on each other. Diversity comes from separate contexts, lenses and models. Launch all entries in one message so they run in parallel.

```
feature, refactoring: default
bug-fix: default
perf-issue: default
hillclimb: default
judgment and prose: opus
hardest tasks: opus
how explorer: default
how explainer: default
why investigators: default
why synthesizer: opus
reflect tooling: default
reflect judgment, divergent, synthesizer: opus
arena runners: sonnet, sonnet, sonnet
arena cross-judge pool: opus, sonnet
swarm workers: default
mechanical lane worker (recipe given): haiku-worker
architect runners: opus, opus, sonnet
interrogate reviewers: opus, opus, sonnet
fork: not used; the hook denies it (it inherits Opus and the parent's whole context)
```

Edit-capable agents run Sonnet. `hooks/agent-default-model.py` rewrites an Opus request on one. Env `KOLIN_OPUS_BUILDERS=1` lets Kolin allow it. An Opus judgment seat runs as a read-only agent: `Plan`, `Explore` or `senior-reviewer`. The judgment seats are architect runners, the why synthesizer, reflect judgment, arena cross-judges, interrogate reviewers and "hardest tasks". Arena runners write code, so they run Sonnet.

Interrogate gives each reviewer one lens:

1. Correctness and data integrity: wrong numbers, races and lost writes.
2. Security and access: authorization, secrets and external writes.
3. Operations: migrations, rollback, deploy order and failure modes.

Plan, build and review are separate seats:

| Seat | Runs as | Model | Does |
|---|---|---|---|
| Orchestrator | the main session | Opus | Value case, plan, Kolin's asks, six-part briefs, `.pstack/status.md`, reads every delegated hunk. `hooks/edit-guard.py` blocks its first edit until `.pstack/status.md` has a `Value:` line, and its 3rd edited file unless status.md has `orchestrator-builds: <reason>` |
| Builder | `poteto-agent`, or the repo's implementer | Sonnet 5.5, medium (hook default when the agent pins no model and can edit) | One unit per brief, runs the gate, reports once. `poteto-agent` has no MCP, web or Agent tools: put that data in the brief |
| Sweeper | `haiku-worker` | Haiku 5.5, medium | Recipe work: renames, codemods, fixtures, searches the brief spells out |
| Searcher | `Explore` | Sonnet (hook default) | Wide read-only search, including the reading a brief needs; returns `file:line` facts, not file dumps |
| Reviewer | `senior-reviewer` | Opus 5.5, high, read-only | Fresh review of every non-trivial diff; never the builder. A Lite re-review of follow-up fix hunks passes `model: "sonnet"` |
| Comment sweep | `comment-sicko` (pstack) | Sonnet (hook default) | Deletes comments before review |

## Spend

Every turn re-reads the whole context, so a tool call costs about the context's size. These rules cut turns and context, not rigor:

- **Size tier.** For one owner and about 10 files or fewer, skip `how`, `architect` and the throughput checkpoint, and say so in one line. The value case, the builder, the fresh review and the verification skill stay; `.pstack/status.md` stays when the work has more than one unit.
- **New task, new session.** A long session re-reads all of its old context on each turn.
- **Read once.** The orchestrator reads ranges (`rg -n`, `sed -n a,b`), not whole files, and passes the `file:line` anchors, the neighbor it chose and the plan sections and skills by path in the brief, so the builder and the reviewer do not explore again. A hook injects the six policy principle leaves into `poteto-agent` only; a repo implementer's brief names them.
- **Batch.** Put independent reads and searches in one turn. Use `rg -g '*.ts'`, not an unquoted zsh glob.
- **Edit** per `agents/poteto-agent.md` (Spend); the main session edits only with Edit or Write (policy, Harness).
- **Gate once.** The builder runs targeted tests and the repo's known-trap check (for example `fallow:audit`) while it builds, and the full gate once at the end. Run the repo's known-trap check only through its script (for example `npm run fallow:audit`), never as raw `npx` with hand-typed flags. The builder owns the pre-review gate. The orchestrator runs the repo gate once, after the review fixes.
- **Background and parallel.** Spawn the builder in the background, and start the app stack (database, dev server) while it builds. Run the reviewer and the verification skill in parallel, and tell the reviewer the verification is running.
- **Watchers.** Stop a `Monitor` when its target changes. Cancel a fallback `ScheduleWakeup` once the agent it guards has reported. Run the last gate in the foreground, so the turn ends with the report and not with "waiting".
- **Sleep before load.** When a gate stalls or tests time out, read `pmset -g log | grep -E ' (Sleep|Wake|DarkWake) '` and the transcript's "computer was asleep" errors before blaming load; `heavy-slot.py` holds `caffeinate -i` for each heavy job, and `hooks/keep-awake.py` holds `caffeinate -i -t 3600` from each prompt or Agent spawn, so a long reviewer turn no longer lets the Mac idle-sleep. Then check `uptime`, and stop your own dev server and browser.
- **Review fixes go to the builder.** Send the reviewer's findings back to the builder with `SendMessage`, then rerun the repo's known-trap check. An orchestrator that fixes findings itself skips the builder's gate. `hooks/fix-rounds.py` denies a third `SendMessage` to one agent: spawn a fresh builder whose brief carries the original brief, every later directive and the open findings. A message that answers the builder's question or hands it the next unit is not a fix round: add `fix-rounds: <agent id> <reason>` to `.pstack/status.md`.
- **One unit per builder.** A unit is one layer (database, server or UI) and about 25 files at most. Split a brief that names more, so each builder ends in one report before it compacts. A browser proof of more than 3 screens is its own unit.
- **Plan panels.** A plan gets at most two review rounds of three reviewers, and each architect runner returns a design of about 150 lines at most. Change a plan doc with Edit, never a full rewrite.
- **Worktrees.** Never spawn an edit-capable agent with `isolation: "worktree"`: the harness then refuses its gate commands, and `hooks/agent-default-model.py` denies it. Create the worktree with `git worktree add <path> -b <branch> <base>` and name the path in the brief.
- **The push hook is the gate.** When the pre-push hook runs the full gate (for example `verify:pr`), do not run it again just before the push. Do not pipe a push or gate into `grep` or `tail`; `bash-guard.py` strips the filter, or rewrites it onto a saved log when it carries a status flag or redirect, and never blocks the command.

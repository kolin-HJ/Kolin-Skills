# pstack model roles on this machine

Replaces `~/.cursor/rules/pstack-models.mdc`. Role labels match the ones pstack skills name. Claude is the only provider. Every role runs as a native Claude subagent through the Agent tool, and no other provider's CLI or API is called.

- `default`: a native subagent with no `model` passed. The Kolin-Skills hook `hooks/agent-default-model.py` sets Sonnet 5.5 on every Agent call with no `model` whose definition pins none: `general-purpose`, `Explore`, `claude-code-guide`, and any user or repo agent with no `model:` line that can edit (no `tools:` line, or one with `Edit` or `Write`), such as a repo's own implementer. A read-only agent with no pin (a repo's reviewer) inherits the session's Opus. `CLAUDE_CODE_SUBAGENT_MODEL` alone does not reach a repo agent, so the hook is the guarantee. A definition's `model` and the Agent tool's `model` still win.
- `haiku-worker`: the `haiku-worker` agent definition (Haiku 5.5, medium). Bounded mechanical work only. The orchestrator writes its brief and reads every hunk. Route to it only when a site-by-site recipe exists, the scope is about 30 sites or one folder, and a gate or test proves each site. A rename, renumber or codemod from a census goes to `haiku-worker`, not `poteto-agent`. Anything that needs a decision goes to `poteto-agent`, and a Haiku lane that fails its check twice moves to Sonnet. A pure location search goes to `Explore`. A doc sync that needs facts beyond the brief stays with the orchestrator.
- `opus`, `sonnet`: a native subagent with that model passed as the Agent tool's `model`.

No role runs on Grok, GPT or any non-Claude model, and no role runs above high effort. Read an upstream `grok-*` default as `sonnet` and an `xhigh` or `max` default as high.

poteto-mode's "Match the model to the job" step changes the effort and speed of each spawn. Here change only the Agent tool's `effort`, from low up to high, and keep the role's model. Drop `-fast`: the Agent tool has no fast mode.

A panel role is a list, with one subagent per entry, each with its own brief and lens. Launch all entries in one message.

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
fork: inherits Opus and the parent's whole context; use it when that context is the point
```

Edit-capable agents run Sonnet; the hook denies an Opus request on one, because a silent rewrite once ran 180 "Opus" interrogate reviewers on Sonnet in 14 days. Env `KOLIN_OPUS_BUILDERS=1` lets Kolin allow Opus builders. An Opus judgment role runs as a read-only agent: `Plan`, `Explore` or `senior-reviewer`. The judgment roles are architect runners, the why synthesizer, reflect judgment, arena cross-judges, interrogate reviewers and "hardest tasks". Arena runners write code, so they run Sonnet.

Interrogate gives each reviewer one lens:

1. Correctness and data integrity: wrong numbers, races and lost writes.
2. Security and access: authorization, secrets and external writes.
3. Operations: migrations, rollback, deploy order and failure modes.

Plan, build and review are separate roles:

| Role | Runs as | Model | Does |
|---|---|---|---|
| Orchestrator | the main session | Opus | Plan, Kolin's asks, briefs, reads every delegated hunk. Builds small work itself |
| Builder | `poteto-agent`, or the repo's implementer | Sonnet 5.5, medium (hook default when the agent pins no model and can edit) | One unit per brief, runs the gate, reports once. `poteto-agent` has no MCP, web or Agent tools: put that data in the brief |
| Sweeper | `haiku-worker` | Haiku 5.5, medium | Recipe work: renames, codemods, fixtures, searches the brief spells out |
| Searcher | `Explore` | Sonnet (hook default) | Wide read-only search, including the reading a brief needs; returns `file:line` facts, not file dumps |
| Reviewer | `senior-reviewer` | Opus 5.5, high, read-only | Fresh review of every non-trivial diff; never the builder. A Lite re-review of follow-up fix hunks passes `model: "sonnet"` |
| Comment sweep | `comment-sicko` (pstack) | Sonnet (hook default) | Deletes comments before review |

## Spend

- **Size tier.** For one owner and about 10 files or fewer, skip `how`, `architect` and the throughput checkpoint, and build it yourself. The fresh review and the verification skill stay.
- **Read once.** The orchestrator reads ranges (`rg -n`, `sed -n a,b`), not whole files, and passes the `file:line` anchors, the neighbor it chose and the plan sections and skills by path in the brief, so the builder and the reviewer do not explore again.
- **Batch.** Use `rg -g '*.ts'`, not an unquoted zsh glob.
- **Edit** per `agents/poteto-agent.md` (Spend).
- **Gate once.** The builder runs targeted tests and the repo's known-trap check (for example `fallow:audit`) while it builds, and the full gate once at the end. Run the repo's known-trap check only through its script (for example `npm run fallow:audit`), never as raw `npx` with hand-typed flags. The builder owns the pre-review gate. The orchestrator runs the repo gate once, after the review fixes.
- **Background and parallel.** Spawn the builder in the background, and start the app stack (database, dev server) while it builds. Run the reviewer and the verification skill in parallel, and tell the reviewer the verification is running.
- **Sleep before load.** When a gate stalls or tests time out, read `pmset -g log | grep -E ' (Sleep|Wake|DarkWake) '` and the transcript's "computer was asleep" errors before blaming load; `heavy-slot.py` holds `caffeinate -i` for each heavy job, and `hooks/keep-awake.py` holds `caffeinate -i -t 3600` from each prompt or Agent spawn, so a long reviewer turn no longer lets the Mac idle-sleep. Then check `uptime`, and stop your own dev server and browser.
- **Review fixes go to the builder.** Send the reviewer's findings back to the builder with `SendMessage`, then rerun the repo's known-trap check. When a builder has drifted after two rounds, spawn a fresh one whose brief carries the original brief and the open findings.
- **One unit per builder.** A unit is one feature end to end and about 25 source files at most; cut a larger feature by user-facing slice, never by layer. Split a brief that names more, so each builder ends in one report before it compacts. A browser proof of more than 3 screens is its own unit.
- **Plan panels.** A plan gets at most two review rounds of three reviewers, and each architect runner returns a design of about 150 lines at most.
- **The push hook is the gate.** When the pre-push hook runs the full gate (for example `verify:pr`), do not run it again just before the push. Do not pipe a push or gate into `grep` or `tail`; `bash-guard.py` strips the filter, or rewrites it onto a saved log when it carries a status flag or redirect, and never blocks the command.

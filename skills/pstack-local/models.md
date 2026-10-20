# pstack model roles on this machine

Replaces `~/.cursor/rules/pstack-models.mdc`. Role labels match the ones pstack skills name. Claude is the only provider. Every role runs as a native Claude subagent through the Agent tool, and no other provider's CLI or API is called.

- `default`: a native subagent with no `model` passed. `~/.claude/hooks/agent-default-model.py` sets Sonnet 5.5 on every Agent call with no `model` whose definition pins none: `general-purpose`, `Explore`, `claude-code-guide`, and any user or repo agent with no `model:` line that can edit (no `tools:` line, or one with `Edit` or `Write`), such as a repo's own implementer. A read-only agent with no pin (a repo's reviewer) inherits the session's Opus. `CLAUDE_CODE_SUBAGENT_MODEL` alone did not reach a repo agent on 2026-10-20, so the hook is the guarantee. A definition's `model` and the Agent tool's `model` still win.
- `haiku-worker`: the `haiku-worker` agent definition (Haiku 5.5, medium). Bounded mechanical work only. The advisor on `default`, `sonnet` or `opus` writes its brief and reads every hunk (`loop-refactor-to-pstack/references/subagents.md`, "Advisor pattern").
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
arena runners: opus, opus, sonnet
arena cross-judge pool: opus, sonnet
swarm workers: default
mechanical lane worker (recipe given): haiku-worker
architect runners: opus, opus, sonnet
interrogate reviewers: opus, opus, sonnet
```

Interrogate gives each reviewer one lens:

1. Correctness and data integrity: wrong numbers, races and lost writes.
2. Security and access: authorization, secrets and external writes.
3. Operations: migrations, rollback, deploy order and failure modes.

Plan, build and review are separate seats:

| Seat | Runs as | Model | Does |
|---|---|---|---|
| Orchestrator | the main session | Opus | Value case, plan, Kolin's asks, six-part briefs, `.pstack/status.md`, reads every delegated hunk |
| Builder | `poteto-agent` | Sonnet 5.5, medium | One unit per brief, runs the gate, reports once |
| Sweeper | `haiku-worker` | Haiku 5.5, medium | Recipe work: renames, codemods, fixtures, searches the brief spells out |
| Searcher | `Explore` | Sonnet (hook default) | Wide read-only search; returns conclusions, not file dumps |
| Reviewer | `senior-reviewer` | Opus 5.5, high, read-only | Fresh review of every non-trivial diff; never the builder |
| Comment sweep | `comment-sicko` (pstack) | Sonnet (hook default) | Deletes comments before review |

Routing by job, with the Haiku cost results measured on 2026-10-07, lives in `loop-refactor-to-pstack/references/subagents.md`.

## Spend

Every turn re-reads the whole context, so a tool call costs about the context's size. On 2026-10-20 a 15-file feature took 180 Opus turns at about 130k context each. These rules cut turns and context, not rigor:

- **Size tier.** For one owner and about 10 files or fewer, skip `how`, `architect` and the throughput checkpoint, and say so in one line. The value case, `.pstack/status.md`, the builder, the fresh review and the verification skill stay.
- **Read once.** Read skill files with parallel `Read` calls. One `cat` of several files overflows the Bash output limit and is read twice. The orchestrator reads ranges (`rg -n`, `sed -n a,b`), not whole files, and passes the `file:line` anchors and the neighbor it chose in the brief, so the builder and the reviewer do not explore again.
- **Batch.** Put independent reads and searches in one turn. Use `rg -g '*.ts'`, not an unquoted zsh glob.
- **Edit with Edit.** A `sed -i` or heredoc edit gets only the late Bash lint pass, and the diff is harder to read.
- **Gate once.** The builder runs targeted tests and the repo's known-trap check (for example `fallow:audit`) while it builds, and the full gate once at the end. The orchestrator runs the repo gate once, after the review fixes.
- **Background and parallel.** Spawn the builder in the background, and start the app stack (database, dev server) while it builds. Run the reviewer and the verification skill in parallel, and tell the reviewer the verification is running.
- **Watchers.** Stop a `Monitor` when its target changes. Run the last gate in the foreground, so the turn ends with the report and not with "waiting".
- **Sleep before load.** When a gate stalls or tests time out, read `pmset -g log | grep -E ' (Sleep|Wake|DarkWake) '` and the transcript's "computer was asleep" errors before blaming load. On 2026-10-20 a 1-minute gate took 8 hours because the Mac slept; `heavy-slot.py` now holds `caffeinate -i` for each heavy job. Then check `uptime`, and stop your own dev server and browser.
- **Review fixes go to the builder.** Send the reviewer's findings back to the builder with `SendMessage`, then rerun the repo's known-trap check. On 2026-10-20 the orchestrator fixed findings itself with heredocs, and its edit added a `fallow:audit` failure that stood for 5 hours.
- **The push hook is the gate.** When the pre-push hook runs the full gate (for example `verify:pr`), do not run it again just before the push.

# pstack model roles on this machine

Replaces `~/.cursor/rules/pstack-models.mdc`. Role labels match the ones pstack skills name. Claude is the only provider. Every role runs as a native Claude subagent through the Agent tool, and no other provider's CLI or API is called.

- `default`: a native subagent with no `model` passed. `CLAUDE_CODE_SUBAGENT_MODEL` in `~/.claude/settings.json` makes that Sonnet 5.5, and `~/.claude/hooks/agent-default-model.py` does the same for `Explore` and `claude-code-guide`, which pin `inherit`. An agent definition's `model` and the Agent tool's `model` still win.
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
| Comment sweep | `comment-sicko` (pstack) | inherits | Deletes comments before review |

Routing by job, with the Haiku cost results measured on 2026-10-07, lives in `loop-refactor-to-pstack/references/subagents.md`.

# pstack model roles on this machine

Replaces `~/.cursor/rules/pstack-models.mdc`. Role labels match the ones pstack skills name. Claude is the only provider. Every role runs as a native Claude subagent through the Agent tool, and no other provider's CLI or API is called.

- `default`: a native subagent with no `model` passed. `CLAUDE_CODE_SUBAGENT_MODEL` runs it on Sonnet, including a repo's agents, read-only or not. A definition's `model` and the Agent tool's `model` win. `Explore` and `Plan` ignore the variable and inherit the session's model, so the model hook runs `Explore` on Sonnet unless the call passes `model`.
- `opus`, `sonnet`: a native subagent with that model passed as the Agent tool's `model`.

No role runs on Grok, GPT or any non-Claude model. Read an upstream `grok-*` default as `sonnet`.

poteto-mode's "Match the model to the job" step sets the Agent tool's `effort`, at any level the model offers. Drop `-fast`: the Agent tool has no fast mode.

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
mechanical lane worker (recipe given): default
architect runners: opus, opus, sonnet
interrogate reviewers: opus, opus, sonnet
fork: inherits Opus and the parent's whole context; use it when that context is the point
```

Builders start on Sonnet. Pass `model: "opus"` when the job is hard enough to need it. An Opus judgment role runs as `judge`, or `senior-reviewer` for a diff; a Sonnet seat passes `model: "sonnet"`. Never use `Plan` for judgment, because `Plan` and `Explore` start without `CLAUDE.md` or `AGENTS.md`. The judgment roles are architect runners, the why synthesizer, reflect judgment, arena cross-judges, interrogate reviewers and "hardest tasks". Arena runners write code, so they run Sonnet.

Interrogate is on demand, not the pre-PR gate (policy, Pull requests). Spawn it only on high-risk work (auth, money, data deletion) or when Kolin or the CEO asks. When it runs, run each Opus seat as `senior-reviewer` and the Sonnet seat as `senior-reviewer` with `model: "sonnet"`, with the lens in the brief. Interrogate gives each reviewer one lens:

1. Correctness and data integrity: wrong numbers, races and lost writes.
2. Security and access: authorization, secrets and external writes.
3. Operations: migrations, rollback, deploy order and failure modes.

Plan, build and review are separate roles:

| Role | Runs as | Model | Does |
|---|---|---|---|
| Orchestrator | the main session | Opus | Plan, Kolin's asks, briefs, reads every delegated hunk. Builds small work itself |
| Builder | `poteto-agent`, or the repo's implementer | Sonnet, high | One unit per brief, runs the gate, reports once. `poteto-agent` has no MCP, web or Agent tools: put that data in the brief |
| Searcher | `Explore` | Sonnet. Pass `model: "opus"` when the search needs judgment | Wide read-only search, including the reading a brief needs; returns `file:line` facts, not file dumps |
| Judge | `judge` | Opus, no edit tools | One design or judgment call, with the policy and the repo's `AGENTS.md` loaded |
| Reviewer | `senior-reviewer` | Opus, high, read-only | Do not spawn by default. Prefer tests, the verify skill, UI proof and harnesses. Spawn only for high-risk work or when Kolin or the CEO asks; never the builder. If spawned: a re-check limited to a small fix delta is that Lite re-review on sonnet, unless the delta touches auth, money or data deletion (then Opus). If a reviewer returns without a verdict, resume or message that same subagent once before spawning another. |
| Comment sweep | `comment-sicko` (pstack) | Sonnet | Deletes comments before review |

## Size

For one owner and about 10 files or fewer, skip `how`, `architect` and the throughput checkpoint, and build it yourself. The proof stays.

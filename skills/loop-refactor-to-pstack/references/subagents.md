# Subagents: one Claude model per role

The strongest model (Opus) plans and reviews, the mid-tier model (Sonnet) builds, and Haiku does mechanical sweeps. Every subagent runs through an agent definition that loads pstack before it works. The coordinator stays on the session's model: it owns briefs, judgment and the user report (Orchestrate, Roles), and never hands those down. The builder never reviews its own work.

## Which definition for which job

| Job | Agent | Why this one |
|---|---|---|
| Lane worker, codemod author, census or audit helper, verifier for a unit | `poteto-agent`, or the implementer the repo's `AGENTS.md` names | The `builder-context.py` hook gives it the six principle leaves, and it does not read `poteto-mode`. A `general-purpose` delegate gets no leaves and drifts. |
| Diff review before a commit | `senior-reviewer` (Opus 5.5) | Fresh context, read-only tools, two passes |
| Comment sweep before review (`no-comments`) | `comment-sicko` | pstack's own comment reviewer, with no model pin |
| Bounded mechanical work with a spelled-out recipe and a gate per site: a rename or renumber from a census, a gate-driven codemod, a codemod with stop conditions, a fixture | `haiku-worker` (Haiku 5.5) | Same final quality as Sonnet, at 27 to 55% lower total cost (measured). The advisor (the coordinator) writes the brief and reads every hunk. See "Advisor pattern" below. |
| A doc sync that needs facts beyond the brief, or a present-versus-past call per sentence | None. The advisor edits directly. | Neither Haiku nor Sonnet got it right in one round, and brief plus review cost more than the edit (measured). |
| A pure location search ("where is X used") | `Explore` with `model: "haiku"` | Built-in types ignore definitions, so the override is the only pin. Never give it code to write or judge: it loads neither pstack nor the user's rules. |

Never use `general-purpose` or `Plan` for program work. If a job fits none of the rows, use `poteto-agent` with a read-only brief.

## How the model is pinned

- The pin lives in each definition's frontmatter: `poteto-agent` and any repo implementer pin `model: claude-sonnet-5-5` with `effort: medium`, `senior-reviewer` pins `claude-opus-5-5`, and `haiku-worker` pins `claude-haiku-5-5`. `comment-sicko` is pstack's and has no pin. Launch these agents **without** a `model` argument, so the definition wins and one file changes the whole program.
- Run `bash <skill>/assets/check-subagents.sh [<repo implementer> ...]` in Phase 0 and after any change to agent files. It checks each pin above in the repo's `.claude/agents/`, then `~/.claude/agents/`, and that `comment-sicko` exists. A wrong or missing pin is fixed in the frontmatter with the user's yes, because agent definitions are harness configuration.
- A Codex agent `.toml` is generated from its `.md`; never edit the mirror by hand.
- Every seat is a native Claude subagent through the Agent tool (`pstack-local/models.md`). Do not start a seat with the `claude` CLI, because it takes the CLI's default model, not the definition's pin.
- Record the model in the ledger: `orch ledger record … --verifier poteto-agent/sonnet-5.5`.

## Worktrees for workers

Lanes share the one program worktree, each with its own files. Launch every worker without `isolation`, with the program worktree's absolute path in the prompt and every Bash command prefixed with `cd <path> && `. The Agent tool's `isolation: "worktree"` would put the lane on a separate branch, and it can also lose its working-directory context, so every Bash call the worker makes is refused. A read-only seat or an `arena` candidate that must not touch the program tree gets its own scratch worktree, which you create in a subshell (`git worktree add <path> <program branch>`), because a `cd` in the coordinator's shell moves the session.

## Panels keep their diversity

`interrogate`, `arena` and `architect` want one reviewer per model family. Claude is the only provider (`pstack-local/models.md`), so each seat that upstream gives another model family is a fresh Claude subagent on a different model or lens. Say in the report that every seat was Claude.

## Briefs written for the builder's tier

A medium-effort worker follows instructions well and improvises poorly. The brief carries what it cannot infer:

- The nine fields (`references/brief-templates.md`), with no field left vague.
- Exact paths it owns and must not touch, exact commands, and the literal output that means done.
- Every rule it depends on, quoted from `AGENTS.md`, plus the standing orders pasted or cited by path.
- The decided tradeoffs, so they do not come back as findings.
- Stop conditions: a file changed under it, a command failing twice, a site outside scope, a behavior change.
- A scope it can finish: about 30 to 70 sites, one folder group, and a timebox. Split anything larger rather than raising the effort.
- No sub-workers, except one read-only reviewer it waits for.

## The review pass runs in a fresh read-only thread

Each unit's review runs on `senior-reviewer` (Opus 5.5) in a new thread that has not seen the build, with read-only tools. It gets the unit's brief, the diff and the evidence, and returns PASS or findings. Cap it at two review rounds per unit, then rewrite the brief.

## When Sonnet is not enough

Raise effort or move up a model only on evidence: the same lane failing its VERIFY twice after a brief rewrite, or a verifier finding the same class of defect in two lanes. Then rewrite the brief first (Orchestrate: two revision rounds, then rewrite), and only if that fails, ask the user before changing a pin. Record the call in the decision trail.

## Advisor pattern: Haiku 5.5 works, the coordinator advises

`haiku-worker` pins `claude-haiku-5-5` at medium effort. The coordinator is the advisor and keeps everything that needs judgment.

| Advisor (the coordinator) | Worker (Haiku 5.5) |
|---|---|
| Design, types, module shape, tradeoffs | Applies a recipe the brief spells out |
| Writes the brief with exact files, commands and the literal output that means done | Edits only its files, runs only its commands |
| Reads every hunk and every new test, then accepts or rewrites the brief | Reports commands with literal results, apart from what it inferred |
| Reviews (`senior-reviewer`, `interrogate`), user-facing numbers, schema, access, and paths that read or write an external system | Never touches those paths |

Route to Haiku only when a site-by-site recipe exists, the scope is about 30 sites or one folder group, and a gate or test proves each site. Anything that needs a decision goes to `poteto-agent` on Sonnet. A Haiku worker that stops and reports has done its job. Escalate the lane to Sonnet after two failed VERIFY rounds, as in "When Sonnet is not enough".

Measured on 2026-10-07 (four lanes, one run per cell): the worker costs about $0.01 a lane and the advisor's review costs $0.39 to $0.77. The review is the cost to cut, so:

- Put the worktree's absolute path in the brief, and tell the worker to run every command from it. Haiku's one failure was running in the parent session's directory.
- Keep the worker's prompt under 100K tokens. Above that, Haiku bills five times its base rate.
- Review the diff and the gate output. Do not reread whole files that a gate already proves.

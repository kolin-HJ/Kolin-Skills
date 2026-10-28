---
name: pstack-local
description: Use whenever poteto-mode or any other pstack skill (how, why, architect, arena, swarm, interrogate, no-comments, unslop, blast-radius, tdd, figure-it-out, create-formal-verification-skill, statechart, the principle-* skills) runs in Claude Code, Codex, Grok or Cursor. Maps pstack's Cursor tools, model roles and paths onto this machine, and lists where Kolin's AGENTS.md rules override pstack.
---

# pstack on this machine

pstack ([upstream](https://github.com/cursor/plugins/tree/main/pstack)) is written for Cursor. Apply this file wherever a pstack skill names a Cursor tool, path or model.

## Loading a pstack skill

Every pstack skill sets `disable-model-invocation: true`, so the Skill tool refuses it. When a playbook says "run the **how** skill" or "read the leaf principle", read `~/.agents/skills/<name>/SKILL.md` and follow it. Relative paths inside it (`references/`, `playbooks/`, `../principle-*/`) resolve from that directory. Kolin can still type `/poteto-mode`, `/how` and the rest.

## Cursor term to local equivalent

| pstack says | Do this |
|---|---|
| `Task` with `subagent_type: generalPurpose` | Claude Code: the Agent tool with `general-purpose`. Codex: a spawned agent. |
| `subagent_type: "poteto-agent"` | A builder: `poteto-agent`. A read-only helper: `Explore`. A repo's own named implementer is a project fact; use it only for that repo's code. |
| `subagent_type: "comment-sicko"` (was `Comment Sicko`) | `comment-sicko`, pstack's own agent, linked by `apply` |
| `readonly: true`, or any role `models.md` runs on Opus | `Plan` with the role's model: read-only, keeps MCP. `Explore` for a search. Not `general-purpose`: it can edit, so `hooks/agent-default-model.py` denies Opus on it. |
| `environment: "cloud"`, `cloud_base_branch` | A worktree from `git worktree add <path> -b <branch> <base>`, named in the brief. |
| `model: <slug>` | The role line in `models.md` next to this file. |
| `~/.cursor/rules/pstack-models.mdc`, `/setup-pstack` | `models.md` next to this file. Never write `~/.claude/rules/pstack-models.md`. |
| `AskQuestion` | `AskUserQuestion` |
| todolist | The harness's todo or task list. If there is none, a checklist in the reply. |
| Cursor `/loop` | Claude Code `/loop`, with `ScheduleWakeup` or `Monitor`. Codex: keep working in the turn. |
| Babysit's watcher (`watch-pr` under `/loop`) | T3 Code: `watch_pull_request` in the thread that owns the PR, then end the turn. Elsewhere: `watch-pr` as one background command. |
| Cursor built-in `create-skill` | `anthropic-skills:skill-creator`. A repo skill goes in `.agents/skills/<name>/SKILL.md` with a `.claude/skills/<name>` symlink. A global skill goes in Kolin-Skills `skills/<name>/`; if a tool wrote it into home, run `kolin-skills import <path>`. |
| `/deslop`, `control-ui`, `control-cli` from `cursor-team-kit` | Vendored and linked with the same names. For proof, use the repo's own verification skill (its CLI and feature map) first; if the repo has none, build one with `create-verification-skill` rather than scripting a one-off. The chrome-devtools MCP is for ad-hoc inspection. |
| `.cursor/skills/<name>/` output, or any project-local skill a pstack skill writes | `.agents/skills/<name>/SKILL.md` with a `.claude/skills/<name>` symlink. |
| `create-formal-verification-skill` tools | Install the verifier per repo at a pinned version (TLC: Java 11+ and `tla2tools.jar`. Kani: `cargo install --locked kani-verifier`, then `cargo kani setup`). A spec or harness has no comments. |
| `statechart` | TLA+ model → chart. |
| `/visualize` (ketchup) | A Mermaid diagram in the reply, or a chart that a script renders. |
| `agent-transcripts/`, `~/.cursor/projects/` | Claude Code: `~/.claude/projects/<cwd with each / and . as ->/*.jsonl`. Codex: `~/.codex/sessions/`. Read only the current workspace's transcripts. |
| `mcps/` discovery (why) | The MCP tools listed in this session. |
| Origin forge | Absent here. Use `gh`. |
| Bugbot | Any review bot on the PR. Same skeptical triage (`poteto-mode/references/bugbot-triage.md`). |
| Any other Cursor term (`run_in_background`, `resume`, Automations) | pstack's own map: `~/.agents/vendor/cursor-plugins/pstack/docs/harness/claude-code.md`. This file and `models.md` win where they differ. Agent names and slash commands have no `pstack:` prefix. |

## Model roles

`models.md` assigns each role. pstack roles run on Claude only, as native subagents; read another provider's name in a pstack skill as one more Claude subagent from `models.md`. `council` is the one exception: Kolin invokes it to get other providers. A subagent's output is a lead: open the code it cites before a finding becomes yours.

## Where Kolin's rules win

The global policy and the repo's `AGENTS.md` win every conflict with pstack. This adapter adds only how they land on pstack's own steps:

- **Autonomy.** pstack lets external actions (team chat, tickets, evals) run without asking. Here they need Kolin's yes (policy, Approvals). Opening a PR acts without asking in pstack. Shipping, Autopilot and Babysit `drive` merge nothing without an explicit ask (policy, Approvals). `autopilot-full` is not used.
- **PR title and body** use the repo's template. Where the repo has none, start from `pr-body <base>` (policy, Pull requests) in place of pstack's Why, Scope and Tradeoffs.
- **Tests** in `tdd`, Refactoring step 1 and the multi-phase plan's unit box follow the policy's Done. A new test only for a named behavior a caller relies on. A unit box may read "No test: <why>". No snapshot. Delete a characterization pin that a kept test duplicates. No sibling-coverage sweep.
- **Comments.** poteto-mode's Comments section keeps a non-obvious why. Here no comment survives except a lint directive with `-- <reason>`.
- **Builder brief.** poteto-mode says to put its path in every `poteto-agent` prompt. Here the brief names the files and the done check, quotes any principle the unit depends on, and the builder does not read poteto-mode.
- **Reply style.** Keep pstack's Writing the reply rules. State the principles that changed a decision in one line, not a section.

## Own skills

Read `thermo-nuclear-code-quality-review` when Kolin asks for a harsh structure review.

## Verify the setup

`kolin-skills check` proves wiring, not behavior. For a routing or model-role change, use `poteto-mode/playbooks/eval.md` with organic tasks and transcript evidence.

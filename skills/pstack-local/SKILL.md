---
name: pstack-local
description: Use whenever poteto-mode or any other pstack skill (how, why, architect, arena, swarm, interrogate, no-comments, unslop, blast-radius, tdd, figure-it-out, create-formal-verification-skill, the principle-* skills) runs in Claude Code, Codex, Grok or Cursor. Maps pstack's Cursor tools, model roles and paths onto this machine, and lists where Kolin's AGENTS.md rules override pstack.
---

# pstack on this machine

pstack ([upstream](https://github.com/cursor/plugins/tree/main/pstack)) is written for Cursor. The skills are vendored unmodified in `~/.agents/vendor/cursor-plugins` (`kolin-skills upstream`) and linked by `kolin-skills apply` into `~/.agents/skills` (Codex) and `~/.claude/skills` (Claude Code, Grok). Cursor uses its installed pstack plugin and the `~/.cursor/skills/pstack-local` link. Read this file with `poteto-mode` and apply it wherever a pstack skill names a Cursor tool, path or model.

## Loading a pstack skill

Every pstack skill sets `disable-model-invocation: true`, so the Skill tool refuses it. When a playbook says "run the **how** skill" or "read the leaf principle", read `~/.agents/skills/<name>/SKILL.md` and follow it. Relative paths inside it (`references/`, `playbooks/`, `../principle-*/`) resolve from that directory. The user can still type `/poteto-mode`, `/how` and the rest.

## Cursor term to local equivalent

| pstack says | Do this |
|---|---|
| `Task` with `subagent_type: generalPurpose` | Claude Code: the Agent tool with `general-purpose`. Codex: a spawned agent. |
| `subagent_type: "poteto-agent"` | A code-writing delegate: `poteto-agent`, the builder seat. A read-only helper: `Explore`. A repo's own named implementer is a project fact; use it only for that repo's code. |
| `subagent_type: "comment-sicko"` (was `Comment Sicko`) | `comment-sicko`, pstack's own agent, linked by `apply` |
| `readonly: true` | `Explore`, or a reviewer agent without Edit and Write. |
| `environment: "cloud"`, `cloud_base_branch` | A local worktree from `git worktree add <path> -b <branch> <base>`, named in the brief. Not `isolation: "worktree"` (models.md, Worktrees). |
| `model: <slug>` | The role line in `models.md` next to this file. |
| `~/.cursor/rules/pstack-models.mdc`, `/setup-pstack` | `models.md` next to this file. Never write `~/.claude/rules/pstack-models.md`. |
| `AskQuestion` | `AskUserQuestion` |
| todolist | The harness's todo or task list. If there is none, a checklist in the reply. |
| Cursor `/loop` | Claude Code `/loop`, with `ScheduleWakeup` or `Monitor`. Codex: keep working in the turn. |
| Cursor built-in `create-skill` | `anthropic-skills:skill-creator`. A repo skill goes where AGENTS.md Instruction files says. A global skill goes in Kolin-Skills `skills/<name>/`; if a tool wrote it into home, run `kolin-skills import <path>`. |
| `/deslop`, `control-ui`, `control-cli` from `cursor-team-kit` | Vendored and linked with the same names. For proof, use the repo's own verification skill (its CLI and feature map) first; if the repo has none, build one with `create-verification-skill` rather than scripting a one-off. The chrome-devtools MCP is for ad-hoc inspection. |
| `.cursor/skills/<name>/` output, or any project-local skill a pstack skill writes | `.agents/skills/<name>/SKILL.md` with a `.claude/skills/<name>` symlink. |
| `create-formal-verification-skill` tools | Install the verifier per repo at a pinned version (TLC: Java 11+ and `tla2tools.jar`. Kani: `cargo install --locked kani-verifier`, then `cargo kani setup`). A spec or harness has no comments. |
| `/visualize` (ketchup) | A Mermaid diagram in the reply, or a chart that a script renders. |
| `agent-transcripts/`, `~/.cursor/projects/` | Claude Code: `~/.claude/projects/<cwd with each / and . as ->/*.jsonl`. Codex: `~/.codex/sessions/`. Read only the current workspace's transcripts. |
| `mcps/` discovery (why) | The MCP tools listed in this session. |
| Origin forge | Absent here. Use `gh`. |
| Bugbot | Any review bot on the PR. Same skeptical triage (`poteto-mode/references/bugbot-triage.md`). |
| Any other Cursor term (`run_in_background`, `resume`, Automations) | pstack's own map: `~/.agents/vendor/cursor-plugins/pstack/docs/harness/claude-code.md`. This file and `models.md` win where they differ. Agent names and slash commands have no `pstack:` prefix. |

## Model seats

`models.md` assigns each role and holds the Spend rules. Claude is the only provider, so every role and every panel entry runs as a native subagent through the Agent tool. Never call another provider's CLI or API, even when a pstack skill names one. Read such a name as one more Claude subagent from `models.md`.

Put the full brief in each subagent's prompt, because a subagent has none of your context. A subagent's output is a lead: open the code it cites before a finding becomes yours. A candidate that has to write and run the gates runs in its own worktree.

## Where Kolin's rules win

The global policy (`policy/AGENTS.md`) lists the rules that override pstack (Approvals, Overrides of pstack). It also outranks the repo's `AGENTS.md`, which adds project facts. Both win every conflict with pstack. This adapter adds only how those rules land on pstack's own steps:

- **Autonomy and Opening a PR** act without asking in pstack. Here a commit, push or PR on a work branch needs no ask; a merge or deploy does (policy, Approvals). Shipping, Autopilot and Babysit `drive` merge nothing without an explicit ask. `autopilot-full` is not used.
- **External writes** (chat, tickets) wait for a yes unless the repo's `AGENTS.md` allows them.
- **PR title and body** use the repo's template. Where the repo has none, start from `scripts/pr-body <base>` (policy, Before a PR ships) in place of pstack's Why, Scope and Tradeoffs.
- **Tests** in `tdd`, Refactoring step 1 and the multi-phase plan's unit box follow the policy's Tests and proof. A new test only for a named behavior a caller relies on. A unit box may read "No test: <why>". No snapshot. Delete a characterization pin that a kept test duplicates. No sibling-coverage sweep.
- **Feature, Bug fix and Refactoring** start with the AGENTS.md value case. **Opening a PR** runs `scripts/diff-audit <base>` first.
- **Comments.** poteto-mode's Comments section keeps a non-obvious why. Here no comment survives except a gate directive with `-- <reason>`.
- **Builder brief.** poteto-mode says to put its path in every `poteto-agent` prompt. Here the builder gets the principle leaves from `hooks/builder-context.py` and does not read poteto-mode.
- **Fix rounds.** poteto-mode gives each fix round a fresh subagent. Here up to two rounds go back to the builder (policy, Delegation; `models.md` Spend), then a fresh builder.
- **Reply style.** Keep pstack's Writing the reply rules. State the principles that changed a decision in one line, not a section.

## Own skills

`foundation` is the root; every other skill inherits its flow, check points and bars. The grouped index lives in the Kolin-Skills README.

`full-stop` and `full-send` are the in-session approval when Kolin invokes them: full stop covers a ready PR; full send adds the merge of that one PR. `scripts/mode-reminder` flags either phrase.

Read `thermo-nuclear-code-quality-review` for the diff pass in the policy's Quality work, or when the user asks for a harsh structure review.

## Verify the setup

This adapter, the policy, the agents and the hooks live in the Kolin-Skills repo. Run `kolin-skills check` after you change any of them. It checks links, rendered settings, agent mirrors, spend caps and tests.

The check proves wiring, not behavior. For a routing or model-seat change, use `poteto-mode/playbooks/eval.md` with organic tasks and transcript evidence.

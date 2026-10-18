---
name: pstack-local
description: Use whenever poteto-mode or any other pstack skill (how, why, architect, arena, swarm, interrogate, no-comments, unslop, blast-radius, tdd, figure-it-out, the principle-* skills) runs in Claude Code, Codex, Grok or Cursor. Maps pstack's Cursor tools, model roles and paths onto this machine, and lists where Kolin's AGENTS.md rules override pstack.
---

# pstack on this machine

pstack ([upstream](https://github.com/cursor/plugins/tree/main/pstack)) is written for Cursor. The skills are vendored unmodified in `~/.agents/vendor/cursor-plugins` (`kolin-skills upstream`) and linked by `kolin-skills apply` into `~/.agents/skills` (Codex) and `~/.claude/skills` (Claude Code, Grok). Cursor uses its installed pstack plugin and the `~/.cursor/skills/pstack-local` link. Read this file with `poteto-mode` and apply it wherever a pstack skill names a Cursor tool, path or model.

## Loading a pstack skill

Every pstack skill sets `disable-model-invocation: true`, so the Skill tool refuses it. When a playbook says "run the **how** skill" or "read the leaf principle", read `~/.agents/skills/<name>/SKILL.md` and follow it. Relative paths inside it (`references/`, `playbooks/`, `../principle-*/`) resolve from that directory. The user can still type `/poteto-mode`, `/how` and the rest.

## Cursor term to local equivalent

| pstack says | Do this |
|---|---|
| `Task` with `subagent_type: generalPurpose` | Claude Code: the Agent tool with `general-purpose`. Codex: a spawned agent. |
| `subagent_type: "poteto-agent"` | `poteto-agent`. For a code-writing delegate in a repo whose AGENTS.md names its own implementer (hj-plm: `plm-implementer`), use that one. Read-only helpers stay on `poteto-agent`. |
| `subagent_type: "Comment Sicko"` | `comment-sicko` |
| `readonly: true` | `Explore`, or a reviewer agent without Edit and Write. |
| `environment: "cloud"`, `cloud_base_branch` | A local worktree (`isolation: "worktree"`) created from that branch. |
| `model: <slug>` | The role line in `models.md` next to this file. |
| `~/.cursor/rules/pstack-models.mdc`, `/setup-pstack` | `models.md` next to this file. Edit it to change a role. |
| `AskQuestion` | `AskUserQuestion` |
| todolist | The harness's todo or task list. If there is none, a checklist in the reply. |
| Cursor `/loop` | Claude Code `/loop`, with `ScheduleWakeup` or `Monitor`. Codex: keep working in the turn. |
| Cursor built-in `create-skill` | `anthropic-skills:skill-creator`, then place the skill per the instruction-file rules in AGENTS.md. |
| `/deslop`, `control-ui`, `control-cli` from `cursor-team-kit` | Vendored and linked with the same names. For proof, use the repo's own verification skill (its CLI and feature map) first; if the repo has none, build one with `create-verification-skill` rather than scripting a one-off. The chrome-devtools MCP is for ad-hoc inspection. |
| `.cursor/skills/<name>/` output | `.agents/skills/<name>/SKILL.md` with a `.claude/skills/<name>` symlink. |
| `agent-transcripts/`, `~/.cursor/projects/` | Claude Code: `~/.claude/projects/<cwd with each / and . as ->/*.jsonl`. Codex: `~/.codex/sessions/`. Read only the current workspace's transcripts. |
| `mcps/` discovery (why) | The MCP tools listed in this session. |
| Origin forge | Absent here. Use `gh`. |
| Bugbot | Any review bot on the PR. Same skeptical triage (`poteto-mode/references/bugbot-triage.md`). |

## Model seats

`models.md` assigns each role. Claude is the only provider, so every role and every panel entry runs as a native subagent through the Agent tool. Never call another provider's CLI or API, even when an upstream pstack skill names Codex, Grok or GPT. Read such a name as one more Claude subagent from the `models.md` list.

Put the full brief in each subagent's prompt, because a subagent has none of your context. A subagent's output is a lead: open the code it cites before a finding becomes yours. A candidate that has to write and run the gates runs in its own worktree.

## Where Kolin's rules win

`~/.codex/AGENTS.md` lists the rules that override pstack (Approvals, Overrides of pstack) and the repo's `AGENTS.md` adds its own. They win every conflict. This adapter adds only how those rules land on pstack's own steps:

- **Autonomy and Opening a PR** act without asking in pstack. Here a commit, push, PR, merge or deploy waits for approval in the session. Shipping, Autopilot and Babysit `drive` merge nothing without an explicit ask. `autopilot-full` is not used.
- **External writes** (chat, tickets) wait for a yes unless the repo's `AGENTS.md` allows them.
- **PR title and body** use the repo's template. pstack's Why, Scope, Tradeoffs, Blast Radius and Verification sections fill in only where the repo has none.
- **`tdd`'s trigger** does not exempt any test from being seen failing first.
- **Comments.** poteto-mode's Comments section keeps a non-obvious why. Here no comment survives except a gate directive with `-- <reason>`.
- **Reply style.** Keep pstack's Writing the reply rules. State the principles that changed a decision in one line, not a section.

## Other upstreams

- `thermo-nuclear-code-quality-review` (cursor-team-kit) is vendored and linked like pstack. Read it for the diff pass in AGENTS.md Quality work, or when the user asks for a harsh structure review. `senior-reviewer` already carries its approval bar.
- [ponytail](https://github.com/DietrichGebert/ponytail) is cloned to `~/.agents/vendor/ponytail` and watched, never linked. Its mode writes `shortcut:` comments, which the no-comments rule bans, and its review duplicates `senior-reviewer`. Its rules live as ported lines: the Quality work ladder in AGENTS.md. When `kolin-skills upstream` reports a change, port a rule only if it earns its place.

## Kolin's own skills

- `local-supabase` (`~/.agents/skills/local-supabase/SKILL.md`) owns every local Supabase or Postgres database in every repo: one stack per checkout in the Supabase CLI's native runtime, never Docker. Read it before you start, seed or connect to one.
- `full-stop` and `full-send` (`~/.agents/skills/full-*/SKILL.md`) are the in-session approval when Kolin invokes them: full stop covers commit, push and a ready PR, and full send adds the merge of that one PR. `scripts/mode-reminder` flags either phrase on each prompt.

## Verify the setup

This adapter, the policy, the agents and the hooks live in the Kolin-Skills repo. Run `kolin-skills check` after you change any of them. It checks that home matches the repo (links, rendered settings, agent mirrors), the spend caps, and the hook and apply tests.

The check proves wiring, not behavior. For a routing or model-seat change, use `poteto-mode/playbooks/eval.md` with organic tasks and transcript evidence.

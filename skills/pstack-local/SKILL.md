---
name: pstack-local
description: Use when running pstack skills (poteto-mode, how, why, teach, architect, arena, swarm, interrogate, no-comments, unslop, blast-radius, tdd, figure-it-out, create-formal-verification-skill, statechart, principle-*) or explaining/walking through changes in Claude Code, Codex, Grok Bot, Cursor or Antigravity. Maps Cursor tools, model roles and paths, and lists Kolin's overrides.
---

# pstack on this machine

pstack ([upstream](https://github.com/cursor/plugins/tree/main/pstack)) is written for Cursor. Apply this file wherever a pstack skill names a Cursor tool, path or model.

## Loading a pstack skill

`kolin-skills apply` links skills into `~/.agents/skills` (registered in Antigravity's `skills.json`). In Claude Code, use the Skill tool. In Codex and Antigravity (no Skill tool), read `SKILL.md` at its supplied path, or `~/.agents/skills/<name>/SKILL.md` when unlisted; resolve relative paths from that folder. `apply` removes the invocation lock from `poteto-mode`, `how`, `architect`, `interrogate`, and the six core principles (`principle-model-the-domain`, `principle-laziness-protocol`, `principle-subtract-before-you-add`, `principle-type-system-discipline`, `principle-minimize-reader-load`, `principle-boundary-discipline`). Every other pstack skill, `tdd` and `correct` included, stays locked and is read by path when named.

## Cursor term to local equivalent

| pstack says | Do this |
|---|---|
| `Task` with `subagent_type: generalPurpose` | Claude: Agent (`general-purpose`). Codex: spawned agent. Antigravity: `invoke_subagent` (`self`) or T3 `delegate_task`. |
| `subagent_type: "poteto-agent"` | Builder: `poteto-agent`. Read-only search: Claude `Explore`, Codex `explorer`, Antigravity `research`. Use a repo's named implementer only in that repo. |
| `subagent_type: "comment-sicko"` (was `Comment Sicko`) | `comment-sicko`, pstack's own agent, linked by `apply` |
| `readonly: true`, or any role `models.md` runs on Opus | Claude: `judge` for judgment, `Explore` for search. Codex: `judge` to judge, `senior-reviewer` to review, `explorer` to search. |
| `environment: "cloud"`, `cloud_base_branch` | T3 Code: `delegate_task` with `isolation: "worktree"`; never create a child checkout in the shell. Else use the harness's worktree support, or `git worktree add <path> -b <branch> <base>`. |
| `model: <slug>` | Claude: the role line in `models.md`. Codex: inherit the session model unless the user or harness directs otherwise. |
| `~/.cursor/rules/pstack-models.mdc`, `/setup-pstack` | `models.md` next to this file. Never write `~/.claude/rules/pstack-models.md`. |
| `AskQuestion` | Use the harness's user input tool when available. |
| todolist | The harness's todo or task list. If there is none, a checklist in the reply. |
| Cursor `/loop` | Claude Code `/loop`, with `ScheduleWakeup` or `Monitor`. Codex: keep working in the turn. |
| Babysit's watcher (`watch-pr` under `/loop`) | T3 Code: `watch_pull_request` in the thread that owns the PR, then end the turn. Elsewhere: `watch-pr` as one background command. |
| Project tracker (`notes.md`), Project store, PR/CI event subscriptions | T3 Code: that thread's project notes and `watch_pull_request`. Elsewhere: `.pstack/` or the loop store, and `gh pr view` / `gh pr checks`. |
| Cursor built-in `create-skill` | `anthropic-skills:skill-creator`. A repo skill goes in `.agents/skills/<name>/SKILL.md` with a `.claude/skills/<name>` symlink. A global skill goes in Kolin-Skills `skills/<name>/`; if a tool wrote it into home, run `kolin-skills import <path>`. |
| `/deslop`, `control-ui`, `control-cli` from `cursor-team-kit` | Vendored and linked with the same names. For proof, use the repo's own verification skill (its CLI and feature map) first; if the repo has none, build one with `create-verification-skill`, driven by `agent-browser` or `agent-desktop`, rather than scripting a one-off. |
| Browser or computer use, UI proof | Web or Electron web content: `agent-browser`. Native app: `agent-desktop`. Read `skills get core` or `skills get desktop` first. Re-read state after each act. Pass the session id on every call. Codex: call `agent-browser-guard` (same args, files in `~/.agent-browser-evidence`); `agent-desktop` asks Kolin per call. Repo Playwright: `control-ui`. Terminal app: `control-cli`. Keep traces, HARs and videos local. |
| `.cursor/skills/<name>/` output, or any project-local skill a pstack skill writes | `.agents/skills/<name>/SKILL.md` with a `.claude/skills/<name>` symlink. |
| `create-formal-verification-skill` tools | Install the verifier per repo at a pinned version (TLC: Java 11+ and `tla2tools.jar`. Kani: `cargo install --locked kani-verifier`, then `cargo kani setup`). A spec or harness has no comments. |
| `statechart` | TLA+ model → chart. |
| explain / how / "walk me through" / walkthrough | Read `teach`. Keep `/how` as pstack's how skill; teach runs it. |
| `/visualize` (ketchup) | An `explainer` page, or a chart that a script renders. |
| `agent-transcripts/`, `~/.cursor/projects/` | Claude Code: `~/.claude/projects/<cwd with each / and . as ->/*.jsonl`. Codex: `~/.codex/sessions/`. Read only the current workspace's transcripts. |
| `mcps/` discovery (why) | The MCP tools listed in this session. |
| Origin forge | Absent here. Use `gh`. |
| Bugbot | Any review bot on the PR. Same skeptical triage (`poteto-mode/references/bugbot-triage.md`). |
| Any other Cursor term (`run_in_background`, `resume`, Automations) | pstack's own map: `~/.agents/vendor/cursor-plugins/pstack/docs/harness/claude-code.md`. This file and `models.md` win where they differ. Agent names and slash commands have no `pstack:` prefix. |

## Model roles

In Claude Code, `models.md` assigns native agent roles. `apply` renders `agents/*.md` as `~/.codex/agents/*.toml`: `poteto-agent` builds, `judge` judges, and `senior-reviewer` reviews. In Codex, use these when the harness exposes them; seats inherit the session model unless configured otherwise. Do not claim model diversity. Follow session delegation rules. A subagent's output is a lead: open the code it cites before a finding becomes yours.

## Where Kolin's rules win

The global policy and the repo's `AGENTS.md` win every conflict with pstack. This adapter adds only how they land on pstack's own steps:

- **Autonomy.** pstack lets external actions (team chat, tickets, evals) run without asking. Here they need Kolin's yes (policy, Approvals). Opening a PR acts without asking in pstack. Shipping, Autopilot and Babysit `drive` merge nothing without an explicit ask (policy, Approvals). `autopilot-full` is not used.
- **PR title and body** use the repo's template. Where the repo has none, start from `pr-body <base> --feature <name>=<paths>` (policy, Pull requests) in place of pstack's Why, Scope and Tradeoffs.
- **Tests** in `tdd`, Refactoring step 1 and the multi-phase plan's unit box follow the policy's Done. A new test only for a named behavior a caller relies on. A unit box may read "No test: <why>". No snapshot. Delete a characterization pin that a kept test duplicates. No sibling-coverage sweep.
- **Write flows.** Before Feature or Bug fix builds a flow that takes a lock, claim, key or queue, or retries an outside write, write its event orders in the plan: a retry, a crash between two steps, two writers at once, a late answer from the outside system, and what each must leave behind (policy, Approvals). Where a repo model skill covers the files, extend the model and run it before the build; its result is the unit's first `Ran:` line.
- **Review rounds.** Follow policy (Pull requests) and `models.md` (Reviewer): one fresh-context review, then one fix-delta re-check. When the re-check brings a new high finding, stop reviewing and stop patching, because the design is unsettled. Apply `principle-attack-the-premise`, return to the flow or the plan, and tell Kolin.
- **Comments.** No comment survives except a lint directive with `-- <reason>`.
- **Builder brief.** poteto-mode now tells kickoffs to read its path and `worker.md` first. Here the brief names the files and the done check, quotes any principle the unit depends on, and the builder reads neither. For a build with a blueprint, the brief also quotes the blueprint's owner file for each state and decision the unit touches, and the builder writes that state nowhere else. Where `worker.md` differs (ready-for-review PRs, no questions, its PR body), the policy wins.
- **Reply style.** Keep pstack's Writing the reply rules. An explain, how, or walk-through follows `teach`: the active output style wins over `teach`'s diagram: plain words first, a flow as a short numbered list, no ASCII art, no table unless asked, offer an explainer page in one line and build it only after a yes. State the principles that changed a decision in one line, not a section.

## Own skills

`structure-review` is the structure read of a blueprint build (`models.md`, Size) and the answer when Kolin asks for a harsh structure or thermo review. It replaces cursor-team-kit's `thermo-nuclear-code-quality-review`, which stays vendored and locked.

## Verify the setup

`kolin-skills check` proves wiring, not behavior. For a routing or model-role change, use `poteto-mode/playbooks/eval.md` with organic tasks and transcript evidence.

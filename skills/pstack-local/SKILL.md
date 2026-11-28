---
name: pstack-local
description: Map pstack Cursor tool names to Claude Code, Codex, Cursor, Grok Bot and Antigravity. Use when a pstack skill names a Cursor tool.
---

# pstack tools on this machine

Vendor: `~/.agents/vendor/cursor-plugins/`. Auto: architect, how, statechart, thermo-nuclear-code-quality-review. Other pstack/team-kit skills: read in that tree (`pstack/skills/<name>/SKILL.md` or `cursor-team-kit/skills/<name>/SKILL.md`). `structure-review` is the blueprint/slice structure read.

| pstack | Here |
|---|---|
| `Task` `generalPurpose` | Claude `Agent` (`general-purpose`). Codex spawned agent. Antigravity `invoke_subagent`. |
| `poteto-agent` | `poteto-agent` |
| readonly / Opus judgment | `senior-reviewer` |
| `AskQuestion` | harness user-input tool |
| todolist | harness todo list |
| Browser / UI proof | `agent-browser`, `agent-desktop`, `control-ui`, `control-cli` |
| Origin | `gh` |
| `.cursor/skills/` output | `.agents/skills/<name>/SKILL.md` |

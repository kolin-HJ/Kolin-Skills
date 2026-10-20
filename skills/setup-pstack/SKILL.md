---
name: setup-pstack
description: Write ~/.claude/pstack-models.md, pstack's per-role model file. Records the per-role split (Sonnet for implementers, Opus for judgment and the hardest work, Haiku or Sonnet for lookups), the reasoning budget, and the panel sizes. Use for /setup-pstack, "configure pstack models", "pstack budget", or changing pstack's model choices.
---

# Setup pstack

Write `~/.claude/pstack-models.md`, the file pstack skills read before they spawn subagents to set the model per role.

## Steps

### 1. Detect available models

Valid values are `claude-sonnet-5-5`, `claude-opus-5-5`, `claude-haiku-4-5`, `inherit-parent`, and `auto`. Confirm a CLI id works before writing it (`claude -p 'say ok' --model <id> --output-format json`, then check `modelUsage`). The `Agent` tool's `model` field only takes the aliases `sonnet`, `opus`, `haiku` (and `fable`): `opus` resolves to `claude-opus-5-5` and `haiku` to `claude-haiku-4-5`, but `sonnet` resolves to the older `claude-sonnet-5`. To get `claude-sonnet-5-5` in a subagent, omit `model` from a parent running on `claude-sonnet-5-5` (the `~/.claude/settings.json` default), or run the role headless with `claude -p ... --model claude-sonnet-5-5`. `inherit-parent` and `auto` mean: omit `model`.

### 2. Load current state

The default role-to-model mapping is the file shape shown in step 5 below. If `~/.claude/pstack-models.md` already exists, read it and treat its `# budget` line and its role values as the current choices. Otherwise start from those defaults. A line whose role is not in step 5, such as `how critics`, is from a retired role. Drop it.

### 3. Budget and confirm the roles

Ask for a budget: `large — xhigh reasoning`, `medium — high reasoning` (default), or `small — medium reasoning`. Never use `max`. The budget is the `--effort` passed to headless runs and the `effortLevel` default; it is not forced to medium. Show every role with its model and list each line step 2 dropped. Ask whether to accept as-is or change specific roles. For panel roles (arena runners, architect runners, interrogate reviewers) the value is a list and one subagent runs per entry, so the list length sets the count. Offer three per panel by default. Prefer AskUserQuestion over free text.

### 4. Validate

Every value written must be one of the valid values in step 1. Never write an id you have not confirmed works, and never write `max` as the budget.

### 5. Write the file

Write `~/.claude/pstack-models.md` with the `# budget` line, and one line per role, using the same labels poteto-mode uses. Overwrite the whole file so re-runs stay idempotent. Shape:

```
# pstack model configuration. One line per role. Delete a line to fall back to the skill default.
# Values are Claude CLI ids. Agent tool mapping: claude-opus-5-5 -> `opus`; claude-haiku-4-5 -> `haiku`;
# claude-sonnet-5-5 -> omit `model` when the parent runs claude-sonnet-5-5, else run headless with `--model claude-sonnet-5-5`
# (the `sonnet` alias is the older claude-sonnet-5). `inherit-parent` or `auto`: omit `model`.
# budget: medium (high). Never max.
feature, refactoring: claude-sonnet-5-5
bug-fix: claude-sonnet-5-5
perf-issue: claude-sonnet-5-5
hillclimb: claude-opus-5-5
judgment and prose: claude-opus-5-5
hardest tasks: claude-opus-5-5
billing, auth, data changes: claude-opus-5-5
how explorer: claude-haiku-4-5
how explainer: claude-opus-5-5
why investigators: claude-sonnet-5-5
why synthesizer: claude-opus-5-5
reflect tooling: claude-sonnet-5-5
reflect judgment, divergent, synthesizer: claude-opus-5-5
arena runners: claude-opus-5-5, claude-opus-5-5, claude-opus-5-5
arena cross-judge pool: claude-opus-5-5
swarm workers: claude-sonnet-5-5
architect runners: claude-opus-5-5, claude-opus-5-5, claude-opus-5-5
interrogate reviewers: claude-opus-5-5, claude-opus-5-5, claude-opus-5-5
```

### 6. Confirm

Tell the user the file was written and that skills read it the next time they spawn subagents. Re-running this skill updates it.

### 7. Offer a verification skill (optional)

Check whether the project has a way to drive the real app for proof (a `verify-*` skill, or an existing harness). If not, offer once: "want a project-local verification skill, so agents can drive the app the way a user does and prove changes work? I can generate one with /create-verification-skill." On yes, invoke `/create-verification-skill` (resolves wherever pstack is installed: project, user, or plugin). On no, move on without pushing.

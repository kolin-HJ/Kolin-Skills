<div align="center">

# Kolin-Skills

**One rule book for every coding agent you use.**

Claude Code, Codex, Cursor and Grok follow the same rules, skills and guardrails, from one repo.

![Claude Code](https://img.shields.io/badge/Claude_Code-d97757)
![Codex](https://img.shields.io/badge/Codex-10a37f)
![Cursor](https://img.shields.io/badge/Cursor-000000)
![Grok](https://img.shields.io/badge/Grok-555555)
![Gate](https://img.shields.io/badge/gate-pre--push_%2B_CI-blue)
![check](https://github.com/kolin-HJ/Kolin-Skills/actions/workflows/check.yml/badge.svg)

[What](#what-it-is) · [Why](#why-use-it) · [How it works](#how-it-works) · [Install](#install) · [For agents](#install-for-agents) · [Updates](#updates-by-environment) · [Quality](#what-quality-means) · [Daily use](#working-with-it) · [Skills](#skills)

</div>

## What it is

One repo holds your agent setup. Each tool's home folder only links to it, so one edit reaches every tool.

```mermaid
flowchart TB
  repo["📦 Kolin-Skills<br/>policy · skills · subagents · hooks · gate"]
  repo --> cc["Claude Code<br/>everything"]
  repo --> cx["Codex<br/>policy, skills, subagents, most hooks"]
  repo --> cu["Cursor<br/>policy rule, skills, lint hook"]
  repo --> gk["Grok<br/>policy, skills"]
```

| Part | What it gives you |
|---|---|
| 📜 **Policy** | A short rule book on top of pstack: only what a model gets wrong untold — approvals, code preferences, security, done, PR format |
| 🧰 **Skills** | pstack is the method. Own skills add knowledge it lacks (the repo standard, UI craft, local Supabase) and the full-stop and full-send permissions |
| 🤖 **Subagents** | A builder, a reviewer and a sweeper. The builder never reviews its own code |
| 🛡️ **Guardrails** | Hooks that block a risky action before it runs |
| ✅ **Gate** | `kolin-skills check`, run on pre-commit (file length), pre-push, and Linux CI |

## Why use it

| Without it | With it |
|---|---|
| Each tool has its own rules file | One rule book in every tool |
| A rule in a prompt is only a request | A hook blocks the action, and the gate fails the push |
| The agent reviews its own code | A fresh reviewer reads every large or risky diff |
| "Done" means it compiles | "Done" means proven on the real artifact |
| The same mistake comes back | A mistake that costs time twice, or once for security, data loss or an irreversible action, becomes a lint rule, a test or a type |

## How it works

Most tasks run in the main session. A large task with independent units adds builders.

```mermaid
flowchart LR
  ask([🙋 You ask]) --> work[🔨 Work<br/>main session]
  work -. large, independent units .-> build[🔨 Builders<br/>Sonnet]
  build -.-> work
  work --> review[🔍 Review<br/>fresh Opus]
  review -- findings --> work
  review --> gate[✅ Gate<br/>pre-push]
  gate --> pr[📬 PR]
  pr --> merge([👍 You merge])
```

In Claude Code, builders run on Sonnet and the reviewer on Opus. Codex runs all three subagents on its default model.

**Guardrails block. They do not ask.** The blocked agent gets the reason and the fix.

| 🚫 Blocked | Why |
|---|---|
| Push to `main`, `master`, `staging`, `sandbox`; force push; `--no-verify`; auto-merge | Protected branches change only through a PR you merge. An agent may create a missing one with `gh api repos/<owner>/<repo>/git/refs -f ref=refs/heads/staging -f sha=<sha>`; GitHub rejects it if the branch exists. Moving or deleting one through the API is blocked |
| Reading a `.env` file | Secrets stay out of the context |
| Foreground sleep loops, long curl retries, Docker databases | Agents use background jobs, Monitor and the native Supabase CLI instead |

Claude Code runs every guard. Codex runs the git guard, the `.env` guard (shell commands only), the lint hook and compaction context. Cursor runs only the lint hook. Grok runs no hooks.

## Install

You need **git**, **`jq`**, **Python ≥ 3.9** and **Node ≥ 22.20**. Without `jq`, the git guard blocks every shell command. The repo is public, so the clone needs no credentials.

```sh
git clone https://github.com/kolin-HJ/Kolin-Skills.git ~/Kolin-Skills
python3 ~/Kolin-Skills/bin/kolin-skills install
```

1. **Run `install` once.** It fetches the pinned third-party skills, links everything into each tool, runs `check` and puts `kolin-skills` in `~/.local/bin`.
2. **Open any agent in any repo.** There is nothing to start.
3. **Stay on `main`.** Updates are not the same on every tool. Use the matrix. Put a machine on current `main` with [`docs/stay-on-main.md`](docs/stay-on-main.md). When an update moves a third-party pin, run `kolin-skills upstream`.
4. **Put your own rules in each project's `AGENTS.md`.** Do not edit the clone, because a local edit stops the updates.

With Node older than 22.20, `install` skips the third-party skills and says so. Offline, it links what it has and exits 1.

### Updates by environment

| Environment | Auto `pull` at session start | What is live after `apply` on current `main` |
|---|---|---|
| Claude Code | Yes (`claude/settings.json` SessionStart) | Policy, skills, subagents, hooks |
| Codex | Yes (`codex/hooks.json` SessionStart) | Policy, skills, subagents, most hooks |
| Cursor | No. `cursor/hooks.json` is `postToolUse` lint only | Policy rule, skills, lint hook via `~/.agents` and `~/.cursor` |
| Grok | No. Grok has no hooks | Policy and skills |

A clone with local edits also skips `pull`. Cursor and Grok then keep whatever `apply` last wrote, even if `origin/main` moved.

T3Bot owns apply verification on T3 DEVS and the home Mac. Box re-apply and hj-supply-chain unvendor are follow-ons ([`docs/consumer-drift.md`](docs/consumer-drift.md)).

## Install (for agents)

Given this repo's URL and "install this", run these steps in order. Stop at the first failure and read its message.

```sh
for tool in git jq python3 node; do command -v "$tool" >/dev/null || echo "missing: $tool"; done
python3 -c 'import sys; assert sys.version_info >= (3, 9), sys.version'
node -e 'const [major, minor] = process.versions.node.split(".").map(Number); if (major < 22 || (major === 22 && minor < 20)) process.exit(1)'
CLONE="${KOLIN_SKILLS_DIR:-$HOME/Kolin-Skills}"
git clone https://github.com/kolin-HJ/Kolin-Skills.git "$CLONE"
python3 "$CLONE/bin/kolin-skills" install
export PATH="$HOME/.local/bin:$PATH"
kolin-skills check --quick
```

Keep the clone where it is, because the home folders link into it. `check --quick` takes seconds and passes only when the links resolve, the hooks and policy are wired, and `poteto-mode`, `how`, `architect`, `tdd`, `interrogate`, `correct` and the `principle-*` skills have no `disable-model-invocation` line. Then start a new session: a running agent keeps the skills and policy it loaded at start.

## What quality means

> **The most value for the least code**, at the same bar for correctness, tests and proof.

Each lesson goes into the strongest layer that can hold it:

```
 strongest ─▶  1. Code that makes the bad state impossible (a type, one paved path)
               2. A gate: a lint rule or test, with a count that can only fall
               3. A skill or AGENTS.md, for judgment no tool can check
 weakest ───▶  4. Review
```

The full bar: [`policy/AGENTS.md`](policy/AGENTS.md) and [`skills/repo-standard/SKILL.md`](skills/repo-standard/SKILL.md). The method is pstack's `poteto-mode`.

## Working with it

Ask for the outcome in plain words, such as "fix the redirect bug on login". The agent picks the skill, does the reversible work alone and waits for you only at the points that matter.

| 🤖 The agent does it alone | 🙋 It waits for your yes |
|---|---|
| Read, edit, test, review, fix | A multi-phase plan, before the build |
| Commit, push and open a PR on a work branch | A new data structure or system flow |
| | A merge, a deploy, a migration |
| | Money, secrets, messages to people |

You can also call any skill by name, such as `/full-stop`.

## Skills

Each skill starts in one of two ways:

| | How it starts |
|---|---|
| 💬 **On match** | The agent loads it when your request matches its description |
| ⌨️ **You only** | Only you can start it, by phrase or slash command. In Claude Code, the agent cannot start it by itself |
| 📜 **By policy** | The policy sends matching work to it, and you can also type its slash command |

**Core**

| Skill | Starts | What it does |
|---|---|---|
| `poteto-mode` (pstack) | 📜 | The method: playbooks for feature, bug fix, refactor, review, babysit and shipping. The policy routes code work beyond a one-line change to it |
| `pstack-local` | 💬 | Maps pstack onto each tool when a pstack skill runs: tools, paths, model roles and where the policy wins |
| `repo-standard` | 💬 | What a finished repo looks like: layout and budgets, quality bars, gate design, the UI bar, and the checklist to audit a repo against it |

**Process**

| Skill | Starts | Say | What it does |
|---|---|---|---|
| `full-stop` | ⌨️ | "full stop" or `/full-stop` | Runs the pstack playbooks to a PR the watcher reports `READY`, inside a fixed permission scope. You merge |
| `full-send` | ⌨️ | "full send" or `/full-send` | Does all of `full-stop`, then merges that one PR after a 4-item merge checklist. It never deploys |
| `council` | ⌨️ | "council" or `/council` | Gets a review from three models on three providers, in rounds, until they agree. Scores go in the PR body |
| `modernize` | 💬 | "Modernize this PR", "take over #42" | Decides if an old PR should still land (modernize, rework or close), then updates it and keeps the authors' credit |
| `loop-refactor-to-pstack` | ⌨️ | `/loop-refactor-to-pstack` | Refactors a whole repo to the standard over many sessions on one branch |

**UI craft**

| Skill | Starts | Say | What it does |
|---|---|---|---|
| `break-ui` | 💬 | "Stress-test this table" | Feeds worst-case data to a UI, fixes the clear breaks and reports the rest |
| `emil-design-eng` | 💬 | "Make this drawer feel polished" | Motion and polish: easing, springs, transitions, gestures |
| `mobile-native` | 💬 | "It feels wrong on my phone" | Fixes the tells that make a web app feel like a website on a phone |

**Utilities**

| Skill | Starts | Say | What it does |
|---|---|---|---|
| `local-supabase` | 💬 | "Start a local database" | Runs a local Supabase or Postgres per checkout, never in Docker |
| `user-notes` | 💬 | "Write release notes for PR 42" | Writes short release notes for the people who use the app |
| `explainer` | 💬 | "Explain this PR visually" | Builds a one-page HTML explainer. Only when you ask or say yes to the offer |

**Subagents.** The main agent spawns these. You do not call them.

| Agent | Model | Spawned when |
|---|---|---|
| `poteto-agent` | Sonnet | A large, independent unit of code can run in parallel with other work |
| `senior-reviewer` | Opus | Before a PR over 150 changed lines or one that touches schema, auth, access, money or a migration; also the seats of pstack's `interrogate` |
| `haiku-worker` | Haiku | A mechanical sweep: a rename, a codemod, a read-only search |

<details>
<summary><b>Third-party skills that install also adds</b></summary>

| Source | Skills | Starts |
|---|---|---|
| [pstack](https://github.com/cursor/plugins) | `how`, `architect`, `interrogate`, `swarm`, `arena`, `tdd`, `unslop`, `technical-writing`, `no-comments`, `correct` and the `principle-*` skills | The agent reads one when a task or playbook needs it. You can type `/poteto-mode`, `/how` and the rest |
| cursor-team-kit | `deslop`, `control-ui`, `control-cli` | 💬 To clean AI slop out of code, or to drive a UI or CLI |
| cursor-team-kit | `thermo-nuclear-code-quality-review` | The agent reads it for the diff pass before review, or when you ask for a harsh structure review |
| `npx skills` | `find-skills` | ⌨️ |

</details>

## Reference

<details>
<summary><b>Layout</b></summary>

```
policy/AGENTS.md             global policy → ~/.claude/CLAUDE.md, ~/.codex/AGENTS.md, ~/.grok/AGENTS.md
policy/compact-instructions.md   what a compaction summary keeps
skills/                      own skills, linked flat into ~/.agents/skills, ~/.claude/skills, ~/.cursor/skills
  pstack-local/models.md     which model plans, builds and reviews
agents/                      subagents; senior-reviewer.md holds the review bar
hooks/                       guards and lint, run in place from the repo
claude/                      managed settings keys, status line, output style (ste-visual)
codex/, cursor/              hook config and the Cursor policy rule
.githooks/                   pre-commit runs check --files; pre-push runs check; post-merge, post-checkout, post-rewrite run apply
upstream/                    pstack and cursor-team-kit (vendor.json), npx skills (skills.json)
docs/                        stay-on-main, consumer-drift
tests/                       installer, hook and repo-rule tests, run by check
```

Edits to existing files are live at once. A new, renamed or deleted skill or agent needs `apply`. Claude Code and Codex run `apply` through `pull` at session start. After `git pull`, `checkout` and `rebase` in this clone, the git hooks run `apply`. Cursor and Grok have no session `pull`; they follow links from the last `apply`. `apply` is idempotent, and a real file it replaces goes to `~/.kolin-skills/backup/`.

Project rules live in each project's own `AGENTS.md`, never here. Not managed: credentials, Codex `config.toml`, Cursor `mcp.json`, and `permissions` and `autoMode` in `~/.claude/settings.json`.

</details>

<details>
<summary><b>Commands</b></summary>

| Command | What it does |
|---|---|
| `kolin-skills install` | First run on a machine: `upstream`, `apply`, then `check` |
| `kolin-skills apply` | Links the repo into home. `--check` reports drift only. `--adopt` moves home to this checkout. `--if-wired` runs only when home is wired here |
| `kolin-skills pull` | Fetches `origin/main`, fast-forwards when it safely can, then applies. Runs at each Claude Code and Codex session start. Not Cursor or Grok. Prints `kolin-skills: stale setup` when it cannot update. Machines without those hooks: [`docs/stay-on-main.md`](docs/stay-on-main.md) |
| `kolin-skills upstream` | Installs third-party skills at pinned commits. `--bump` moves the pins |
| `kolin-skills import <path>` | Moves a skill or agent made in home into the repo |
| `kolin-skills stacks` | Lists running native Supabase stacks. `--stop` stops the idle ones. `--notice` runs at session start and prints only when idle stacks exist |
| `kolin-skills check` | The gate: drift, strays, pins, spend caps, size budgets, 1,000-line files, tools, tests, comments. `--files` is only the line limit. `--quick` checks only home, in seconds: links resolve, hooks and policy are wired, the self-invoking pstack skills carry no model lock. Prints `feature-budget` and does not fail on it. In a worktree it skips home drift. In CI it skips home and vendor. With a path, it only runs `check-drift` |
| `kolin-skills check-drift <path>` | Fails when that tree's vendored pstack SOURCE/rev or synced `senior-reviewer` differs from this repo. What it compares, and the hj-supply-chain / box follow-ups: [`docs/consumer-drift.md`](docs/consumer-drift.md) |
| `context-audit` | Lists skills, tools and MCP servers that cost context and went unused for 30 days. `--sessions [DAYS]` reports token use, hook blocks and failing tools across recent transcripts |
| `pr-body <base>` | Prints a PR body skeleton with the policy's sections and a diff table grouped into code, tests and docs |
| `diff-audit <base>` | Flags reward hacks and slop in a diff (skipped tests, comments, new dependencies) and lists every addition for the value check |
| `feature-budget` | Counts files and lines under `features/<name>/` against the plan (defaults: read 5/800, edit 7/1,200, write 12/2,500, tests excluded). Lists under-40-line single-importer files except a library wrapper. Report-only in `kolin-skills check`. Over budget fails review; over twice the budget stops the wave (`repo-standard`, Layout) |

</details>

<details>
<summary><b>Hooks</b></summary>

| Hook | Tools | Does |
|---|---|---|
| `hooks/gate/block-forbidden-git.sh` | Claude Code, Codex | Blocks protected-branch pushes and merges, force push, `--no-verify`, auto-merge, edits to hook files |
| `hooks/block-env-reads.py` | Claude Code, Codex | Blocks `.env` reads. `.env.example` stays readable |
| `hooks/agent-default-model.py` | Claude Code | Blocks editing subagents spawned with `isolation: "worktree"`. Denies Opus on an editing subagent and names `Plan`. Runs `senior-reviewer` on Opus when a repo copy pins lower |
| `hooks/bash-guard.py` | Claude Code | Guards each Bash command: blocks polling loops, Docker databases and long curl retries, strips or rewrites filters on gate output and never blocks them, and queues heavy jobs into 3 shared slots |
| `hooks/context-budget.py` | Claude Code | In a subagent, warns at 200,000 context tokens to wrap up and blocks at 260,000 until it reports |
| `hooks/mcp-access.py` | Claude Code | When an MCP tool fails with an access error, tells the agent this account lacks the connector, to stop calling it and to use the CLI |
| `hooks/lint-changed-lines.py` | All but Grok | Lints the JS and TS lines the agent just changed |
| `hooks/compact-context.py` | Claude Code, Codex | Keeps the branch and changed files through compaction |
| `hooks/keep-awake.py` | Claude Code | Holds `caffeinate` from each prompt or subagent spawn, so a long turn does not let the Mac sleep |
| `hooks/heavy-slot.py` | Claude Code (through `bash-guard`) | Gives heavy jobs one of 3 shared slots and keeps the Mac awake while each runs |

</details>

## Credits

The method is [pstack](https://github.com/cursor/plugins) by Lauren Tan, with skills from Cursor's cursor-team-kit. Both are vendored at pinned commits in `upstream/vendor.json`, never copied. `emil-design-eng` follows Emil Kowalski's UI craft. `council`, `modernize` and the babysit and review-scope rules in `full-stop` adapt Theo Browne's [tstack](https://github.com/t3dotgg/tstack).

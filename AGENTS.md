# Kolin-Skills

This repo is the source of truth for Kolin's agent setup on every machine: the global policy, own skills, subagents, hooks and harness settings. Home directories hold only links to it or files rendered from it. `README.md` has the layout and the bootstrap.

## Rules

- Never create a skill, agent, command or rule straight in a home folder. `apply` reports it, `check` fails on it, and `kolin-skills import <path>` moves it here.
- Edit files here, never the copy in home. A file in home that `kolin-skills apply` links or renders is replaced on the next apply. A replaced real file goes to `~/.kolin-skills/backup/`.
- One CLI owns the wiring: `bin/kolin-skills`. A new harness path goes into its `LINKS`, `MERGED_JSON` or `RENDERED` table, not into a new script. A new harness folder for skills, agents, commands or rules goes into `WATCHED_HOMES`. A tool that installs into a watched folder by itself goes into `OTHER_INSTALLERS`.
- Hook commands and machine paths use `{{HOME}}` and `{{REPO}}` in the templates under `claude/`, `codex/` and `cursor/`. Never commit a literal home path.
- A hook entry is managed when its command names a path in this repo. `apply` replaces managed entries and keeps every other entry, such as herdr's.
- `claude/settings.json` holds only the keys this repo manages. Machine-specific keys (`permissions`, `autoMode`) stay in `~/.claude/settings.json`.
- Third-party skills and agents are not copied here. pstack and cursor-team-kit are listed in `upstream/vendor.json`, and `npx skills` packages in `upstream/skills.json`. `kolin-skills upstream` installs them. The one copy is `skills/reverse-engineer-anything` (REA, MIT), kept so it can carry `disable-model-invocation: true`. Refresh it from REA's installed skill and keep that line.
- No secret goes into this repo: no token, `auth.json`, MCP credential or `.env` value.
- Clone plus `install` must keep working on any machine, macOS or Linux: no machine path, no manual step, no tool missing from the README prerequisites.
- Nothing project-specific goes here. Project rules live in that project's `AGENTS.md`.

## Add something

| To add | Put it in | Then |
|---|---|---|
| A skill | `skills/<name>/SKILL.md` | Run `kolin-skills apply`, or start a session. It links into `~/.agents/skills`, `~/.claude/skills` and `~/.cursor/skills`. |
| A subagent | `agents/<name>.md` | `apply` links it for Claude and writes the Codex `.toml` mirror. |
| A hook | `hooks/<name>.py`, plus an entry in `claude/settings.json` or `codex/hooks.json` | Add a case to `tests/test_hooks.py`. |
| A third-party skill | `upstream/skills.json` | Run `kolin-skills upstream`. |
| A skill or agent another tool wrote into home (`skill-creator`, `npx skills add`) | Nowhere by hand | Run `kolin-skills import <path>`. |

## Gate

`kolin-skills check` is the gate, and `.githooks/pre-push` runs it. There is no CI. It fails when home has drifted from the repo, a watched home folder holds an entry the repo does not own, a skill in `upstream/skills.json` is not installed, a spend cap is off, a required tool is missing, the policy or `skills/pstack-local/SKILL.md` is over its size budget, or a test fails. It also fails on a comment in code and on a skill missing from the README index. Run it before you call work done.

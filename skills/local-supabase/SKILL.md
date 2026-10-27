---
name: local-supabase
description: Run a local Supabase or Postgres database for development, tests or an agent, in any repo. One project per checkout in the Supabase CLI's native runtime, never Docker or docker compose. Use when you start, seed, reset or connect to a local database, set one up in a repo, or meet a docker-compose Postgres or a fixed localhost:5432 URL.
---

# Local Supabase

Local Supabase and Postgres run as one project per checkout in the Supabase CLI's native runtime, never in Docker or `docker compose`. Each worktree and branch gets its own database on its own ports, so parallel agents never share data. Sources: the [Supabase blog post](https://supabase.com/blog/local-supabase-project-per-agent-with-or-without-docker), [Running multiple local projects](https://supabase.com/docs/guides/local-development/running-multiple-local-projects) and [Docker and native runtimes](https://supabase.com/docs/guides/local-development/docker-and-native-runtimes). The stack commands are experimental, so read those guides again when a flag fails.

## Set up a repo

1. Pin the CLI, v2.119.0 or later, as the repo's `supabase` dev dependency. Run it as `pnpm exec supabase` or `node_modules/.bin/supabase`.
2. Commit `supabase/config.toml` with `[experimental] stack = true`, `db.major_version` equal to production's (15 or 17), and no `port` keys. Remove the ports before the first start, because a stack keeps the ports it was created with. A new app runs `SUPABASE_EXPERIMENTAL_STACK=1 supabase init`, which writes no ports.
3. Replace every fixed local URL (`localhost:5432`, `54322`) with the URL read from `supabase status --output-format json` (`env.DB_URL`). User and password are `postgres`.
4. Delete the repo's Docker Postgres (`docker-compose.yml` service, docs, scripts) in the same change, and point the verification skill's launch at the stack.

A repo that still runs local Postgres in Docker moves to this in its own change.

## Use it

```bash
supabase start --runtime native --output-format json   # idempotent; prints env.DB_URL and keys
supabase status --output-format json                   # no env.DB_URL means the stack is stopped
supabase stop                                          # keeps data and ports
supabase stack list                                    # every stack on the machine
supabase stack destroy --yes                           # deletes this checkout's data
```

- Postgres starts at once. Other services start on their first request and stop after 60 s idle. `--eager` starts all of them.
- A stack's identity is its checkout path and git branch. A new worktree, a branch switch or a moved directory starts an empty stack. Seed it from another local stack, never from production.
- The `db`, `migration`, `gen` and `test` commands route to the stack. They cannot target a `--stack` name.
- Stop your stack (`supabase stop`) when your unit's proof is done. macOS allows 32 shared-memory segments (`kern.sysv.shmmni`), each running stack holds some, and a new start fails with `could not create shared memory segment` when they run out. `kolin-skills stacks --stop` stops every idle stack.
- Before you remove a worktree, run `supabase stack destroy --yes` in it. Stack data lives in `~/.supabase/stacks/<id>/`, and the shared download cache in `~/.supabase/cache/stack`.
- Native runs on macOS 14 or later on Apple silicon and Linux with glibc 2.35 or later, not as `root`. A cold first start downloads about 360 MB.
- The docs recommend Docker when several stacks share one machine, because native stacks share the process table. The native runtime is still the rule here, so agents never need a container engine.

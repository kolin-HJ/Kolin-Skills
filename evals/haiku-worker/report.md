# Haiku worker vs Sonnet worker on recipe lanes

Run 2026-10-07. One run per cell: four cases, two workers, one Opus 5.5 advisor per run. Method and scripts are in `README.md`. Every final diff, score and the agent-id map are in `runs/`.

## Verdict

On these four lanes the Haiku worker matched the Sonnet worker's final quality. It needed the same number of advisor rounds and cost 27 to 55% less in total. The worker itself costs 31 to 47 times less: $0.006 to $0.013 against $0.28 to $0.43 per lane (measured). The advisor's review is 97 to 99% of a Haiku lane's total cost (measured), so the review is now the cost to cut, not the worker.

Haiku had one failure Sonnet did not: on `modal-shell` round 1 it ran its commands in the parent session's worktree, not the run's worktree, and stopped on two false blockers. That is a brief and harness problem with a direct fix (see Follow-ups). Sonnet had one failure Haiku did not: on `adr-sync` round 1 it invented a redirect target that does not exist, and flagged it as a guess.

```
                  worker $    advisor $   total $    rounds   final gates
renumber   haiku   0.006       0.544       0.550       1        pass
           sonnet  0.283       0.530       0.813       1        pass
adr-sync   haiku   0.011       0.636       0.647       2        pass
           sonnet  0.357       0.601       0.959       2        pass
dead-exp   haiku   0.011       0.387       0.398       1        pass
           sonnet  0.344       0.542       0.886       1        pass
modal-sh   haiku   0.013       0.771       0.784       2        pass
           sonnet  0.431       0.642       1.073       2        pass
```

## Per case

"Lines off" counts changed lines that differ from the merged commit's diff, in either direction (`score.mjs`). A difference is not always a defect: the merged commits are one valid answer, not the only one.

### renumber (rename, `6651e592`)

| | Haiku | Sonnet |
|---|---|---|
| Gates (`agents-refs`, `feature-map`) | pass | pass |
| Hunks / lines off vs merged | 0 / 0 | 0 / 0 |
| Trap: five `0163` hits mean the Demand tab ADR | left, all five named | left, all five named |
| Trap: migration id in TypeScript | correctly no edit, explained | correctly no edit |
| Rounds | 1 | 1 |
| Worker / advisor / total tokens | 221K / 519K / 740K | 412K / 504K / 917K |
| Total $ | 0.550 | 0.813 |

Both diffs are identical to the merged commit. Haiku also named a false-positive census hit in a CSV float.

### adr-sync (doc sync, `2938f742`)

| | Haiku | Sonnet |
|---|---|---|
| Gate (`agents-refs`) | pass | pass |
| Lines off vs merged (final) | 14 extra / 7 missing | 10 extra / 7 missing |
| Trap: "as it was" section in 0054 | left | left |
| Trap: out-of-list files 0051, 0071 | not edited | not edited |
| Round 1 defects | skipped one present-tense census hit (0160:23) and flagged its own miss; declined to state two facts the brief did not give | invented "redirects to `/demand/demand-plan`" (flagged as a guess); left half of the 0130 bullet stale |
| Rounds | 2 | 2 |
| Worker / advisor / total tokens | 476K / 791K / 1,267K | 697K / 627K / 1,323K |
| Total $ | 0.647 | 0.959 |

The line counts are high for both because the advisor wrote the round-2 sentences, and both final diffs fix stale claims the merged commit kept: 0054:30 still said "Variant page", and 0130 still said "dropping that redirect" and that the capability key stays. Haiku's run also removed the 0160:70 "Variant list" example at its advisor's direction; the merged commit kept it, and the other advisor called it allowed history. That is advisor variance, not worker variance.

### dead-exports (codemod, `9d9740e1`)

| | Haiku | Sonnet |
|---|---|---|
| Gates (`deadcode`, `typecheck`, `comments`, vitest 115 tests, `oxfmt`) | pass | pass |
| Lines off vs merged | 1 / 1 | 1 / 1 |
| Trap: `formatDay` from `@/lib/dates` | untouched, callers listed | untouched |
| Trap: unrequested `tags` test rename | not made | not made |
| Rounds | 1 | 1 |
| Worker / advisor / total tokens | 441K / 526K / 966K | 675K / 510K / 1,185K |
| Total $ | 0.398 | 0.886 |

The two diffs are the same. The one line off: both deleted the unused `MatchedField` type, where the merged commit only dropped its `export`. Nothing references it, so the brief's rule ("delete if nothing uses it") makes deletion correct.

### modal-shell (codemod with stops, `c2c37999`)

| | Haiku | Sonnet |
|---|---|---|
| Gates (`rules`, `typecheck`, `comments`, `oxfmt`) | pass | pass |
| Lines off vs merged (final) | 5 / 6 | 4 / 4 |
| Trap: `save-preview-modal` must stop | stopped (round 2) | stopped (round 1) |
| Trap: `global-search-modal` must stop | stopped (round 2) | stopped (round 1) |
| Round 1 defect | worked in the parent worktree; reported "no `apps/web`" and "no `rules-baseline.json`", both false; read no candidate | stopped on all four, including the two that fit, over width and footer-padding differences |
| Rounds | 2 | 2 |
| Worker / advisor / total tokens | 591K / 1,138K / 1,729K | 991K / 805K / 1,795K |
| Total $ | 0.784 | 1.073 |

The remaining line differences are the footer markup and a subtitle margin, both dictated by the advisors and different between them. Neither converted modal was rendered (not verified).

## Recommendation

Send to Haiku:

- Renames and renumbers driven by a `git grep` census, with "leave these" rules in the brief.
- Codemods that a deterministic gate drives and checks: `deadcode`, `rules` baselines, `typecheck`. Both workers produced the same diff here.
- Codemods with stop conditions, once the brief pins the working directory (Follow-up 1). Haiku's stop judgment in round 2 was right on all four candidates.

Keep with the advisor or Sonnet:

- Doc sync that needs facts beyond the brief or a present-versus-past judgment per sentence. Neither worker got it right in one round. The advisor wrote the final sentences in both runs, at $0.60 to $0.64 of review. For a three-file doc edit, the advisor editing directly is cheaper than brief, worker, review, revise, review.
- Everything already excluded: design, review, planner numbers, schema, access, NetSuite and BigQuery.

Cut the review cost next. A Haiku lane spends $0.39 to $0.77 on Opus review against about $0.01 on the worker. Each advisor read 500K to 1.1M tokens, mostly a general-purpose system prompt of about 80K re-read per request. A dedicated advisor agent with a short brief, or a Sonnet advisor for lanes whose gates are deterministic, is the next experiment.

## Limits

- One run per cell. The senior-reviewer eval showed same-cell runs differing by three points, so read small gaps as noise. Here the quality gaps are qualitative (one failure each) and the cost gap is large and consistent.
- The Sonnet arm ran as a general-purpose agent told to follow `haiku-worker.md`. Its system prompt is larger (max prompt 86K to 99K against Haiku's 34K to 58K), which inflates Sonnet's cost somewhat. A dedicated `sonnet-worker` definition would narrow the cost gap, but not close a 30-times-plus price difference.
- Cost is at API list price from `usage.mjs`: Opus 5.5 $4 / $20, Sonnet 5.5 $2 / $10, cache reads $0.20; Haiku 5.5 $0.10 / $0.50 up to 100K prompt tokens and $0.50 / $2.50 above. Cache writes are 1.25 times input. The Haiku cache-read rate ($0.01, $0.05 above 100K) is inferred as 0.1 times input; the skill lists no rate. No Haiku request crossed 100K, so the long-context tier never applied.
- The main thread's relay messages are not counted. They were the same size for both arms.
- `expected/adr-sync.patch` is a weak oracle: the merged commit left stale claims that both workers' final diffs fixed.

## Follow-ups

1. `haiku-worker.md`: add "Run every command from the worktree your brief names, and read that worktree's `AGENTS.md`." Haiku read `AGENTS.md` from the session's working directory, then ran its commands there. Rerun `modal-shell` after the change to confirm.
2. Add a `sonnet-worker` agent definition with the same body, so the Sonnet arm runs with the same harness and tool set.
3. Rerun all four cases with a Sonnet advisor and compare verdicts with these Opus verdicts.
4. The hj-supply-chain ADRs still carry two stale claims both advisors found: 0130:113 says Top Down is "parked", and 0160:70 says comment threads key on literal paths, but `commentPage()` keys on page ids.

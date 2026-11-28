# Workflow templates

Keep each of these short. The policy is the rule. These are the shapes.

## One-page shape

Kolin approves this before code on non-trivial work. A build over about 10 files, or one that adds a lifecycle, is this shape as a blueprint. Spawn `structure-review` on the blueprint and first slice. The slice waits for a yes before builders copy.

```
Goal:
Greenfield ceiling (ignore what exists—optimal shape):
Benchmark to hill-climb on (metric + how we measure it):
Applies to (divisions/roles):
UX / visible behavior (if UI):
Types:
States (union or state machine):
Owner file per state/decision:
Module boundaries:
Files touched:
First slice:
Smallest version:
Cut list (left out, and why):
```

## Grill

Cap at 5 questions. Always contrast the highest-ceiling greenfield option (with its benchmark) against the smallest version and a cut list. Stop when a wrong answer would not change the work.

## Brief

```
Smallest change that makes X correct.
List what you left out and why.
Never "all edge cases".
```

## Pull request

Use `pr-body <base> --feature NAME=PATHS`. Keep the body under about 1,500 characters. One thing. Net lines. `## Verification` with `Ran:` or `Not run: <check>, because <why>`.

## Release

About every 10 merged PRs, or weekly. Body generated from those merged PRs. `senior-reviewer` reads it as a structural diff.

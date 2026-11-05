---
name: hydrojug-untangle
description: "Opt-in: untangle caller files or the current diff. Slash /hydrojug-untangle only."
disable-model-invocation: true
argument-hint: "[optional focus inside the scoped files]"
---

# Hydrojug untangle

Kolin invoked `/hydrojug-untangle`. If Kolin did not, stop.

Inspired by [caldoai/skills `untangle-codebase`](https://github.com/caldoai/skills/blob/main/skills/untangle-codebase/SKILL.md) (MIT). Not pinned. Not a whole-repo rewrite.

This skill does not grant `full-send` powers. Ask before commit, push or merge.

## Scope

Use the caller's files or the current diff only. Otherwise use the current diff against the base branch (repo policy base, else `main`), including the working tree. Never the whole repo by default.

If Kolin names a focus, stay inside those scoped files. Widening needs an explicit Kolin yes in this session.

## Optional extras

Ask once. Do only what Kolin picks. Both stay in scope.

| Extra | What it does |
| --- | --- |
| Comments | Remove comments that only restate the code. Load `no-comments` if Kolin picks this. |
| Tests | Remove tests that would not catch a real bug. Fix tests that fail without one. |

## 1. List problems. Do not edit yet.

Scan scoped files. Ask: should these pieces change together? Write every miss.

Three ways to get it wrong:

- **Hidden coupling:** pieces that must change together, but the code hides it. Copied logic. Hidden globals. Related code split by layer. A call order callers just have to know.
- **Needless coupling:** pieces tied together that change for different reasons. Callers on internals. Stable code importing volatile code. A general function that speaks one caller's words. A shallow wrapper whose interface tracks its guts.
- **Surplus:** pieces with no reason of their own to change. Pass-through wrappers. Unused extension points. Dead code.

Also note special cases: an `if` for one value, a parameter for one caller, a swallowed error, a retry or sleep, a disabled test.

Scan these inside scope only: Coupling, Naming, Abstraction, Duplication, State, Comments, Structure, Dead code.

## 2. Propose fixes. Still no edits.

Work as if today's requirements were known from the start. Prefer one root-cause fix over many special-case patches. Prefer delete and narrow over a new abstraction.

Write each proposed fix above the problems it solves.

Load when relevant. Do not copy them here:

- `principle-redesign-from-first-principles`
- `principle-subtract-before-you-add`
- `principle-migrate-callers-then-delete-legacy-apis`
- `principle-minimize-reader-load`
- `principle-laziness-protocol`
- `deslop`
- `no-comments` (only if Kolin chose Comments)

## 3. Apply surgical fixes in scope

Smallest root-cause diffs in the scoped files. Subtract before you add.

Do not complete it to the end. Do not rewrite the repo. Stop when remaining issues are out of scope or need Kolin's yes.

Prove touched paths in this session. If you change tests, make them fail first.

## Decision log

Problems first:

```md
- `path:line` what is wrong
```

Then each fix above the problems it solves:

```md
- the fix
  - `path:line` problem it removes
```

## Stop

Report what changed, what Kolin must still decide, and every leftover outside scope.

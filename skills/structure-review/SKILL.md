---
name: structure-review
description: Use only when Kolin asks for a structure review or the policy sends a blueprint or first slice here. Strict read-only review of code structure. It counts state owners, duplicate paths and reader load, then reports each fix with its proof and the simpler shape.
disable-model-invocation: true
---

# Structure review

Find what makes the code hard to change, prove it with a count, and name the simpler shape. Report only. `hydrojug-untangle` applies the fixes when Kolin asks.

Correctness, security and proof of behavior belong to `senior-reviewer` and `interrogate`. Leave them out.

## Scope

Review what you were handed, and nothing wider. A finding outside it is one line under Leftovers.

- **A blueprint, before code.** Run Owners and Paths on the code that exists today. Say which existing owner each new state extends, which existing path each new task extends, and what the build deletes. A blueprint that adds a second owner or a second path fails.
- **A first slice or a diff.** Run every check on the changed files and the modules they call. Handed a blueprint with its first slice, do both: the slice is checked against the owners the blueprint names.
- **A folder or a feature.** Run every check on it. Read `git log` for files that were written and then rewritten.

## Measure first

Run these before you form a view. A finding with no count and no `path:line` is dropped. Every count over one becomes a fix, or a line that says why it stays.

When the scope is over about 4,000 source lines, run the counts on all of it, then read in full only the files the counts point at. Name the rest under Not read.

1. **Size.** Lines added and removed, source and tests apart (`git diff --numstat`). The feature's source files and lines against its budget: a read-only page 5 files and 800 lines, an edit page 7 and 1,200, a core write flow 12 and 2,500. Files over 400 lines, and any file the change pushes past 1,000.
2. **Owners.** For each state the code stores (a status column, a plan state, a queue state, a flag): every place that writes it (`rg`). Writes in more than one module are a finding. Then every place that works out the same derived answer from it by hand, such as `state === "waiting" && live`: more than one is a finding.
3. **Paths.** For each task a user can do (accept, decline, save, submit): every function that carries it out. Two engines for one task are a finding. Put their guard lists side by side. Each difference is a bug or the one real reason for two.
4. **Reader load.** Take the question a new reader asks first, such as "what happens when a planner accepts a request". Trace it from the entry point to the write. Count the files opened, the layers that only forward, and the times one row is read or locked.
5. **Duplicates.** The same query, mapping, guard chain or type shape in two places. Search for one distinctive line of each suspect before you claim it. Two helpers that differ only by the client or library they use (`fooSql` beside `fooDrizzle`) point at the root: two tools for one job in one module. Count the files that use both.
6. **Shape.** Booleans or nullable fields that must agree. A boolean parameter that switches behavior. A branch per case where a union or a table would carry it. An `"x" in value` test beside a tagged union. A wrapper with one caller. A file under 40 lines with one importer. Related writes that are not atomic. A value written into text and read back with a pattern match when a field already holds it. Optional parameters that exist only so a test can swap a fake, passed down through many signatures.
7. **Boundaries.** The same normalizing or checking call at many call sites, such as `division.toLowerCase()`: count them. It belongs once where the value enters, with a type that says it is done.
8. **Direction.** Imports that point the wrong way: shared code that imports a feature, domain logic that sits in a route folder, a client copy of a server rule.
9. **Run-time waste.** Work repeated in one request: the same read twice, a query in a loop, a recompute of a value the caller holds, independent reads run in sequence, a read that one mode loads and never uses.
10. **Dead and silent.** A branch no caller can reach: trace each flag and mode to its callers. A fallback that hides a bad input: a `-1` index that reads as "no rows", a `?? null` over an unclear contract, arguments swapped back without a word. A hand-built helper where the repo already has one: search the shared helpers before you accept it.

## Then read for the bigger move

The counts find what repeats. They do not find the design that makes a whole file unnecessary. After the counts, read each file in scope once more with one question: what would make this file, this mode or this branch not needed at all? Two files that are one tool written twice, one tool that is six behind a mode flag, one model stated three times in one function. Do not stop at "this could be cleaner".

## Climb the ladder

For each finding, try the rungs in order and stop at the first that solves it. Name the rung in the fix.

1. **Delete.** What breaks if this goes? If nothing a user or a caller relies on, it goes: the second engine, the pass-through, the dead branch, the unused option, the test that repeats another test.
2. **Simplify.** One owner for the state. One path for the task. A union or a table in place of the branches. The wrapper inlined. A value derived, not kept in sync.
3. **Optimize.** Only code that is already simple: drop the repeat read, start independent work together.
4. **Automate.** A kind of finding seen twice becomes a check whose message names the fix (pstack `correct`). Never automate around code that should be deleted.

Prefer the move that makes a whole branch, helper or mode disappear over the move that tidies it. Ask what the code would be if today's requirements had been known on day one.

Do not force a model. Boring code that is clear, local and unlikely to grow stays. An abstraction that removes no branch and no invalid state is itself a finding.

Read a principle before you cite it, at `~/.agents/skills/<name>/SKILL.md`: `principle-model-the-domain`, `principle-minimize-reader-load`, `principle-subtract-before-you-add`, `principle-laziness-protocol`, `principle-redesign-from-first-principles`, `principle-type-system-discipline`, `principle-boundary-discipline`.

## Prove each fix

A first impression is a lead. Before a fix goes in the report:

- Open the cited lines and confirm them.
- Name what proves the behavior stays: the test, the parity run or the model that covers the code. If nothing covers it, say so, because that is part of the cost.
- Estimate the lines the fix removes, and label the number a guess.
- Look for the reason the code is this way (`git log`, an ADR, a nearby test). A real reason drops the finding or becomes its one open question.

## Report

First line: `Structure review of <scope> at <sha>: <Sound / Fix first / Redesign>`.

- `Fix first`: a fix on rung 1 or 2 stands with proof.
- `Redesign`: the shape is wrong enough that a new blueprint costs less than the fixes one by one. Say what the blueprint must decide.
- `Sound`: no fix on rung 1 or 2 stands. Give the Scores, then any rung 3 or 4 fix, or "No findings".

Then, in this order:

1. **Scores**, 1 to 10 with one line each: size against need, state model, module direction, duplication, time to answer the main question. They make two reviews of one area comparable.
2. **Fixes**, ranked by the lines and concepts they remove. Give the eight biggest in full, then the rest as one line each under **Smaller**. Each fix sits above the problems it solves, which is the decision-log shape `hydrojug-untangle` starts from:

```md
- <rung>: the fix in one sentence, with the simpler shape named. Removes about N lines (guess). Behavior held by <test or run>.
  - `path:line` the problem, with its count
```

3. **Cause** of each fix: `no blueprint`, `scope too big`, `review missed it` or `a check could catch it`. Name the check for the last kind.
4. **Done well**: up to three things worth copying.
5. **Leftovers**, then **Not read**: files in scope you did not open.

No renames, no style notes, no praise beyond Done well.

# The target architecture

pstack architecture is a codebase where a change that looks right from one file is right for the whole repo. An agent sees only the files it opened, copies the nearest example and takes the shortest path that compiles (`correct`, `architect`). So the target is deep modules with one owner per piece of state, one supported way per task, internals that an outside import cannot reach, and lists derived from one source. Gates enforce each of these, so they hold after the program ends.

## Steps

1. **Ground.** Run `how` over every subsystem through `swarm`, one read-only worker per area. Each worker returns the subsystem's modules and entry points. It also returns the state each module owns and who writes that state. Run `why` on any ownership or layering that looks wrong before you plan to change it, so its reason becomes a constraint and not a guess.
2. **Census the red flags.** Screen every module against `~/.agents/skills/architect/references/design-red-flags.md`: shallow module, information leakage, temporal decomposition, pass-through method, split ownership, two ways to do one task, importable internals and hand-synced lists. Record each hit with `file:line` in `research/red-flags.md`. Each kind becomes a countable baseline, and each count needs a script or a gate that prints it, not a hand tally.
3. **Sketch the target** with `architect`. It runs `arena` with structurally distinct candidates on the panel in `pstack-local/models.md`. The package is a module map: each module, the state it owns, its public interface, what it may import, and the red flags it removes. Write the callers' usage first and derive the types from it. Prefer the candidate that hides more behind a smaller interface.
4. **Interrogate** the synthesized map. Act on consensus findings. Park a real product question in `gates.md`.
5. **Record** the map in `.pstack/architecture.md` and its reasons in an ADR. Link both from `AGENTS.md`.
6. **Gate it.** Express each boundary as data that a gate reads: import boundaries in the dead-code tool or a lint rule, banned imports with the fix text that names the owner, and owner lists in `gate-policy.json`. Seed each gate at today's count with an owner wave. A boundary that no gate can express is a finding for `correct`, which decides the next best level.
7. **Order the waves.** Subtract first: delete dead code, pass-through methods and the second way to do a task (`principle-subtract-before-you-add`). Then move state to its one owner, and make the internals unreachable. Then reshape the interfaces, migrating every caller and deleting the old interface in the same wave (`principle-migrate-callers-then-delete-legacy-apis`).

## Rules for the waves

- A move that does not lower reader load somewhere is reverted (`refactoring.md` step 7).
- A file that a wave would push past the line limit is split first, as a pure move in its own commit.
- A new module needs an owner that no existing module can be. Extend the existing owner when one fits.
- When implementation fights the map in the same way twice, stop. Re-ground with `how` and return to `architect` (its Phase E). Do not patch around a wrong map.
- Update `.pstack/architecture.md` in the same commit as any wave that changes the map, so the map and the code never disagree.

## Done

The predicate's row 4 holds when three things are true. Every red-flag baseline reads zero and is deleted. Every boundary in the map has a gate at zero allowance. A fresh `how` pass over two subsystems the program touched describes the same modules as `.pstack/architecture.md`.

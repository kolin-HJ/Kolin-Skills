# AGENTS.md

This is the only agent instruction file in this repository. Every agent reads it. There is no `CLAUDE.md` and no tool-specific rule file, so a new rule goes here or, better, into a gate.

<One paragraph: what the product is, who uses it every day, the systems it reads and writes, and what a wrong change costs those users.>

## How work happens here

This repo runs Lauren Tan's pstack method ([upstream](https://github.com/cursor/plugins/tree/main/pstack), MIT), vendored in `.agents/skills/` at the commit in `.agents/PSTACK.SOURCE`. Go deep first. The goal is the most impact with the least code, proven on the running app.

1. **Non-trivial program units follow poteto-mode playbooks.** Read `.agents/skills/poteto-mode/SKILL.md` and match the unit to one playbook in `.agents/skills/poteto-mode/playbooks/`.
2. **Understand before editing.** A nontrivial change starts with the `how` skill. Code that crosses a module boundary gets `architect` first. Name the data shape before writing logic.
3. **Observe, do not ask.** Prototype any question an experiment can answer. Ask only for product or preference calls. Prove it on the real app.
4. **Review adversarially.** Read every non-trivial diff in a fresh context (`<reviewer>`). A contested design, mutation, access rule or schema change also gets `interrogate`.
5. **Encode lessons in structure.** The second time an instruction is needed, make it a type, a lint rule, a test or a script (`correct`).
6. **Keep a decision trail** for long or unattended work with `show-me-your-work` under `.pstack/`.

### Where this repo's rules win over pstack

| pstack says | Here |
|---|---|
| Commit, push, open or merge PRs without asking | <the approval rule> |
| Trunk is `main` | Branch from and PR into **`<integration branch>`**. |
| Keep a comment for a non-obvious why | **No comments.** The why goes into a name, a type, a test, an ADR or the PR body. A gate enforces it. |
| Its own checks | `<check command>` is the gate. pstack's checks add to it and never replace it. |
| Post to chat, update tickets freely | <the external-write rule> |

## Done means proven

The verification skill is `.agents/skills/verify-<app>/`. Read its `SKILL.md` first. Drive the feature the way a user does, capture the action and the resulting state, and read side effects back. A refactor shows zero parity changes against the base branch, or only the intended ones. A user-facing feature with no map file gets one in the same change. Say plainly what you did not verify.

The `verifier` agent proves a change in a fresh context and returns the PR's Verification block. A PR's `## Verification` lists one `- Ran: \`<command>\` <result>` line per check and one `- Not run: <check>, because <reason>` line per skipped one. The PR proof check fails the PR otherwise.

## Gates

`<check command>` runs every gate. The pre-commit and pre-push hooks run it. A suppression carries `-- <reason>` and never replaces a fix. A baseline is temporary debt, burned to zero and deleted. A new rule enters at zero.

| Gate | Command | What it stops |
|---|---|---|
| <gate> | `<command>` | <what it stops> |

## Rules

| Rule | Enforced by |
|---|---|
| <one row per mistake class from `correct`> | <the type, gate, test or "review" when no tool can check it> |

## Code rules

- **Smallest change that works.** Prefer deleting code to adding it. No speculative option, layer or abstraction.
- **Model the data first.** Encode the domain in a type, a registry or a state machine, not an `if` per case.
- **Types carry the invariants.** No `any`, no cast except right after a validated parse, no non-null assertion.
- **Boundaries.** Validate input at the edge. Check authorization before every write. Keep secrets out of logs, errors and client bundles.
- **One decision in one place.** Extend the existing owner. Refactor a shared module in its own change.
- **Tests** call the code the way its caller does, assert a literal, and are seen failing without the change first.

## Architecture

`.pstack/architecture.md` is the module map: each module, the state it owns, its interface and what it may import. The ADRs in `docs/adr/` hold each subsystem's rules. Read the owning ADR before changing its module, and update it in the same change.

## Writing

Replies, PR bodies, commit messages and docs follow the `unslop` and `technical-writing` skills. PR titles are Conventional Commits. The body fills `.github/PULL_REQUEST_TEMPLATE.md`.

## Commands

```bash
<check command>
<dev command>
<verify launch command>
```

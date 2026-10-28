---
name: explainer
description: Build a one-page HTML explainer of a change, PR, subsystem or decision, with a diagram of the real mechanism, its evidence and what is not verified. Use only when the user asks for an explainer, an explainer page, a visual walkthrough or "explain this visually", or says yes to your one-line offer. Never build one unasked. Not for UI craft (emil-design-eng) or UI testing (break-ui).
---

# Explainer

An explainer replaces reading a diff or a long report with one page a person can review in a few minutes.

## Gather the facts first

1. Name the subject: a PR (`gh pr view`, `gh pr diff`), a branch (`git diff origin/<base>...HEAD`), a subsystem, or a decision.
2. Read the code the page will describe. Read the callers of each changed function.
3. Collect the evidence that exists: the repo's verification evidence (for example `.verify/evidence/`), test and gate output, reviewer reports, the PR body's Verification section. Label each claim measured, inferred or guess.
4. If a fact is missing, say so on the page. Never fill a gap with a plausible guess.

## What the page holds, in this order

1. **The task**, in the user's words, and who notices the change (a planner, a caller, an operator).
2. **A diagram of the real mechanism.** Show the actual modules, tables, routes and functions, and how data moves between them. For a change, show the flow before and after, or mark the changed parts on one diagram.
3. **What changed**, grouped by what the parts do together, with file links. Keep moved code apart from new code.
4. **Evidence**: each check that ran, with its command and result, and the screenshots inline.
5. **Risks and findings**: the reviewer's findings with severity and `file:line`, and each behavior change.
6. **Not verified**: every claim nobody ran, in a list of its own.

Keep it to one screen per section.

## Publish

Where the harness has an Artifact tool, load its design skill first (for UI craft, `emil-design-eng`), then publish the page as a private artifact and give the user the link. Otherwise write a single self-contained `.html` file in the session's folder and give its path. Draw diagrams as inline SVG, with colors from CSS variables so the page reads in light and dark mode.

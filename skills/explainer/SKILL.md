---
name: explainer
description: Build a one-page HTML explainer of a change, PR, subsystem or decision. Use only when the user asks for an explainer page, a visual walkthrough page, or "explain this visually" as a page, or says yes to your one-line offer. Never build one unasked. A spoken explain, how, or walk-me-through goes to pstack `teach` via `pstack-local`. Not for UI craft (emil-design-eng) or UI testing (break-ui).
---

# Explainer

An explainer is one page a person can review in a few minutes. It is not the in-chat reply. Spoken explain, how, and walk-through requests go to `teach` via `pstack-local`. Offer this page in one line. Build it only after a yes.

## Reply and page shape

1. One-sentence answer first.
2. One diagram of at most 7 nodes, or a short build-up series, with the real module, function, route and table names.
3. At most 3 short beats of prose. No table unless the user asked for one.
4. Offer a deeper explainer page only after a yes.

## Gather the facts first

1. Name the subject: a PR (`gh pr view`, `gh pr diff`), a branch (`git diff origin/<base>...HEAD`), a subsystem, or a decision.
2. Read the code the page will describe. Read the callers of each changed function.
3. Collect the evidence that exists: the repo's verification evidence (for example `.verify/evidence/`), test and gate output, reviewer reports, the PR body's Verification section. Label each claim measured, inferred or guess.
4. If a fact is missing, say so on the page. Never fill a gap with a plausible guess.

## Publish

Where the harness has an Artifact tool, load its design skill first (for UI craft, `emil-design-eng`), then publish the page as a private artifact and give the user the link. Otherwise write a single self-contained `.html` file in the session's folder and give its path. Draw diagrams as inline SVG, with colors from CSS variables so the page reads in light and dark mode. Evidence, risks and what is not verified go on the page as short beats, or after a yes for more depth.

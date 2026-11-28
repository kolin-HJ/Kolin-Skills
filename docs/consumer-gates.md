# Consumer gate recipe

Copy these into a product repo. Do not wire them from this repo.

The copies live in `templates/consumer-gate/` and `templates/state-machine/`.

| Gate | Fail when |
|---|---|
| PR size | Over 600 changed lines, excluding tests, lockfiles and generated files. `templates/consumer-gate/check-pr-size.mjs` |
| Import boundary | A cycle, or a data layer importing feature code. dependency-cruiser `no-circular` plus `no-restricted-paths`, or oxlint `import/no-cycle` plus a no-restricted-paths equivalent |
| Dead code | knip reports unused exports or files |
| Function size | Report-only (`warn` in `templates/consumer-gate/lint-snippets.json`): a function over 80 lines or complexity 12 never blocks an edit or push. Prefer a folder budget (`feature-budget`) and the 1,000-line file cap |
| Boolean switch | A boolean parameter that switches behavior. ESLint / oxlint `no-restricted-syntax` snippet in `templates/consumer-gate/lint-snippets.json` |

State: copy `templates/state-machine/` (`State` union, `Event` union, pure `transition()`, one effect file, one test per transition).

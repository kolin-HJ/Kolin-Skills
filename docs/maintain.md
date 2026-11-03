# Maintain

Steward and CEO share this loop. Kolin merges.

## Weekly drift

From the Kolin-Skills checkout, against each consumer checkout on disk:

```sh
python3 bin/kolin-skills check-drift /path/to/hj-plm
python3 bin/kolin-skills check-drift /path/to/hj-supply-chain
python3 bin/kolin-skills check-drift /path/to/hj-reporting
python3 bin/kolin-skills check-drift /path/to/hj-ui
```

Paths are clone roots, not GitHub URLs. A failure is a drifted pstack pin, a drifted synced `senior-reviewer`, or policy that still requires a reviewer on every PR or every staging merge. What the check compares: [`consumer-drift.md`](consumer-drift.md).

## Land a change

1. CEO sends a one-liner.
2. Steward opens one draft PR on Kolin-Skills. Steward does not merge unless this session said yes.
3. Steward reports the draft to CEO.
4. Kolin merges.

## Pins and outside notes

Bump a pstack pin only when upstream moved. No drive-by bumps.

An X or trusted-practitioner digest is a proposal. It lands only when Kolin says yes.

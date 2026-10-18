#!/usr/bin/env bash
set -uo pipefail

if [ $# -lt 4 ]; then
  echo "usage: bracket-parity.sh <base-checkout> <branch-checkout> <out-dir> <branch-sha> [--legacy]" >&2
  exit 2
fi
BASE="$1" HEAD_CO="$2" OUT="$3" SHA="$4" LEGACY="${5:-}"
LAUNCH="${PARITY_LAUNCH:-node .agents/skills/verify/scripts/verify.mjs launch --fresh}"
CLEANUP="${PARITY_CLEANUP:-node .agents/skills/verify/scripts/verify.mjs cleanup}"
PARITY="${PARITY_SCRIPT:-node .agents/skills/verify/scripts/parity.mjs}"
mkdir -p "$OUT"

git -C "$HEAD_CO" checkout -q -f --detach "$SHA"

leg() {
  local dir="$1" out="$2" extra="$3"
  (cd "$dir" && $LAUNCH > "$out.launch" 2>&1 && $PARITY $extra --out "$out" > "$out.log" 2>&1; $CLEANUP > /dev/null 2>&1)
}

leg "$BASE" "$OUT/A.json" "$LEGACY"
leg "$HEAD_CO" "$OUT/X.json" ""
leg "$BASE" "$OUT/B.json" "$LEGACY"
(cd "$HEAD_CO" && $PARITY --observed "$OUT/X.json" --against "$OUT/A.json,$OUT/B.json" > "$OUT/cmp.json" 2>&1)
echo "compare: $OUT/cmp.json"

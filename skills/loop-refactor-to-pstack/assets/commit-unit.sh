#!/usr/bin/env bash
set -euo pipefail

if [ $# -lt 3 ]; then
  echo "usage: commit-unit.sh <unit-id> <message-file> <path>..." >&2
  exit 2
fi
unit="$1" message_file="$2"
shift 2
root=$(git rev-parse --show-toplevel)
cd "$root"
store="$(cd "$(dirname "$0")" && pwd)"
attribution="${COMMIT_ATTRIBUTION:-}"

if [ -n "$(git diff --cached --name-only)" ]; then
  echo "refusing: the index already holds staged changes; commit or unstage them first" >&2
  git diff --cached --name-only >&2
  exit 1
fi

git add -A -- "$@"
staged=$(git diff --cached --name-only)
if [ -z "$staged" ]; then
  echo "refusing: nothing to commit under $*" >&2
  exit 1
fi

{
  cat "$message_file"
  printf '\n\nUnit: %s\n' "$unit"
  if [ -n "$attribution" ]; then printf '%s\n' "$attribution"; fi
} > "$store/.commit-msg"
if ! git commit -q -F "$store/.commit-msg"; then
  git reset -q -- "$@"
  rm -f "$store/.commit-msg"
  echo "commit failed; unstaged $*" >&2
  exit 1
fi
rm -f "$store/.commit-msg"
sha=$(git rev-parse --short HEAD)
orch="$HOME/.agents/skills/poteto-mode/scripts/orch/orch.ts"
if [ -f "$orch" ] && [ -f "$store/units.tsv" ] && command -v bun >/dev/null; then
  bun "$orch" --store "$store" unit set "$unit" --state committed --sha "$sha" >/dev/null ||
    echo "warning: the store has no unit $unit; add it with orch unit add" >&2
fi
echo "$unit committed as $sha ($(echo "$staged" | wc -l | tr -d ' ') files)"

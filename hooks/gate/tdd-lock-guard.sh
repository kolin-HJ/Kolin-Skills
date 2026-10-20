#!/usr/bin/env bash
# PreToolUse (Edit|Write|MultiEdit) guard for the failing-test-first rule.
# Git-history detection of "committed as failing" is too fuzzy, so this uses an explicit lock:
# /tdd writes the repo-relative paths of the failing tests it committed, one per line, to
# <worktree>/.tdd-locked (add .tdd-locked to .git/info/exclude so it is never committed).
# Edits to a listed file are blocked. To change a locked test on purpose, Kolin or Boss removes its line.
# Any error fails open.
input=$(cat) || exit 0
f=$(jq -r '.tool_input.file_path // ""' <<<"$input" 2>/dev/null) || exit 0
[ -n "$f" ] || exit 0
d=$(dirname "$f"); while [ ! -d "$d" ] && [ "$d" != / ]; do d=$(dirname "$d"); done
top=$(git -C "$d" rev-parse --show-toplevel 2>/dev/null) || exit 0
lock="$top/.tdd-locked"; [ -f "$lock" ] || exit 0
rel=$(realpath -m --relative-to="$top" "$f" 2>/dev/null) || exit 0
while IFS= read -r l; do l=${l%%#*}; l=$(echo "$l" | xargs); [ -z "$l" ] && continue
  [ "$(realpath -m --relative-to="$top" "$top/$l")" = "$rel" ] && {
    echo "Blocked by owner rule: $rel is a committed failing test locked by /tdd (.tdd-locked). Fix the code, not the test. Do not retry or work around this." >&2; exit 2; }
done < "$lock"
exit 0

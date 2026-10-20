#!/usr/bin/env bash
# Gate wrapper. Run from a repo worktree: ~/.claude/hooks/gate-pass.sh [gate command...]
# Default gate: npm run verify:local-gate, under flock "${GATE_LOCK:-/workspace/runs/gate.lock}".
# On exit 0 it writes the marker <git-dir>/gate-pass/<HEAD sha> that the Stop hook requires.
# The marker is per worktree and per commit: any new commit needs a fresh gate pass.
# A dirty tree is gated as-is but the marker records "dirty" and the Stop hook rejects it.
# Queue collapse (2026-10-11): each waiter registers in $GATE_QUEUE/<worktree-key>. A newer run for the
# same worktree overwrites that entry; an older run still waiting for the lock sees it and exits 3
# ("superseded"). A waiter whose worktree HEAD moved past the commit it was started for also exits 3.
# Once a run holds the lock it is never superseded. The gate command is capped at GATE_TIMEOUT (45m).
set -o pipefail
lock="${GATE_LOCK:-/workspace/runs/gate.lock}"; q="${GATE_QUEUE:-$(dirname "$lock")/gate-queue}"
head=$(git rev-parse HEAD 2>/dev/null) || { echo "gate-pass: no commit yet" >&2; exit 2; }
top=$(git rev-parse --show-toplevel) || { echo "gate-pass: not in a git worktree" >&2; exit 2; }
cd "$top"; gd=$(git rev-parse --absolute-git-dir); head=$(git rev-parse HEAD)
[ $# -gt 0 ] || set -- npm run verify:local-gate
mkdir -p "$q"; key=$(printf '%s' "$top" | sha1sum | cut -c1-16); me="$$ $head $top"
printf '%s\n' "$me" > "$q/$key"
cleanup() { [ "$(cat "$q/$key" 2>/dev/null)" = "$me" ] && rm -f "$q/$key"; }
trap cleanup EXIT
exec 9>>"$lock"
while :; do
  flock -w 10 9 && break
  [ "$(cat "$q/$key" 2>/dev/null)" = "$me" ] || { echo "gate-pass: superseded by a newer run for $top, exiting" >&2; exit 3; }
  [ "$(git rev-parse HEAD)" = "$head" ] || { echo "gate-pass: HEAD moved past $head in $top, exiting" >&2; exit 3; }
done
cleanup
timeout --kill-after=60 "${GATE_TIMEOUT:-45m}" "$@" 9>&-; rc=$?
[ $rc -eq 124 ] && echo "gate-pass: TIMEOUT after ${GATE_TIMEOUT:-45m}" >&2
flock -u 9
if [ $rc -eq 0 ]; then
  mkdir -p "$gd/gate-pass"
  state=clean; [ -n "$(git status --porcelain --untracked-files=no)" ] && state=dirty
  printf '%s %s %s %s\n' "$head" "$state" "$(date -Iseconds)" "$*" > "$gd/gate-pass/$head"
  echo "gate-pass: PASS, marker $gd/gate-pass/$head ($state)"
else echo "gate-pass: FAIL rc=$rc, no marker" >&2; fi
exit $rc

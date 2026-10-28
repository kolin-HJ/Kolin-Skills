#!/usr/bin/env bash
set -uo pipefail

builder_model="${SUBAGENT_MODEL:-claude-sonnet-5-5}"
builder_effort="${SUBAGENT_EFFORT:-medium}"
dirs=()
[ -n "${AGENTS_DIR:-}" ] && dirs+=("$AGENTS_DIR")
root=$(git rev-parse --show-toplevel 2>/dev/null) && dirs+=("$root/.claude/agents")
dirs+=("$HOME/.claude/agents")

failed=0
check() {
  local name="$1" model="${2:-$builder_model}" effort="${3:-$builder_effort}"
  local file=""
  for dir in "${dirs[@]}"; do
    if [ -f "$dir/$name.md" ]; then file="$dir/$name.md"; break; fi
  done
  if [ -z "$file" ]; then
    echo "MISSING $name: no $name.md in ${dirs[*]}"
    failed=1
    return
  fi
  front=$(awk 'NR==1 && $0=="---" {f=1; next} f && $0=="---" {exit} f' "$file")
  got_model=$(printf '%s\n' "$front" | sed -n 's/^model:[[:space:]]*//p')
  got_effort=$(printf '%s\n' "$front" | sed -n 's/^effort:[[:space:]]*//p')
  problems=""
  [ "$model" = any ] || [ "$got_model" = "$model" ] || problems="$problems model=${got_model:-unset} (want $model)"
  [ "$effort" = any ] || [ "$got_effort" = "$effort" ] || problems="$problems effort=${got_effort:-unset} (want $effort)"
  if [ -n "$problems" ]; then
    echo "WRONG $name ($file):$problems"
    failed=1
  else
    echo "ok $name: model ${got_model:-unset}, effort ${got_effort:-unset} ($file)"
  fi
}

check poteto-agent
check senior-reviewer "${REVIEWER_MODEL:-claude-opus-5-5}" any
check comment-sicko any any
check haiku-worker "${WORKER_MODEL:-claude-haiku-5-5}"
for extra in "$@"; do check "$extra"; done

if [ "$failed" -ne 0 ]; then
  echo "Fix each WRONG or MISSING definition's frontmatter with the user's yes, then rerun." >&2
fi
exit "$failed"

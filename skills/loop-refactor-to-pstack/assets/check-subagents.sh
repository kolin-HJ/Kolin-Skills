#!/usr/bin/env bash
set -uo pipefail

model="${SUBAGENT_MODEL:-claude-sonnet-5-5}"
effort="${SUBAGENT_EFFORT:-medium}"
dirs=()
[ -n "${AGENTS_DIR:-}" ] && dirs+=("$AGENTS_DIR")
root=$(git rev-parse --show-toplevel 2>/dev/null) && dirs+=("$root/.claude/agents")
dirs+=("$HOME/.claude/agents")

failed=0
check() {
  name="$1" must_read="$2" model="${3:-$model}"
  file=""
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
  [ "$got_model" = "$model" ] || problems="$problems model=${got_model:-unset} (want $model)"
  [ "$got_effort" = "$effort" ] || problems="$problems effort=${got_effort:-unset} (want $effort)"
  if [ -n "$must_read" ] && ! grep -q "$must_read" "$file"; then
    problems="$problems does not read $must_read"
  fi
  if [ -n "$problems" ]; then
    echo "WRONG $name ($file):$problems"
    failed=1
  else
    echo "ok $name: $model, effort $effort ($file)"
  fi
}

check poteto-agent "poteto-mode/SKILL.md"
check senior-reviewer ""
check comment-sicko ""
check haiku-worker "" "${WORKER_MODEL:-claude-haiku-5-5}"
for extra in "$@"; do check "$extra" ""; done

if [ "$failed" -ne 0 ]; then
  echo "Fix the frontmatter (model: $model, effort: $effort) with the user's yes, then rerun." >&2
fi
exit "$failed"

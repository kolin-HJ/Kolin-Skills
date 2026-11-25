#!/usr/bin/env bash
emit="claude"
if [[ "${1:-}" == "--emit" && -n "${2:-}" ]]; then
  emit="$2"
fi
input=$(cat)
deny() {
  if [[ "$emit" == "antigravity" ]]; then
    if command -v jq >/dev/null; then
      jq -nc --arg reason "Blocked: $1" '{decision:"deny",reason:$reason}'
    else
      python3 -c 'import json,sys; print(json.dumps({"decision":"deny","reason":"Blocked: " + sys.argv[1]}))' "$1"
    fi
    exit 0
  fi
  echo "Blocked: $1" >&2
  exit 2
}
allow() {
  if [[ "$emit" == "antigravity" ]]; then
    echo '{"decision":"allow"}'
  fi
  exit 0
}
command -v jq >/dev/null || deny "jq is missing, so this guard cannot read the command; install jq"
here=$(dirname "$(readlink -f "${BASH_SOURCE[0]}")")
out=$(python3 "$here/git_guard.py" payload <<<"$input")
rc=$?
if (( rc == 2 )); then
  deny "$out"
fi
if (( rc != 0 )); then
  deny "the git guard could not run. Report this to Kolin; do not work around it."
fi
allow

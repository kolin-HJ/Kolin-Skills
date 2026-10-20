#!/usr/bin/env bash
# Stop hook. Blocks ending a session that edited files inside a git worktree unless
#  (i) the transcript has a poteto-mode Skill tool_use (/workspace/runs/check-skill-use.sh), unless it is a
#      read-only thread (every recorded permissionMode is "plan"; that script decides), and
#  (ii) <git-dir>/gate-pass/<HEAD> exists and says "clean" (written by ~/.claude/hooks/gate-pass.sh).
# Read-only sessions pass. Any script error fails OPEN with a warning. After 3 blocks in one
# session it lets the session stop with a warning so it can never loop forever.
warn() { echo "stop-hook warning: $1 (allowing stop)" >&2; exit 0; }
trap 'warn "hook error at line $LINENO"' ERR
input=$(cat) || warn "no input"
tp=$(jq -r '.transcript_path // ""' <<<"$input") || warn "bad json"
cwd=$(jq -r '.cwd // ""' <<<"$input"); sid=$(jq -r '.session_id // "x"' <<<"$input")
[ -r "$tp" ] || warn "transcript not readable"
# Files this session edited.
mapfile -t files < <(jq -r 'select(.type=="assistant")|.message.content[]?|select(.type=="tool_use" and (.name=="Edit" or .name=="Write" or .name=="MultiEdit" or .name=="NotebookEdit"))|.input.file_path // .input.notebook_path // empty' "$tp" 2>/dev/null | sort -u)
[ ${#files[@]} -eq 0 ] && exit 0
top=""
for f in "${files[@]}"; do
  d=$(dirname "$f"); while [ ! -d "$d" ] && [ "$d" != / ]; do d=$(dirname "$d"); done
  t=$(git -C "$d" rev-parse --show-toplevel 2>/dev/null) && { top=$t; break; }
done
[ -z "$top" ] && exit 0   # edits only outside any repo
cnt=/tmp/claude-stophook-$sid; n=$(( $(cat "$cnt" 2>/dev/null || echo 0) + 1 ))
[ $n -gt 3 ] && warn "blocked 3 times already in session $sid"
miss=()
/workspace/runs/check-skill-use.sh "$tp" poteto-mode >/dev/null 2>&1 || miss+=("no poteto-mode Skill tool_use in this transcript: invoke the poteto-mode skill")
gd=$(git -C "$top" rev-parse --absolute-git-dir); head=$(git -C "$top" rev-parse HEAD)
m="$gd/gate-pass/$head"
if [ ! -f "$m" ]; then miss+=("no gate-pass marker for HEAD $head in $top: commit, then run ~/.claude/hooks/gate-pass.sh")
elif ! grep -q " clean " "$m"; then miss+=("gate marker for $head was written on a dirty tree: commit and re-run ~/.claude/hooks/gate-pass.sh"); fi
[ ${#miss[@]} -eq 0 ] && { rm -f "$cnt"; exit 0; }
echo $n > "$cnt"
reason="Not done (owner rule, block $n of 3): $(IFS='; '; echo "${miss[*]}")."
jq -n --arg r "$reason" '{decision:"block",reason:$r}'
exit 0

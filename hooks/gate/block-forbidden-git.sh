#!/usr/bin/env bash
input=$(cat)
deny() { echo "Blocked by owner rule: $1. Do not retry or work around this." >&2; exit 2; }
command -v jq >/dev/null || deny "jq is missing, so this guard cannot read the command; install jq"
cmd=$(jq -r '.tool_input.command // .toolInput.command // .command // ""' <<<"$input")
cwd=$(jq -r '.cwd // ""' <<<"$input")
here=$(dirname "$(readlink -f "${BASH_SOURCE[0]}")")
guard() { python3 "$here/git_guard.py" "$1" <<<"$cmd"; }
shopt -s nocasematch
nv="--no-""verify"
guard skip-hooks; rc=$?
(( rc == 0 )) && deny "skipping git hooks is forbidden"
(( rc != 1 )) && { [[ $cmd == *"$nv"* ]] || [[ $cmd =~ git[[:space:]]+commit([^;&|]*)[[:space:]]-[a-z]*n ]]; } && deny "skipping git hooks is forbidden (unparsed command)"
if [[ $cmd =~ gh[[:space:]]+pr[[:space:]]+merge ]]; then
  [[ $cmd =~ [\;\&\|\`] ]] && deny "run gh pr merge on its own"
  pr=$(grep -oE '[[:space:]][0-9]+([[:space:]]|$)' <<<"$cmd" | head -1 | tr -d ' ')
  repo=$(grep -oE '(-R|--repo)[= ][^ ]+' <<<"$cmd" | head -1 | sed -E 's/^(-R|--repo)[= ]//')
  [[ -z $pr ]] && deny "gh pr merge needs a PR number"
  base=$(cd "${cwd:-.}" 2>/dev/null; gh pr view "$pr" ${repo:+-R "$repo"} --json baseRefName -q .baseRefName 2>/dev/null)
  [[ -z $base || $base == main || $base == master ]] && deny "merging into main (production) needs Kolin"
fi
[[ ! $cmd =~ gh[[:space:]]+pr[[:space:]]+merge ]] && [[ $cmd =~ --auto([[:space:]]|$) && $cmd =~ gh[[:space:]] ]] && deny "auto-merge is forbidden"
guard api-merge; rc=$?
(( rc == 0 )) && deny "merging via the API is forbidden"
(( rc != 1 )) && [[ $cmd =~ (merge|automerge|auto_merge|enablePullRequestAutoMerge) && $cmd =~ gh[[:space:]]+api ]] && deny "merging via the API is forbidden"
pushes=$(sed -e ':a' -e '/\\$/N; s/\\\n/ /; ta' <<<"$cmd" | tr -d "\"'" | grep -oiE 'git([[:space:]]+-[^[:space:]]+([[:space:]]+[^-[:space:]][^[:space:]]*)?)*[[:space:]]+push([[:space:]][^;&|`]*)?')
if [[ -n $pushes ]]; then
  [[ $pushes =~ (--for|--de|--m|--pru|[[:space:]]-[^-[:space:]]*[fd]|[[:space:]][+:][^[:space:]]) ]] && deny "force-push / delete / mirror push is forbidden"
  protected='(main|master|staging|sandbox)'
  [[ $pushes =~ (^|[[:space:]]|:|refs/heads/)$protected([[:space:]]|\)|$) ]] && deny "pushing to ${BASH_REMATCH[2]} is forbidden; it changes only through a PR"
  branch=$(git -C "${cwd:-.}" rev-parse --abbrev-ref HEAD 2>/dev/null)
  [[ $branch =~ ^$protected$ ]] && deny "pushing while on $branch is forbidden; it changes only through a PR"
fi
guard d4; rc=$?
(( rc == 0 )) && deny "D4: skipping the local gate or editing hook files is forbidden for agents"
(( rc != 1 )) && [[ $cmd =~ SKIP_LOCAL_GATE= ]] && deny "D4: skipping the local gate is forbidden (unparsed command)"
exit 0

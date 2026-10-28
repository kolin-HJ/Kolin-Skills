#!/usr/bin/env bash
input=$(cat)
deny() { echo "Blocked: $1" >&2; exit 2; }
command -v jq >/dev/null || deny "jq is missing, so this guard cannot read the command; install jq"
cmd=$(jq -r '.tool_input.command // .toolInput.command // .command // ""' <<<"$input")
file=$(jq -r '.tool_input.file_path // .toolInput.file_path // ""' <<<"$input")
cwd=$(jq -r '.cwd // ""' <<<"$input")
here=$(dirname "$(readlink -f "${BASH_SOURCE[0]}")")
if [[ -n $file ]]; then
  python3 "$here/git_guard.py" file-hooks <<<"$file"; rc=$?
  (( rc == 0 )) && deny "agents do not edit git or harness hook files. Ask Kolin to make the change."
  (( rc != 1 )) && deny "the file path could not be checked. Report this to Kolin; do not work around it."
  out=$(python3 "$here/git_guard.py" file-install "$cwd" <<<"$file"); rc=$?
  (( rc == 0 )) && deny "$out"
  (( rc != 3 )) && deny "the install check could not run. Report this to Kolin; do not work around it."
  exit 0
fi
guard() { python3 "$here/git_guard.py" "$1" "$cwd" <<<"$cmd"; }
shopt -s nocasematch
nv="--no-""verify"
protected='(main|master|staging|sandbox)'
guard skip-hooks; rc=$?
(( rc == 0 )) && deny "agents do not skip git hooks (--no-verify, commit -n, core.hooksPath). Fix what the hook reports."
(( rc != 1 )) && { [[ $cmd == *"$nv"* ]] || [[ $cmd =~ git[[:space:]]+commit([^;&|]*)[[:space:]]-[a-z]*n ]]; } && deny "this command could not be parsed and may skip git hooks. Rewrite it so --no-verify or -n does not appear in the command, for example put a commit message in a file and use -F."
guard pr-merge; rc=$?
merging=0
(( rc == 0 )) && merging=1
(( rc != 0 && rc != 1 )) && [[ $cmd =~ gh[[:space:]]+pr[[:space:]]+merge ]] && merging=1
if (( merging )); then
  [[ $cmd =~ [\;\&\|\`] ]] && deny "run gh pr merge as one plain command, with no chained commands."
  pr=$(grep -oE '[[:space:]][0-9]+([[:space:]]|$)' <<<"$cmd" | head -1 | tr -d ' ')
  repo=$(grep -oE '(-R|--repo)[= ][^ ]+' <<<"$cmd" | head -1 | sed -E 's/^(-R|--repo)[= ]//')
  [[ -z $pr ]] && deny "gh pr merge needs a PR number. Pass it as an argument."
  base=$(cd "${cwd:-.}" 2>/dev/null; gh pr view "$pr" ${repo:+-R "$repo"} --json baseRefName -q .baseRefName 2>/dev/null)
  [[ -z $base || $base =~ ^$protected$ ]] && deny "merging into ${base:-an unknown base} needs Kolin; it changes only through a PR that Kolin merges. Ask Kolin to merge."
fi
(( ! merging )) && [[ $cmd =~ --auto([[:space:]]|$) && $cmd =~ gh[[:space:]] ]] && deny "auto-merge is forbidden. Ask Kolin to merge."
guard api-merge; rc=$?
(( rc == 0 )) && deny "merging via the API is forbidden. Ask Kolin to merge."
(( rc != 1 )) && [[ $cmd =~ (merge|automerge|auto_merge|enablePullRequestAutoMerge) && $cmd =~ gh[[:space:]]+api ]] && deny "merging via the API is forbidden. Ask Kolin to merge."
guard api-ref; rc=$?
(( rc == 0 )) && deny "moving or deleting a protected branch via the API is forbidden; it changes only through a PR. Open a PR instead."
(( rc != 1 )) && [[ $cmd =~ (git/refs/heads/|updateRef|deleteRef) && $cmd =~ gh[[:space:]]+api ]] && deny "moving or deleting a branch via the API is forbidden (unparsed command). Open a PR instead."
pushes=$(sed -e ':a' -e '/\\$/N; s/\\\n/ /; ta' <<<"$cmd" | tr -d "\"'" | grep -oiE 'git([[:space:]]+-[^[:space:]]+([[:space:]]+[^-[:space:]][^[:space:]]*)?)*[[:space:]]+push([[:space:]][^;&|`]*)?')
if [[ -n $pushes ]]; then
  [[ $pushes =~ (--for|--de|--m|--pru|[[:space:]]-[^-[:space:]]*[fd]|[[:space:]][+:][^[:space:]]) ]] && deny "force-push, delete and mirror pushes are forbidden. Push a new commit to a work branch instead."
  [[ $pushes =~ (^|[[:space:]]|:|heads/)$protected([[:space:]]|\)|$) ]] && deny "pushing to ${BASH_REMATCH[2]} is forbidden; it changes only through a PR. To create a missing one, use gh api repos/<owner>/<repo>/git/refs -f ref=refs/heads/${BASH_REMATCH[2]} -f sha=<sha>, which GitHub rejects if it exists"
  branch=$(git -C "${cwd:-.}" rev-parse --abbrev-ref HEAD 2>/dev/null)
  [[ $branch =~ ^$protected$ ]] && deny "pushing while on $branch is forbidden; it changes only through a PR. Switch to a work branch, then push."
fi
guard d4; rc=$?
(( rc == 0 )) && deny "agents do not skip the local gate or write hook files. Fix what the gate reports."
(( rc != 1 )) && [[ $cmd =~ SKIP_LOCAL_GATE= ]] && deny "agents do not skip the local gate or write hook files. Fix what the gate reports."
out=$(guard install); rc=$?
(( rc == 0 )) && deny "$out"
exit 0

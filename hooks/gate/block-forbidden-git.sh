#!/usr/bin/env bash
# PreToolUse guard for Bash: hard-blocks merges, auto-merge, force-push, pushes to staging/main, and --no-verify,
# regardless of permission mode. Exit 2 blocks the tool call and shows stderr to Claude.
input=$(cat)
cmd=$(jq -r '.tool_input.command // ""' <<<"$input")
cwd=$(jq -r '.cwd // ""' <<<"$input")
deny() { echo "Blocked by owner rule: $1. Do not retry or work around this." >&2; exit 2; }
here=$(dirname "$(readlink -f "${BASH_SOURCE[0]}")")
guard() { python3 "$here/git_guard.py" "$1" <<<"$cmd"; }
shopt -s nocasematch
# Only real git invocations count. Heredoc bodies, quoted text, file paths and grep patterns do not.
# git_guard.py exits 0 = forbidden, 1 = clean, anything else = could not parse: fall back to the old broad match (fail closed).
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
# Merging through the API: only real API calls that write, hit a /merge endpoint, or use graphql.
guard api-merge; rc=$?
(( rc == 0 )) && deny "merging via the API is forbidden"
(( rc != 1 )) && [[ $cmd =~ (merge|automerge|auto_merge|enablePullRequestAutoMerge) && $cmd =~ gh[[:space:]]+api ]] && deny "merging via the API is forbidden"
if [[ $cmd =~ git([[:space:]]+-C[[:space:]]+[^[:space:]]+)?[[:space:]]+push ]]; then
  [[ $cmd =~ (--force|[[:space:]]-f([[:space:]]|$)|[[:space:]]\+[^[:space:]]|--mirror|--delete|[[:space:]]-d([[:space:]]|$)) ]] && deny "force-push / delete / mirror push is forbidden"
  [[ $cmd =~ (^|[[:space:]:/])main([[:space:]]|$) ]] && deny "pushing to main is forbidden"
  branch=$(git -C "${cwd:-.}" rev-parse --abbrev-ref HEAD 2>/dev/null)
  [[ $branch == main ]] && deny "pushing while on $branch is forbidden"
fi
# --- D4 (optional): agents may not set SKIP_LOCAL_GATE or write to hook files ---
guard d4; rc=$?
(( rc == 0 )) && deny "D4: skipping the local gate or editing hook files is forbidden for agents"
(( rc != 1 )) && [[ $cmd =~ SKIP_LOCAL_GATE= ]] && deny "D4: skipping the local gate is forbidden (unparsed command)"
exit 0

#!/usr/bin/env bash
# PreToolUse guard for Bash: hard-blocks merges, auto-merge, force-push, pushes to staging/main, and --no-verify,
# regardless of permission mode. Exit 2 blocks the tool call and shows stderr to Claude.
input=$(cat)
cmd=$(jq -r '.tool_input.command // ""' <<<"$input")
cwd=$(jq -r '.cwd // ""' <<<"$input")
deny() { echo "Blocked by owner rule: $1. Do not retry or work around this." >&2; exit 2; }
shopt -s nocasematch
[[ $cmd =~ --no-verify ]] && deny "--no-verify is forbidden"
[[ $cmd =~ git[[:space:]]+commit([^;&|]*)[[:space:]]-[a-z]*n ]] && deny "git commit -n skips hooks"
if [[ $cmd =~ gh[[:space:]]+pr[[:space:]]+merge ]]; then
  [[ $cmd =~ [\;\&\|\`] ]] && deny "run gh pr merge on its own"
  pr=$(grep -oE '[[:space:]][0-9]+([[:space:]]|$)' <<<"$cmd" | head -1 | tr -d ' ')
  repo=$(grep -oE '(-R|--repo)[= ][^ ]+' <<<"$cmd" | head -1 | sed -E 's/^(-R|--repo)[= ]//')
  [[ -z $pr ]] && deny "gh pr merge needs a PR number"
  base=$(cd "${cwd:-.}" 2>/dev/null; gh pr view "$pr" ${repo:+-R "$repo"} --json baseRefName -q .baseRefName 2>/dev/null)
  [[ -z $base || $base == main || $base == master ]] && deny "merging into main (production) needs Kolin"
fi
[[ ! $cmd =~ gh[[:space:]]+pr[[:space:]]+merge ]] && [[ $cmd =~ --auto([[:space:]]|$) && $cmd =~ gh[[:space:]] ]] && deny "auto-merge is forbidden"
[[ $cmd =~ (merge|automerge|auto_merge|enablePullRequestAutoMerge) && $cmd =~ gh[[:space:]]+api ]] && deny "merging via the API is forbidden"
if [[ $cmd =~ git([[:space:]]+-C[[:space:]]+[^[:space:]]+)?[[:space:]]+push ]]; then
  [[ $cmd =~ (--force|[[:space:]]-f([[:space:]]|$)|[[:space:]]\+[^[:space:]]|--mirror|--delete|[[:space:]]-d([[:space:]]|$)) ]] && deny "force-push / delete / mirror push is forbidden"
  [[ $cmd =~ (^|[[:space:]:/])main([[:space:]]|$) ]] && deny "pushing to main is forbidden"
  branch=$(git -C "${cwd:-.}" rev-parse --abbrev-ref HEAD 2>/dev/null)
  [[ $branch == main ]] && deny "pushing while on $branch is forbidden"
fi
exit 0

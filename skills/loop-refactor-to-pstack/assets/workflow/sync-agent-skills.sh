#!/usr/bin/env bash
set -euo pipefail

root=$(cd "$(dirname "$0")/.." && pwd)
skills="$root/.agents/skills"
links="$root/.claude/skills"
source_file="$root/.agents/PSTACK.SOURCE"
skip=" setup-pstack "
mode=link
pstack_checkout=""

usage() {
  echo "usage: scripts/sync-agent-skills.sh [--check] [--pstack <cursor/plugins checkout>]" >&2
  exit 2
}

while [ $# -gt 0 ]; do
  case "$1" in
    --check) mode=check ;;
    --pstack) pstack_checkout="${2:?--pstack needs a path}"; shift ;;
    *) usage ;;
  esac
  shift
done

vendor_pstack() {
  local src="$1" commit tmp name
  commit=$(git -C "$src" rev-parse HEAD)
  tmp=$(mktemp -d)
  git -C "$src" archive HEAD pstack/skills pstack/LICENSE | tar -x -C "$tmp"
  if [ -f "$source_file" ]; then
    while IFS= read -r name; do
      rm -rf "${skills:?}/$name"
    done < <(sed -n 's/^skill: //p' "$source_file")
  fi
  {
    echo "source: https://github.com/cursor/plugins/tree/main/pstack"
    echo "commit: $commit"
    echo "license: MIT, Lauren Tan (see PSTACK.LICENSE)"
    echo "refresh: scripts/sync-agent-skills.sh --pstack <cursor/plugins checkout>"
  } > "$source_file"
  for dir in "$tmp"/pstack/skills/*/; do
    name=$(basename "$dir")
    case "$skip" in *" $name "*) continue ;; esac
    if [ -e "$skills/$name" ]; then
      echo "refusing to overwrite repo-owned skill $name" >&2
      exit 1
    fi
    cp -R "$dir" "$skills/$name"
    echo "skill: $name" >> "$source_file"
  done
  cp "$tmp/pstack/LICENSE" "$root/.agents/PSTACK.LICENSE"
  rm -rf "$tmp"
  echo "vendored pstack at $commit"
}

problems=0
report() {
  echo "$1" >&2
  problems=$((problems + 1))
}

[ -n "$pstack_checkout" ] && vendor_pstack "$pstack_checkout"
mkdir -p "$links"

for dir in "$skills"/*/; do
  name=$(basename "$dir")
  target="../../.agents/skills/$name"
  if [ ! -f "$dir/SKILL.md" ]; then
    report "$name has no SKILL.md"
    continue
  fi
  if [ -L "$links/$name" ] && [ "$(readlink "$links/$name")" = "$target" ]; then
    continue
  fi
  if [ "$mode" = check ]; then
    report ".claude/skills/$name is missing or does not link to $target"
  else
    rm -rf "${links:?}/$name"
    ln -s "$target" "$links/$name"
  fi
done

for link in "$links"/*; do
  [ -e "$link" ] || [ -L "$link" ] || continue
  name=$(basename "$link")
  if [ ! -d "$skills/$name" ]; then
    if [ "$mode" = check ]; then
      report ".claude/skills/$name has no skill in .agents/skills"
    else
      rm -f "$link"
    fi
  fi
done

cursor_link="$root/.cursor/skills"
if [ ! -L "$cursor_link" ] || [ "$(readlink "$cursor_link")" != "../.agents/skills" ]; then
  if [ "$mode" = check ]; then
    report ".cursor/skills is missing or does not link to ../.agents/skills"
  else
    rm -rf "$cursor_link"
    ln -s ../.agents/skills "$cursor_link"
  fi
fi

if [ "$problems" -gt 0 ]; then
  echo "run scripts/sync-agent-skills.sh to repair the links" >&2
  exit 1
fi
echo "skill links ok: $(find "$skills" -mindepth 1 -maxdepth 1 -type d | wc -l | tr -d ' ') skills"

#!/usr/bin/env bash
# Usage: check-skill-use.sh <transcript.jsonl> [skill=poteto-mode]
# OK (exit 0) if: assistant tool_use "Skill" with input.skill/command matching, OR
# a user slash-command expansion (<command-name>/skill</command-name>, followed by
# the isMeta "Base directory for this skill: .../skill" body). Prints which.
set -u
f="${1:?usage: check-skill-use.sh <transcript.jsonl> [skill]}"; s="${2:-poteto-mode}"
[ -r "$f" ] || { echo "MISSING $s (no file $f)"; exit 1; }
tool=$(jq -r --arg s "$s" 'select(.type=="assistant")|.message.content[]?|select(.type=="tool_use" and .name=="Skill")
  |(.input.skill // .input.command // .input.name // "")|ltrimstr("/")|select(.==$s or endswith(":"+$s))' "$f" 2>/dev/null | wc -l)
slash=$(jq -r --arg s "$s" 'select(.type=="user")|.message.content
  |(if type=="string" then . else (map(.text? // "")|join("\n")) end)
  |select(contains("<command-name>/"+$s+"</command-name>") or test("Base directory for this skill: \\S*/"+$s+"\\b"))' "$f" 2>/dev/null | grep -c . )
# Binding rule (2026-10-10 8:04 PM): only a Skill tool_use counts; slash expansion is reported but not sufficient.
# Build-only rule (Kolin, 2026-10-11 11:28 PM): poteto-mode is required only on build threads.
# Signal (operate-claude-code-headless: read-only stages run in interactionMode plan): the transcript's
# recorded permissionMode. EXEMPT only if at least one is recorded and every one is "plan". A plan thread
# approved out of plan mode, or any missing/unknown mode, counts as a build thread (fail closed).
modes=$(jq -r 'select(.permissionMode!=null)|.permissionMode' "$f" 2>/dev/null | sort -u)
if [ "${POTETO_FORCE_BUILD:-0}" != 1 ] && [ "$modes" = "plan" ]; then echo "EXEMPT $s (read-only thread: permissionMode=plan only) tool_use=$tool slash=$slash"; exit 0; fi
if [ "$tool" -gt 0 ]; then echo "OK $s tool_use=$tool slash=$slash"; exit 0; fi
echo "MISSING $s tool_use=$tool slash=$slash"; exit 1

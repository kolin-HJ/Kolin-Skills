#!/usr/bin/env python3
import json
import pathlib
import sys

import ag_notes

PREVIEW_PREFIXES = ("mcp__t3-code__preview_", "mcp_t3-code_preview_")
WARN_EVERY = 15
SAME_BATCH = 4


def parse_emit(argv):
    if "--emit" in argv:
        index = argv.index("--emit")
        if index + 1 < len(argv):
            return argv[index + 1]
    return "claude"


def preview_call_count(transcript_path, exclude_id):
    path = pathlib.Path(transcript_path or "")
    if not path.is_file():
        return 0
    seen = set()
    unnamed = 0
    with path.open(errors="ignore") as handle:
        for line in handle:
            if not any(prefix in line for prefix in PREVIEW_PREFIXES):
                continue
            try:
                record = json.loads(line)
            except ValueError:
                continue
            if not isinstance(record, dict):
                continue
            message = record.get("message")
            content = message.get("content") if isinstance(message, dict) else None
            for block in content if isinstance(content, list) else []:
                if isinstance(block, dict) and block.get("type") == "tool_use" and str(block.get("name") or "").startswith(PREVIEW_PREFIXES):
                    seen.add(block.get("id"))
            for call in record.get("tool_calls") if isinstance(record.get("tool_calls"), list) else []:
                if isinstance(call, dict) and str(call.get("name") or "").startswith(PREVIEW_PREFIXES):
                    call_id = call.get("id")
                    if call_id:
                        seen.add(call_id)
                    else:
                        unnamed += 1
    seen.discard(exclude_id)
    return len(seen) + unnamed


def main():
    emit = parse_emit(sys.argv[1:])
    try:
        event = json.load(sys.stdin)
    except (json.JSONDecodeError, ValueError):
        if emit == "antigravity":
            print(json.dumps({"decision": "allow"}))
        return 0
    if not isinstance(event, dict):
        if emit == "antigravity":
            print(json.dumps({"decision": "allow"}))
        return 0
    tool_call = event.get("toolCall") if isinstance(event.get("toolCall"), dict) else {}
    transcript = event.get("transcript_path") or event.get("transcriptPath")
    exclude = event.get("tool_use_id") or tool_call.get("id")
    prior = preview_call_count(transcript, exclude)
    if prior < WARN_EVERY or prior % WARN_EVERY >= SAME_BATCH:
        if emit == "antigravity":
            print(json.dumps({"decision": "allow"}))
        return 0
    warning = (
        f"This thread already made {prior} preview calls. Each one re-reads the whole context. "
        "Hand the UI drive to the repo's `verifier` subagent (or its verify skill) and keep only its screenshots and verdict here."
    )
    if emit == "antigravity":
        ag_notes.append_note(event, warning)
        print(json.dumps({"decision": "allow"}))
        return 0
    json.dump({"hookSpecificOutput": {"hookEventName": "PreToolUse", "additionalContext": warning}}, sys.stdout)
    return 0


if __name__ == "__main__":
    sys.exit(main())

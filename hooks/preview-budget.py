#!/usr/bin/env python3
import json
import pathlib
import sys

PREVIEW_PREFIX = "mcp__t3-code__preview_"
WARN_EVERY = 40


def preview_call_count(transcript_path, exclude_id):
    path = pathlib.Path(transcript_path or "")
    if not path.is_file():
        return 0
    seen = set()
    with path.open(errors="ignore") as handle:
        for line in handle:
            if PREVIEW_PREFIX not in line:
                continue
            try:
                record = json.loads(line)
            except ValueError:
                continue
            message = record.get("message") if isinstance(record, dict) else None
            content = message.get("content") if isinstance(message, dict) else None
            for block in content if isinstance(content, list) else []:
                if isinstance(block, dict) and block.get("type") == "tool_use" and str(block.get("name")).startswith(PREVIEW_PREFIX):
                    seen.add(block.get("id"))
    seen.discard(exclude_id)
    return len(seen)


def main():
    event = json.load(sys.stdin)
    prior = preview_call_count(event.get("transcript_path"), event.get("tool_use_id"))
    if not prior or prior % WARN_EVERY:
        return 0
    warning = (
        f"This thread already made {prior} preview calls. Each one re-reads the whole context. "
        "Hand the UI drive to the repo's `verifier` subagent (or its verify skill) and keep only its screenshots and verdict here."
    )
    json.dump({"hookSpecificOutput": {"hookEventName": "PreToolUse", "additionalContext": warning}}, sys.stdout)
    return 0


if __name__ == "__main__":
    sys.exit(main())

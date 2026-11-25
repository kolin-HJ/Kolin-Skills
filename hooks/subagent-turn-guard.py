#!/usr/bin/env python3
import json
import os
import pathlib
import sys

WARN_AT = (55, 65)


def assistant_turns(transcript_path):
    path = pathlib.Path(transcript_path or "")
    if not path.is_file():
        return 0
    seen = set()
    with path.open(errors="ignore") as handle:
        for line in handle:
            if '"type":"assistant"' not in line and '"type": "assistant"' not in line:
                continue
            try:
                record = json.loads(line)
            except ValueError:
                continue
            if not isinstance(record, dict) or record.get("type") != "assistant":
                continue
            message = record.get("message")
            identifier = (message.get("id") if isinstance(message, dict) else None) or record.get("uuid")
            if identifier:
                seen.add(identifier)
    return len(seen)


def main():
    try:
        event = json.load(sys.stdin)
    except (json.JSONDecodeError, ValueError):
        return 0
    transcript = str(event.get("transcript_path") or "")
    if "/subagents/" not in transcript.replace(os.sep, "/"):
        return 0
    turns = assistant_turns(transcript)
    if turns not in WARN_AT:
        return 0
    note = (
        f"Subagent turn {turns} of 80: do not start new files or extra exploration. "
        "Finish the current hunk, run the check in your brief, and write your report now so maxTurns does not cut you off."
    )
    json.dump({"hookSpecificOutput": {"hookEventName": "PreToolUse", "additionalContext": note}}, sys.stdout)
    return 0


if __name__ == "__main__":
    sys.exit(main())

#!/usr/bin/env python3
import json
import os
import pathlib
import re
import sys

SAFE_ID = re.compile(r"[^A-Za-z0-9_.-]+")


def notes_dir():
    override = os.environ.get("KOLIN_SKILLS_STATE_DIR")
    base = pathlib.Path(override) if override else pathlib.Path.home() / ".kolin-skills"
    return base / "ag-notes"


def note_file(conversation_id):
    safe = SAFE_ID.sub("_", str(conversation_id or "")).strip("._")
    return notes_dir() / f"{safe}.txt" if safe else None


def append_note(payload, text):
    if not text:
        return
    path = note_file((payload or {}).get("conversationId") or (payload or {}).get("conversation_id"))
    if path is None:
        return
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("a", encoding="utf-8") as handle:
        handle.write(text.strip() + "\n\n")


def flush_notes(payload):
    path = note_file((payload or {}).get("conversationId") or (payload or {}).get("conversation_id"))
    if path is None or not path.is_file():
        return ""
    try:
        content = path.read_text(encoding="utf-8").strip()
        path.unlink(missing_ok=True)
        return content
    except OSError:
        return ""


def main():
    try:
        payload = json.load(sys.stdin)
    except (json.JSONDecodeError, ValueError):
        print("{}")
        return 0
    text = flush_notes(payload if isinstance(payload, dict) else {})
    if text:
        print(json.dumps({"injectSteps": [{"systemMessage": {"systemMessage": text}}]}))
    else:
        print("{}")
    return 0


if __name__ == "__main__":
    sys.exit(main())

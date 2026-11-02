import json
import os
import re
import sys

SEAT_MODELS = {"senior-reviewer": "opus"}
PINNED = re.compile(r"^model:[ \t]*(\S+)", re.M)


def definition(agent, cwd):
    folders = []
    directory = cwd
    while True:
        folders.append(os.path.join(directory, ".claude", "agents"))
        parent = os.path.dirname(directory)
        if parent == directory:
            break
        directory = parent
    for home in dict.fromkeys([os.environ.get("CLAUDE_CONFIG_DIR"), os.path.expanduser("~/.claude")]):
        if home:
            folders.append(os.path.join(home, "agents"))
    for folder in folders:
        path = os.path.join(folder, agent + ".md")
        if os.path.isfile(path):
            with open(path, encoding="utf-8") as handle:
                return handle.read()
    return None


def pinned_model(text):
    header = text.split("---", 2)[1] if text.startswith("---") else ""
    match = PINNED.search(header)
    return match.group(1) if match else None


def main():
    event = json.load(sys.stdin)
    tool_input = event.get("tool_input") or {}
    agent = tool_input.get("subagent_type") or ""
    seat = SEAT_MODELS.get(agent)
    if not seat or tool_input.get("model"):
        return 0
    text = definition(agent, event.get("cwd") or os.getcwd())
    pinned = pinned_model(text) if text else None
    if not pinned or seat in pinned.lower():
        return 0
    json.dump({"hookSpecificOutput": {
        "hookEventName": "PreToolUse",
        "permissionDecision": "allow",
        "permissionDecisionReason": f"{agent} runs on {seat}; this repo's copy pins a lower model",
        "updatedInput": {**tool_input, "model": seat},
    }}, sys.stdout)
    return 0


if __name__ == "__main__":
    sys.exit(main())

import json
import os
import re
import sys

SEAT_FLOORS = {"senior-reviewer": "opus"}
MEETS_FLOOR = {"opus": ("opus", "fable", "mythos")}
BUILT_IN_DEFAULTS = {"Explore": "sonnet"}
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


def chosen_model(agent, cwd):
    text = definition(agent, cwd)
    if text is None and agent in BUILT_IN_DEFAULTS:
        return BUILT_IN_DEFAULTS[agent], f"{agent} ignores CLAUDE_CODE_SUBAGENT_MODEL, so it runs on {BUILT_IN_DEFAULTS[agent]} unless the call passes a model"
    seat = SEAT_FLOORS.get(agent)
    pinned = pinned_model(text) if seat and text else None
    if pinned and not any(tier in pinned.lower() for tier in MEETS_FLOOR[seat]):
        return seat, f"{agent} runs on {seat}; this repo's copy pins a lower model"
    return None, None


def main():
    event = json.load(sys.stdin)
    tool_input = event.get("tool_input") or {}
    if tool_input.get("model"):
        return 0
    model, reason = chosen_model(tool_input.get("subagent_type") or "", event.get("cwd") or os.getcwd())
    if not model:
        return 0
    json.dump({"hookSpecificOutput": {
        "hookEventName": "PreToolUse",
        "permissionDecision": "allow",
        "permissionDecisionReason": reason,
        "updatedInput": {**tool_input, "model": model},
    }}, sys.stdout)
    return 0


if __name__ == "__main__":
    sys.exit(main())

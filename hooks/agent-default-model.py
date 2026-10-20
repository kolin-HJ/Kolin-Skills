import json
import os
import pathlib
import re
import sys

INHERIT_PINNED_BUILTINS = {"Explore", "claude-code-guide"}
DEFAULT_MODEL = "sonnet"
MODEL_LINE = re.compile(r"^model:\s*\S", re.M)


def agent_definition(name, cwd):
    homes = [os.environ.get("CLAUDE_CONFIG_DIR"), "~/.claude"]
    start = pathlib.Path(cwd).resolve()
    folders = [folder / ".claude/agents" for folder in [start, *start.parents]]
    folders += [pathlib.Path(home).expanduser() / "agents" for home in homes if home]
    for folder in folders:
        path = folder / f"{name}.md"
        if path.is_file():
            return path.read_text(errors="replace")
    return None


def pins_no_model(definition):
    parts = definition.split("---", 2)
    return len(parts) == 3 and not MODEL_LINE.search(parts[1])


def main():
    event = json.load(sys.stdin)
    tool_input = event.get("tool_input") or {}
    name = tool_input.get("subagent_type")
    if not name or tool_input.get("model"):
        return 0
    if name in INHERIT_PINNED_BUILTINS:
        reason = f"{name} pins model inherit"
    else:
        definition = agent_definition(name, event.get("cwd") or os.getcwd())
        if definition is None or not pins_no_model(definition):
            return 0
        reason = f"{name} pins no model"
    json.dump(
        {
            "hookSpecificOutput": {
                "hookEventName": "PreToolUse",
                "permissionDecision": "allow",
                "permissionDecisionReason": f"{reason}; defaulted to {DEFAULT_MODEL}",
                "updatedInput": {**tool_input, "model": DEFAULT_MODEL},
            }
        },
        sys.stdout,
    )
    return 0


if __name__ == "__main__":
    sys.exit(main())

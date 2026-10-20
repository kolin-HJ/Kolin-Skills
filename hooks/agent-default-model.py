import json
import os
import re
import sys

UNPINNED_BUILTINS = {"Explore", "claude-code-guide", "general-purpose"}
DEFAULT_MODEL = "sonnet"
PINNED = re.compile(r"^model:[ \t]*\S", re.M)
TOOLS = re.compile(r"^tools:(.*)$", re.M)
WRITERS = {"Edit", "Write", "NotebookEdit", "*"}


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


def unpinned_builder(text):
    frontmatter = text.split("---", 2)[1] if text.startswith("---") else ""
    if PINNED.search(frontmatter):
        return False
    tools = TOOLS.search(frontmatter)
    return tools is None or bool(WRITERS & {t.strip() for t in tools.group(1).split(",")})


def needs_default(agent, cwd):
    if agent in UNPINNED_BUILTINS:
        return True
    text = definition(agent, cwd) if agent else None
    return text is not None and unpinned_builder(text)


def main():
    event = json.load(sys.stdin)
    tool_input = event.get("tool_input") or {}
    agent = tool_input.get("subagent_type")
    if tool_input.get("model") or not needs_default(agent, event.get("cwd") or os.getcwd()):
        return 0
    json.dump(
        {
            "hookSpecificOutput": {
                "hookEventName": "PreToolUse",
                "permissionDecision": "allow",
                "permissionDecisionReason": f"{agent} pins no model; defaulted to {DEFAULT_MODEL}",
                "updatedInput": {**tool_input, "model": DEFAULT_MODEL},
            }
        },
        sys.stdout,
    )
    return 0


if __name__ == "__main__":
    sys.exit(main())

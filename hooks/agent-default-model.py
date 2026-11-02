import json
import os
import re
import sys

SUBAGENT_MODEL_IGNORED_BY = {"Explore": "sonnet"}
EDITING_BUILTINS = {"general-purpose", "claude"}
OPUS_REASON = (
    "Blocked: agents that can edit run on Sonnet. "
    "For an Opus judgment role, spawn `judge` (no edit tools). For a builder, drop `model`."
)
SEAT_MODELS = {"senior-reviewer": "opus"}
PINNED = re.compile(r"^model:[ \t]*(\S+)", re.M)
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


def frontmatter(text):
    return text.split("---", 2)[1] if text.startswith("---") else ""


def pinned_model(text):
    match = PINNED.search(frontmatter(text))
    return match.group(1) if match else None


def edit_capable(agent, text):
    if agent in EDITING_BUILTINS:
        return True
    if text is None:
        return False
    tools = TOOLS.search(frontmatter(text))
    return tools is None or bool(WRITERS & {t.strip() for t in tools.group(1).split(",")})


def decide(agent, tool_input, text):
    passed = tool_input.get("model")
    seat = SEAT_MODELS.get(agent)
    pinned = pinned_model(text) if text else None
    if seat and not passed and pinned and seat not in pinned.lower():
        return "allow", f"{agent} runs on {seat} in pstack-local/models.md; this definition pins a lower model", seat
    if not passed and agent in SUBAGENT_MODEL_IGNORED_BY:
        model = SUBAGENT_MODEL_IGNORED_BY[agent]
        return "allow", f"{agent} ignores CLAUDE_CODE_SUBAGENT_MODEL; defaulted to {model}", model
    if passed and "opus" in passed.lower() and edit_capable(agent, text) and os.environ.get("KOLIN_OPUS_BUILDERS") != "1":
        return "deny", OPUS_REASON, None
    return None


def main():
    event = json.load(sys.stdin)
    tool_input = event.get("tool_input") or {}
    agent = tool_input.get("subagent_type") or "general-purpose"
    text = definition(agent, event.get("cwd") or os.getcwd())
    verdict = decide(agent, tool_input, text)
    if verdict is None:
        return 0
    decision, reason, model = verdict
    output = {"hookEventName": "PreToolUse", "permissionDecision": decision, "permissionDecisionReason": reason}
    if model:
        output["updatedInput"] = {**tool_input, "model": model}
    json.dump({"hookSpecificOutput": output}, sys.stdout)
    return 0


if __name__ == "__main__":
    sys.exit(main())

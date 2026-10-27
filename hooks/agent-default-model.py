import json
import os
import re
import sys

UNPINNED_BUILTINS = {"Explore", "claude-code-guide", "general-purpose"}
EDITING_BUILTINS = {"general-purpose", "claude"}
FORK_REASON = (
    "fork inherits Opus and the parent's whole context. Spawn poteto-agent (or the repo's implementer) "
    "to build, or Explore, Plan or senior-reviewer to read, with a six-part brief."
)
ISOLATION_REASON = (
    "isolation: worktree makes the harness refuse the builder's gate commands. "
    "Create the worktree with `git worktree add <path> -b <branch> <base>`, name the path in the brief, "
    "and spawn without isolation."
)
OPUS_REASON = (
    "Edit-capable agents run on Sonnet (pstack-local/models.md), so this Opus request would run on Sonnet. "
    "For an Opus judgment seat (pstack-local/models.md), spawn `Plan` "
    "with model opus: it is read-only and keeps MCP. For a builder, drop `model`."
)
DEFAULT_MODEL = "sonnet"
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


def effective_model(tool_input, text):
    return tool_input.get("model") or (pinned_model(text) if text else None)


def decide(agent, tool_input, text):
    if agent == "fork":
        return "deny", FORK_REASON, None
    if tool_input.get("isolation") == "worktree" and edit_capable(agent, text):
        return "deny", ISOLATION_REASON, None
    passed = tool_input.get("model")
    seat = SEAT_MODELS.get(agent)
    pinned = pinned_model(text) if text else None
    if seat and not passed and pinned and seat not in pinned.lower():
        return "allow", f"{agent} is the {seat} seat in pstack-local/models.md; this definition pins a lower model", seat
    if not effective_model(tool_input, text) and (agent in UNPINNED_BUILTINS or edit_capable(agent, text)):
        return "allow", f"{agent} pins no model; defaulted to {DEFAULT_MODEL}", DEFAULT_MODEL
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

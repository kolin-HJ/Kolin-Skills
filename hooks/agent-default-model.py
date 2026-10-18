import json
import sys

INHERIT_PINNED_BUILTINS = {"Explore", "claude-code-guide"}
DEFAULT_MODEL = "sonnet"


def main():
    event = json.load(sys.stdin)
    tool_input = event.get("tool_input") or {}
    if tool_input.get("subagent_type") not in INHERIT_PINNED_BUILTINS or tool_input.get("model"):
        return 0
    json.dump(
        {
            "hookSpecificOutput": {
                "hookEventName": "PreToolUse",
                "permissionDecision": "allow",
                "permissionDecisionReason": f"{tool_input['subagent_type']} pins model inherit; defaulted to {DEFAULT_MODEL}",
                "updatedInput": {**tool_input, "model": DEFAULT_MODEL},
            }
        },
        sys.stdout,
    )
    return 0


if __name__ == "__main__":
    sys.exit(main())

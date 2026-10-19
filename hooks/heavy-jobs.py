#!/usr/bin/env python3
import json
import pathlib
import re
import shlex
import sys


SLOT = pathlib.Path(__file__).resolve().parent / "heavy-slot.py"
TIMEOUT_MS = {False: (120_000, 600_000), True: (1_800_000, 7_200_000)}
HEREDOC = re.compile(
    r"<<-?\s*(['\"]?)([A-Za-z_][\w]*)\1.*?^\s*\2\s*$",
    re.DOTALL | re.MULTILINE,
)
QUOTED = re.compile(r"\"[^\"]*\"|'[^']*'")
POLL_LOOP = re.compile(r"\b(?:until|while|for)\b.*?\bdo\b(?:(?!\bdone\b).)*?\bsleep\s+(\d+(?:\.\d+)?)", re.DOTALL)
COMMAND_START = r"(?:^|[;&|(\n])\s*(?:\w+=\S*\s+)*"
HEAVY = re.compile(
    COMMAND_START + r"(?:"
    r"(?:pnpm|npm|yarn|bun)\s+(?:run\s+)?(?:check|verify|test|build|typecheck|lint)\b"
    r"|(?:npx\s+|bunx\s+|pnpm\s+(?:exec\s+)?)?(?:\S*/)?(?:vitest|tsc|playwright|turbo|next\s+build)\b"
    r"|java\b.*\btlc2\.TLC\b"
    r")"
)
LONG_LIVED = re.compile(r"--watch\b|\bwatch\b|\bdev\b")
POLL_MESSAGE = (
    "Blocked: a sleep loop that polls holds this turn and hits the Bash timeout. "
    "Start the job with run_in_background: true and you are notified when it exits. "
    "To wait for a file, a port or a log line, use the Monitor tool with an until-loop."
)


def main() -> int:
    try:
        payload = json.load(sys.stdin)
    except (json.JSONDecodeError, ValueError):
        return 0
    tool_input = payload.get("tool_input") or {}
    command = tool_input.get("command") or ""
    background = bool(tool_input.get("run_in_background"))
    code = QUOTED.sub(" ", HEREDOC.sub(" ", command))

    poll = POLL_LOOP.search(code)
    if poll and float(poll.group(1)) >= 2 and not background:
        print(POLL_MESSAGE, file=sys.stderr)
        return 2

    if not HEAVY.search(code) or LONG_LIVED.search(code):
        return 0
    default_ms, ceiling_ms = TIMEOUT_MS[background]
    timeout_ms = tool_input.get("timeout") or default_ms
    max_wait_ms = max(0, min(timeout_ms // 2, ceiling_ms - timeout_ms))
    prefix = f"python3 {shlex.quote(str(SLOT))} $$ {max_wait_ms // 1000}\n"
    print(json.dumps({
        "hookSpecificOutput": {
            "hookEventName": "PreToolUse",
            "updatedInput": {**tool_input, "command": prefix + command, "timeout": timeout_ms + max_wait_ms},
        }
    }))
    return 0


if __name__ == "__main__":
    sys.exit(main())

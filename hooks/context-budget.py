#!/usr/bin/env python3
import json
import pathlib
import sys


WARN_TOKENS = 200_000
STOP_TOKENS = 260_000
TAIL_BYTES = 256 * 1024
WARN_NOTE = (
    "This agent's context passed 200,000 tokens. Finish the step you are on, run the brief's check, and report "
    "what is done and what is left. The orchestrator gives the rest to a fresh agent."
)
STOP_MESSAGE = (
    "Blocked: this agent's context passed 260,000 tokens. Stop now and report: the files changed, each command "
    "with its result, and what is left. Call no more tools."
)


def transcript_of(payload) -> pathlib.Path:
    path = pathlib.Path(payload.get("transcript_path") or "")
    name = f"agent-{payload['agent_id']}.jsonl"
    return path if path.name == name else path.with_suffix("") / "subagents" / name


def tail_lines(path: pathlib.Path):
    with path.open("rb") as handle:
        size = handle.seek(0, 2)
        handle.seek(max(0, size - TAIL_BYTES))
        lines = handle.read().splitlines()
    return lines if size <= TAIL_BYTES else lines[1:]


def last_context_tokens(path: pathlib.Path):
    if not path.is_file():
        return None
    for line in reversed(tail_lines(path)):
        try:
            usage = json.loads(line).get("message", {}).get("usage")
        except (json.JSONDecodeError, AttributeError):
            continue
        if usage:
            return sum(usage.get(key, 0) for key in ("input_tokens", "cache_creation_input_tokens", "cache_read_input_tokens"))
    return None


def main() -> int:
    try:
        payload = json.load(sys.stdin)
    except (json.JSONDecodeError, ValueError):
        return 0
    if not payload.get("agent_id") or not payload.get("transcript_path"):
        return 0
    tokens = last_context_tokens(transcript_of(payload)) or 0
    if tokens >= STOP_TOKENS:
        print(STOP_MESSAGE, file=sys.stderr)
        return 2
    if tokens >= WARN_TOKENS:
        print(json.dumps({"hookSpecificOutput": {"hookEventName": "PreToolUse", "additionalContext": WARN_NOTE}}))
    return 0


if __name__ == "__main__":
    sys.exit(main())

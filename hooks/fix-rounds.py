#!/usr/bin/env python3
import json
import os
import pathlib
import subprocess
import sys
import tempfile


MAX_ROUNDS = 2
MESSAGE = (
    "Two fix rounds went to {to}. Spawn a fresh builder with a rewritten brief that carries the original brief, "
    "every later directive and the open findings. Stop a running agent with TaskStop, or add "
    "`fix-rounds: {to} <reason>` to .pstack/status.md when the message answers the builder's question "
    "or hands it new work."
)


def top_level(directory):
    result = subprocess.run(["git", "-C", directory, "rev-parse", "--show-toplevel"], capture_output=True, text=True)
    return pathlib.Path(result.stdout.strip()) if result.returncode == 0 else None


def has_override(directory, to):
    if not directory:
        return False
    top = top_level(directory)
    status = top / ".pstack/status.md" if top else None
    if status is None or not status.is_file():
        return False
    return any(line.split()[:2] == ["fix-rounds:", to] for line in status.read_text().splitlines())


def read_state(state_file):
    try:
        state = json.loads(state_file.read_text())
    except (OSError, ValueError):
        return {}
    return state if isinstance(state, dict) else {}


def count_round(session_id, to):
    state_file = pathlib.Path.home() / f".kolin-skills/state/fix-rounds-{session_id}.json"
    state = read_state(state_file)
    sent = state.get(to, 0)
    if sent >= MAX_ROUNDS:
        return sent + 1
    state[to] = sent + 1
    state_file.parent.mkdir(parents=True, exist_ok=True)
    handle, temporary = tempfile.mkstemp(dir=state_file.parent, suffix=".tmp")
    with os.fdopen(handle, "w") as stream:
        stream.write(json.dumps(state))
    os.replace(temporary, state_file)
    return sent + 1


def main():
    try:
        payload = json.load(sys.stdin)
    except (json.JSONDecodeError, ValueError):
        return 0
    session_id = payload.get("session_id")
    to = (payload.get("tool_input") or {}).get("to")
    if payload.get("agent_id") or not session_id or not to:
        return 0
    to = str(to)
    if has_override(payload.get("cwd") or os.environ.get("PWD"), to):
        return 0
    if count_round(session_id, to) > MAX_ROUNDS:
        print(MESSAGE.format(to=to), file=sys.stderr)
        return 2
    return 0


if __name__ == "__main__":
    sys.exit(main())

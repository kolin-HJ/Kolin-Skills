#!/usr/bin/env python3
import json
import os
import pathlib
import subprocess
import sys


VALUE_MESSAGE = (
    "Before the first edit, write the value case to {status}: a line starting `Value:` "
    "and the five lines from the policy's Quality work."
)
MAX_ORCHESTRATOR_FILES = 2
ORCHESTRATOR_MESSAGE = (
    f"The orchestrator has edited {MAX_ORCHESTRATOR_FILES} files here. Send the build to poteto-agent "
    "(or the repo's implementer) with a six-part brief, or add "
    "`orchestrator-builds: <reason>` to .pstack/status.md."
)


def git(directory, *args):
    return subprocess.run(["git", "-C", str(directory), *args], capture_output=True, text=True)


def top_level(path):
    directory = path.parent
    while not directory.exists():
        directory = directory.parent
    result = git(directory, "rev-parse", "--show-toplevel")
    return pathlib.Path(os.path.realpath(result.stdout.strip())) if result.returncode == 0 else None


def has_line(status, prefix):
    return status.is_file() and any(line.startswith(prefix) for line in status.read_text().splitlines())


def exclude_pstack(top):
    common = git(top, "rev-parse", "--path-format=absolute", "--git-common-dir").stdout.strip()
    exclude = pathlib.Path(common) / "info/exclude"
    exclude.parent.mkdir(parents=True, exist_ok=True)
    existing = exclude.read_text() if exclude.is_file() else ""
    if ".pstack/" not in existing.splitlines():
        prefix = "" if existing == "" or existing.endswith("\n") else "\n"
        exclude.write_text(f"{existing}{prefix}.pstack/\n")


def deny(message):
    print(message, file=sys.stderr)
    return 2


def count_file(session_id, top, path):
    state_file = pathlib.Path.home() / f".kolin-skills/state/edit-guard-{session_id}.json"
    state = json.loads(state_file.read_text()) if state_file.is_file() else {}
    files = state.get(str(top), [])
    if str(path) in files:
        return len(files)
    if len(files) >= MAX_ORCHESTRATOR_FILES:
        return len(files) + 1
    state[str(top)] = [*files, str(path)]
    state_file.parent.mkdir(parents=True, exist_ok=True)
    state_file.write_text(json.dumps(state))
    return len(state[str(top)])


def main():
    try:
        payload = json.load(sys.stdin)
    except (json.JSONDecodeError, ValueError):
        return 0
    tool_input = payload.get("tool_input") or {}
    raw = tool_input.get("file_path") or tool_input.get("notebook_path")
    if not raw:
        return 0
    path = pathlib.Path(os.path.realpath(pathlib.Path(payload.get("cwd") or ".") / raw))

    if payload.get("agent_id"):
        return 0
    top = top_level(path)
    if top is None or path.is_relative_to(top / ".pstack"):
        return 0
    if git(top, "check-ignore", "-q", str(path)).returncode == 0:
        return 0

    status = top / ".pstack/status.md"
    if not has_line(status, "Value:"):
        exclude_pstack(top)
        return deny(VALUE_MESSAGE.format(status=status))
    if count_file(payload.get("session_id"), top, path) > MAX_ORCHESTRATOR_FILES and not has_line(
        status, "orchestrator-builds:"
    ):
        return deny(ORCHESTRATOR_MESSAGE)
    return 0


if __name__ == "__main__":
    sys.exit(main())

#!/usr/bin/env python3
import json
import re
import shlex
import sys


OPERAND = re.compile(r"^(?:[\w./~@:-]*[/:@])?\.env(\.[\w.-]+)?$", re.IGNORECASE)
SAFE_SUFFIX = re.compile(r"\.(example|sample|template|dist)$", re.IGNORECASE)
HEREDOC = re.compile(
    r"<<-?\s*(['\"]?)([A-Za-z_][\w]*)\1.*?^\s*\2\s*$",
    re.DOTALL | re.MULTILINE,
)


def operands(command: str):
    stripped = HEREDOC.sub(" ", command)
    try:
        tokens = shlex.split(stripped, comments=False)
    except ValueError:
        tokens = stripped.split()
    for token in tokens:
        yield token.strip("`'\"")


def main() -> int:
    try:
        payload = json.load(sys.stdin)
    except (json.JSONDecodeError, ValueError):
        return 0
    tool_input = payload.get("tool_input") or payload.get("toolInput") or {}
    paths = [tool_input.get(key) or "" for key in ("file_path", "path")]
    glob = (tool_input.get("glob") or "").replace("*", "").replace("?", "")
    tokens = [*operands(tool_input.get("command") or ""), *paths, glob]

    for token in tokens:
        name = token.split("=")[-1] if token.startswith("-") else token
        if not OPERAND.match(name) or SAFE_SUFFIX.search(name):
            continue
        print(
            f"Blocked: `{token}` is a .env file. Secrets are off limits — use "
            "`npx supabase status` for local service details, or the provider "
            "dashboard for hosted values. Ask the user if you need a variable name.",
            file=sys.stderr,
        )
        return 2
    return 0


if __name__ == "__main__":
    sys.exit(main())

#!/usr/bin/env python3
import json
import re
import shlex
import sys


OPERAND = re.compile(r"^(?:[\w./~@:-]*[/:@])?\.env(\.[\w.-]+)?$", re.IGNORECASE)
EMBEDDED = re.compile(r"(?:^|[\s'\"(=,:])((?:[\w.~@-]*/)*\.env(?:\.[\w-]+)*)(?=$|[\s'\"),;])", re.IGNORECASE)
SAFE_SUFFIX = re.compile(r"\.(example|sample|template|dist)$", re.IGNORECASE)
HEREDOC = re.compile(
    r"<<-?\s*(['\"]?)([A-Za-z_][\w]*)\1.*?^\s*\2\s*$",
    re.DOTALL | re.MULTILINE,
)


EXISTENCE_CHECKS = {"ls", "test", "[", "stat"}
SIMPLE_COMMAND_SPLIT = re.compile(r"(;|&&|\|\||\||\n)")
PIPE_READERS = {"xargs", "cat", "source", "."}
SUBSHELL = re.compile(r"\$\(|`")


def tokens_of(text: str):
    try:
        return shlex.split(text, comments=False)
    except ValueError:
        return text.split()


def operands(command: str):
    parts = SIMPLE_COMMAND_SPLIT.split(HEREDOC.sub(" ", command))
    for index in range(0, len(parts), 2):
        tokens = tokens_of(parts[index])
        if tokens and tokens[0] in EXISTENCE_CHECKS and not SUBSHELL.search(parts[index]):
            piped_to = tokens_of(parts[index + 2])[:1] if parts[index + 1:index + 2] == ["|"] else []
            if not set(piped_to) & PIPE_READERS:
                continue
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
        embedded = [path for path in EMBEDDED.findall(token) if not SAFE_SUFFIX.search(path)]
        if (not OPERAND.match(name) or SAFE_SUFFIX.search(name)) and not embedded:
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

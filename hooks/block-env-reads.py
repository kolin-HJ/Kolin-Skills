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


def parse_emit(argv):
    if "--emit" in argv:
        index = argv.index("--emit")
        if index + 1 < len(argv):
            return argv[index + 1]
    return "claude"


def main() -> int:
    emit = parse_emit(sys.argv[1:])
    try:
        payload = json.load(sys.stdin)
    except (json.JSONDecodeError, ValueError):
        if emit == "antigravity":
            print(json.dumps({"decision": "allow"}))
        return 0
    if not isinstance(payload, dict):
        if emit == "antigravity":
            print(json.dumps({"decision": "allow"}))
        return 0
    tool_call = payload.get("toolCall") if isinstance(payload.get("toolCall"), dict) else {}
    raw_input = payload.get("tool_input") or payload.get("toolInput") or tool_call.get("args") or {}
    tool_input = raw_input if isinstance(raw_input, dict) else {}
    paths = [tool_input.get(key) or "" for key in ("file_path", "path", "Path", "AbsolutePath", "TargetFile", "SearchPath", "SearchDirectory")]
    globs = [(tool_input.get(key) or "").replace("*", "").replace("?", "") for key in ("glob", "Pattern")]
    command = tool_input.get("command") or tool_input.get("CommandLine") or ""
    tokens = [*operands(command), *paths, *globs]

    for token in tokens:
        name = token.split("=")[-1] if token.startswith("-") else token
        embedded = [path for path in EMBEDDED.findall(token) if not SAFE_SUFFIX.search(path)]
        if (not OPERAND.match(name) or SAFE_SUFFIX.search(name)) and not embedded:
            continue
        message = (
            f"Blocked: `{token}` is a .env file, and agents do not read secrets. "
            "For local database values run `supabase status -o env`; "
            "for a variable name read `.env.example` or ask Kolin."
        )
        if emit == "antigravity":
            print(json.dumps({"decision": "deny", "reason": message}))
            return 0
        print(message, file=sys.stderr)
        return 2
    if emit == "antigravity":
        print(json.dumps({"decision": "allow"}))
    return 0


if __name__ == "__main__":
    sys.exit(main())

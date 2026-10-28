#!/usr/bin/env python3
import json
import pathlib
import re
import shlex
import sys
import uuid


SLOT = pathlib.Path.home() / ".kolin-skills/bin/heavy-slot.py"
TIMEOUT_MS = {False: (120_000, 600_000), True: (1_800_000, 7_200_000)}
HEREDOC = re.compile(
    r"<<-?\s*(['\"]?)([A-Za-z_][\w]*)\1.*?^\s*\2\s*$",
    re.DOTALL | re.MULTILINE,
)
QUOTED = re.compile(r"\"[^\"]*\"|'[^']*'")
POLL_LOOP = re.compile(r"\b(?:until|while|for)\b.*?\bdo\b(?:(?!\bdone\b).)*?\bsleep\s+(\d+(?:\.\d+)?)", re.DOTALL)
NESTED_SUBSHELL = re.compile(r"\$\([^()]*\)|`[^`]*`")
COMMAND_START = r"(?:^|[;&|(\n])\s*(?:\w+=\S*\s+)*"
HEAVY = re.compile(
    COMMAND_START + r"(?:"
    r"(?:pnpm|npm|yarn|bun)\s+(?:run\s+)?(?:check|verify|test|build|typecheck|lint)\b"
    r"|(?:npx\s+|bunx\s+|pnpm\s+(?:exec\s+)?)?(?:\S*/)?(?:vitest|tsc|playwright|turbo|next\s+build)\b"
    r"|git\s+(?:-C\s+\S+\s+)?push\b"
    r"|java\b.*\btlc2\.TLC\b"
    r")"
)
FILTERED_GATE = re.compile(
    r"(?:^|[;&|(\n])\s*(?P<gate>(?:\w+=\S*\s+)*(?:git\s+(?:-C\s+\S+\s+)?push\b|(?:npm|pnpm|yarn|bun)\s+(?:run\s+)?(?:check|verify)[\w:-]*)"
    r"(?:(?!&&|\|\||;|\n).)*?)(?P<filters>(?<!\|)\|(?!\|)\s*(?:grep|tail|head|awk|sed)\b)"
)
FILTER_STAGES = re.compile(r"(?:(?<!\|)\|(?!\|)\s*(?:grep|tail|head|awk|sed)\b(?:2>&1|\\[^\n]|[^;&|\n)\\])*)+")
TRAILING_STAGES = re.compile(r"(?:\|(?!\|)(?:\\[^\n]|[^;&|\n)\\])*)+")
TRAILING_REDIRECT = re.compile(r"\s*2>&1\s*$")
STATUS_FLAG = re.compile(r"\s(?:-[a-zA-Z]*[qcl][a-zA-Z]*|--(?:quiet|silent|count|files-with-matches))\b")
MASKED = re.compile(rf"(?ms:{HEREDOC.pattern})|\"(?:\\.|[^\"\\])*\"|'[^']*'")
LONG_CURL_RETRY = re.compile(r"\bcurl\b[^;&|\n]*?--retry(?:\s+|=)(\d+)")
UNQUOTED_GLOB = re.compile(
    rf"(?ms:{HEREDOC.pattern})|{QUOTED.pattern}"
    r"|(--(?:include|exclude|exclude-dir))=([^\s'\"$]*[*?\[][^\s'\"$]*)"
)
LONG_LIVED = re.compile(r"--watch\b|\bwatch\b|\bdev\b")
POLL_MESSAGE = (
    "Blocked: a foreground sleep loop holds the turn until the Bash timeout. "
    "Run the job with run_in_background: true, or wait for a file, port or log line with Monitor and an until-loop."
)
GATE_LOG_NOTE = "The hook saved the gate's full output to {logs} and ran your filter on that file. Read it for the whole output."
CURL_RETRY_MESSAGE = (
    "Blocked: a foreground curl with more than 10 retries holds the turn and keeps retrying a dead server. "
    "Start the server with run_in_background, then wait with Monitor in an until-loop that also exits when the server dies."
)

DOCKER_DB = re.compile(
    COMMAND_START + r"docker(?:-compose)?\b[^\n]*\b(?:supabase|postgres|psql|pg_dump)",
    re.IGNORECASE,
)
DOCKER_DB_MESSAGE = (
    "Blocked: local Supabase and Postgres run in the Supabase CLI's native runtime, never in Docker "
    "(see the local-supabase skill). Run `supabase start --runtime native --output-format json`, "
    "connect with its env.DB_URL, and carry on with the task."
)


def quote_globs(command: str) -> str:
    return UNQUOTED_GLOB.sub(
        lambda match: match.group(0) if match.group(3) is None else f"{match.group(3)}='{match.group(4)}'",
        command,
    )


def drop_gate_filters(command: str):
    logs = []
    while True:
        masked = MASKED.sub(lambda match: "x" * len(match.group(0)), command)
        gate = FILTERED_GATE.search(masked)
        if gate is None:
            return command, logs
        start = gate.start("filters")
        end = FILTER_STAGES.match(masked, start).end()
        trailing = TRAILING_STAGES.match(masked, end)
        end = trailing.end() if trailing else end
        stages = masked[start:end].replace("2>&1", "")
        spacing = command[start:end][len(command[start:end].rstrip()):]
        if not (trailing or ">" in stages or "\\" in stages or STATUS_FLAG.search(stages)):
            command = command[:start].rstrip(" \t") + spacing + command[end:]
            continue
        log = f"/tmp/gate-{uuid.uuid4().hex[:8]}.log"
        logs.append(log)
        gate_text = TRAILING_REDIRECT.sub("", command[gate.start("gate"):start].rstrip())
        block = f"{{ {gate_text} > {log} 2>&1; cat {log} {command[start:end].rstrip()}; }}{spacing}"
        command = command[:gate.start("gate")] + block + command[end:]


def main() -> int:
    try:
        payload = json.load(sys.stdin)
    except (json.JSONDecodeError, ValueError):
        return 0
    tool_input = payload.get("tool_input") or {}
    command = tool_input.get("command") or ""
    background = bool(tool_input.get("run_in_background"))
    code = QUOTED.sub(" ", HEREDOC.sub(" ", command))

    if DOCKER_DB.search(code):
        print(DOCKER_DB_MESSAGE, file=sys.stderr)
        return 2

    heavy = HEAVY.search(code) and not LONG_LIVED.search(code)
    command, gate_logs = drop_gate_filters(command)
    code = QUOTED.sub(" ", HEREDOC.sub(" ", command))

    retry = LONG_CURL_RETRY.search(code)
    if retry and int(retry.group(1)) > 10 and not background:
        print(CURL_RETRY_MESSAGE, file=sys.stderr)
        return 2

    poll_code = code
    while (stripped := NESTED_SUBSHELL.sub(" ", poll_code)) != poll_code:
        poll_code = stripped
    poll = POLL_LOOP.search(poll_code)
    if poll and float(poll.group(1)) >= 2 and not background:
        print(POLL_MESSAGE, file=sys.stderr)
        return 2

    updated = {**tool_input, "command": quote_globs(command)}
    if heavy:
        default_ms, ceiling_ms = TIMEOUT_MS[background]
        timeout_ms = tool_input.get("timeout") or default_ms
        max_wait_ms = max(0, min(timeout_ms // 2, ceiling_ms - timeout_ms))
        prefix = f"python3 {shlex.quote(str(SLOT))} $$ {max_wait_ms // 1000}\n"
        updated = {**updated, "command": prefix + updated["command"], "timeout": timeout_ms + max_wait_ms}
    if updated == tool_input:
        return 0
    output = {"hookEventName": "PreToolUse", "updatedInput": updated}
    if gate_logs:
        output["additionalContext"] = GATE_LOG_NOTE.format(logs=", ".join(gate_logs))
    print(json.dumps({"hookSpecificOutput": output}))
    return 0


if __name__ == "__main__":
    sys.exit(main())

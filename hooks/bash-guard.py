#!/usr/bin/env python3
import json
import pathlib
import re
import shlex
import subprocess
import sys
import uuid


SLOT = pathlib.Path.home() / ".kolin-skills/bin/heavy-slot.py"
TIMEOUT_MS = {False: (120_000, 600_000), True: (1_800_000, 7_200_000)}
HEREDOC = re.compile(
    r"<<-?\s*(['\"]?)([A-Za-z_][\w]*)\1.*?^\s*\2\s*$",
    re.DOTALL | re.MULTILINE,
)
QUOTED = re.compile(r"\"[^\"]*\"|'[^']*'")
COMMAND_START = r"(?:^|[;&|(\n])\s*(?:\w+=\S*\s+)*"
HEAVY = re.compile(
    COMMAND_START + r"(?:"
    r"(?:pnpm|npm|yarn|bun)\s+(?:run\s+)?(?:check|verify|test|build|typecheck|lint|model-check)\b"
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
UNQUOTED_GLOB = re.compile(
    rf"(?ms:{HEREDOC.pattern})|{QUOTED.pattern}"
    r"|(--(?:include|exclude|exclude-dir))=([^\s'\"$]*[*?\[][^\s'\"$]*)"
)
LONG_LIVED = re.compile(r"--watch\b|\bwatch\b|\bdev\b")
GATE_LOG_NOTE = "The hook saved the gate's full output to {logs} and ran your filter on that file. Read it for the whole output."

DOCKER_DB = re.compile(
    COMMAND_START + r"docker(?:-compose)?\b[^\n]*\b(?:supabase|postgres|psql|pg_dump)",
    re.IGNORECASE,
)
DOCKER_DB_MESSAGE = (
    "Blocked: local Supabase and Postgres run in the Supabase CLI's native runtime, never in Docker "
    "(see the local-supabase skill). On Darwin x86_64, native is unsupported; run `pglite-replay` and "
    "carry on with the task. Elsewhere, run `supabase start --runtime native --output-format json`, "
    "connect with its env.DB_URL, and carry on with the task."
)
SLEEP = re.compile(COMMAND_START + r"sleep\s+(\d+(?:\.\d+)?)([smhd]?)(?![\w.])(?!\s*&(?!&))")
SLEEP_UNIT_SECONDS = {"": 1, "s": 1, "m": 60, "h": 3600, "d": 86400}
POLL_SECONDS = 5
POLL_LOOP = re.compile(
    COMMAND_START + r"(?:until|while)\b(?!\s+(?:IFS=\S*\s+)?read\b)(?:(?!\bdone\b).)*?\bdo\b(?:(?!\bdone\b).)*?\bsleep\b",
    re.DOTALL,
)
POLL_MESSAGE = (
    "Blocked: this command waits by polling (a `sleep` of 5 s or more, or an until/while loop that sleeps). "
    "Run the job itself with run_in_background: true, then wait for its completion notification with "
    "t3_background_wait or Monitor, and do other work meanwhile."
)
SLOT_ROOM_MESSAGE = (
    "Blocked: this heavy job asks for {seconds} s in the foreground, which leaves no time to wait for one of the "
    "heavy-job slots. Run it with run_in_background: true and wait with t3_background_wait or Monitor, "
    "or pass a timeout of {limit} ms or less."
)
MERGE = re.compile(COMMAND_START + r"gh\s+pr\s+merge\b([^;&|)\n]*)")
REPO_FLAG = re.compile(r"(?:--repo[=\s]|-R\s*)(\S+)")
AUTO_FLAG = re.compile(r"(?:^|\s)--auto(?:\s|=|$)")
NO_CHECKS = re.compile(r"no required checks|no checks reported", re.I)
GH_TIMEOUT = 20


def run_gh(cwd, args):
    try:
        return subprocess.run(
            ["gh", *args], cwd=cwd, capture_output=True, text=True, errors="replace", timeout=GH_TIMEOUT,
        )
    except (subprocess.TimeoutExpired, OSError) as error:
        return subprocess.CompletedProcess(["gh", *args], 1, "", str(error))


def parse_checks(result):
    detail = (result.stderr or result.stdout).strip()[-200:]
    text = f"{result.stdout}\n{result.stderr}"
    parsed = None
    if result.stdout.strip():
        try:
            parsed = json.loads(result.stdout)
        except ValueError:
            parsed = ()
        if isinstance(parsed, list):
            return parsed, None
        if NO_CHECKS.search(text):
            return [], None
        return None, detail or "no output"
    if NO_CHECKS.search(text):
        return [], None
    if result.returncode:
        return None, detail or "no output"
    return [], None


def not_green(rows, required):
    ok = {"pass"} if required else {"pass", "skipping"}
    return any(str(row.get("bucket") or "").lower() not in ok for row in rows)


def watch_fix(pr, required=True):
    flag = " --required" if required else ""
    return f"Run `gh pr checks {pr} --watch{flag} --fail-fast`, then fix any red check."


def merge_block(rest, cwd):
    if AUTO_FLAG.search(rest):
        return None
    repo = REPO_FLAG.search(rest)
    repo_args = ["--repo", repo.group(1)] if repo else []
    words = [word for word in REPO_FLAG.sub(" ", rest).split() if not word.startswith("-") and ">" not in word]
    pr = words[0] if words else None
    shown = pr or "<pr>"
    selector = [pr] if pr else []
    required, err = parse_checks(
        run_gh(cwd, ["pr", "checks", *selector, "--required", "--json", "name,bucket", *repo_args]),
    )
    if err:
        return f"Blocked: gh pr checks failed: {err}. {watch_fix(shown)}"
    if required:
        if not_green(required, True):
            return f"Blocked: required checks are not all green. {watch_fix(shown)}"
        return None
    all_rows, err = parse_checks(
        run_gh(cwd, ["pr", "checks", *selector, "--json", "name,bucket", *repo_args]),
    )
    if err:
        return f"Blocked: gh pr checks failed: {err}. {watch_fix(shown, False)}"
    if not all_rows:
        return f"Blocked: required checks are not all green (no checks found). {watch_fix(shown, False)}"
    if not_green(all_rows, False):
        return f"Blocked: required checks are not all green. {watch_fix(shown, False)}"
    return None


def polls(code):
    long_sleep = any(
        float(match.group(1)) * SLEEP_UNIT_SECONDS[match.group(2)] >= POLL_SECONDS for match in SLEEP.finditer(code)
    )
    return long_sleep or POLL_LOOP.search(code) is not None


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
    claude = sys.argv[1:] != ["--client", "codex"]
    tool_input = payload.get("tool_input") or payload.get("toolInput") or {}
    command = tool_input.get("command") or ""
    background = bool(tool_input.get("run_in_background"))
    code = QUOTED.sub(" ", HEREDOC.sub(" ", command))

    if DOCKER_DB.search(code):
        print(DOCKER_DB_MESSAGE, file=sys.stderr)
        return 2
    if claude and not background and polls(code):
        print(POLL_MESSAGE, file=sys.stderr)
        return 2
    merge = MERGE.search(code)
    if merge:
        blocked = merge_block(merge.group(1), payload.get("cwd") or ".")
        if blocked:
            print(blocked, file=sys.stderr)
            return 2

    heavy = HEAVY.search(code) and not LONG_LIVED.search(code)
    command, gate_logs = drop_gate_filters(command)

    updated = {**tool_input, "command": quote_globs(command)}
    if heavy:
        default_ms, ceiling_ms = TIMEOUT_MS[background]
        timeout_ms = tool_input.get("timeout") or default_ms
        max_wait_ms = max(0, min(timeout_ms // 2, ceiling_ms - timeout_ms))
        if claude and not background and max_wait_ms < timeout_ms // 2:
            limit = ceiling_ms * 2 // 3
            print(SLOT_ROOM_MESSAGE.format(seconds=timeout_ms // 1000, limit=limit), file=sys.stderr)
            return 2
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

#!/usr/bin/env python3
import json
import pathlib
import re
import shlex
import subprocess
import sys
from dataclasses import dataclass, field


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
    COMMAND_START + r"(?:git\s+(?:-C\s+\S+\s+)?push\b|(?:npm|pnpm|yarn|bun)\s+(?:run\s+)?(?:check|verify)[\w:-]*)"
    r"(?:(?!&&|\|\||;|\n).)*?(?P<filters>(?<!\|)\|(?!\|)\s*(?:grep|tail|head|awk|sed)\b)"
)
FILTER_STAGES = re.compile(r"(?:(?<!\|)\|(?!\|)\s*(?:grep|tail|head|awk|sed)\b(?:2>&1|[^;&|\n])*)+")
STATUS_FLAG = re.compile(r"\s(?:-[a-zA-Z]*[qcl][a-zA-Z]*|--(?:quiet|silent|count|files-with-matches))\b")
MASKED = re.compile(rf"(?ms:{HEREDOC.pattern})|{QUOTED.pattern}")
LONG_CURL_RETRY = re.compile(r"\bcurl\b[^;&|\n]*?--retry(?:\s+|=)(\d+)")
UNQUOTED_GLOB = re.compile(
    rf"(?ms:{HEREDOC.pattern})|{QUOTED.pattern}"
    r"|(--(?:include|exclude|exclude-dir))=([^\s'\"$]*[*?\[][^\s'\"$]*)"
)
SEGMENT = re.compile(r"(?:\"[^\"]*\"|'[^']*'|[^;&|\n\"'])+")
TOKEN = re.compile(r"(?:\"[^\"]*\"|'[^']*'|\S)+")
SCRATCH_PATH = re.compile(r"^(?:/tmp/|/private/tmp/|\$TMPDIR/|\$\{TMPDIR\}/|/dev/null$)|(?:^|/)\.(?:pstack|scratch)/")
ASSIGNMENT = re.compile(r"^\s*(\w+)=(.*)$", re.DOTALL)
SCRATCH_VALUE = re.compile(
    r"^(?:\$\(\s*mktemp\b(?:\s+-\w+)*(?:\s+(?:/tmp/|/private/tmp/|\$TMPDIR/)[^\s)]*)?\s*\)(?:/\S*)?"
    r"|(?:/tmp|/private/tmp)/\S*)$"
)
PLAIN_RELATIVE = re.compile(r"^[\w.][\w./-]*$")
DIRECTORY_WORD = re.compile(r"(?<![\w-])(?:cd|pushd|popd)(?![\w-])")
SHELL_KEYWORDS = ("do", "then", "else", "elif", "if", "while", "until", "time", "{", "!")
VARIABLE_PATH = re.compile(r"^\$(?:\{(\w+)\}|(\w+))(?:/|$)")
HEREDOC_SCRIPT = re.compile(
    COMMAND_START + r"(?:python3?|node)\b[^\n<;&|]*<<-?\s*(['\"]?)(\w+)\1[^\n]*\n(.*?)^[ \t]*\2[ \t]*$",
    re.DOTALL | re.MULTILINE,
)
PY_WRITE_TEXT = re.compile(r"write_text\(")
PY_PATH_RECEIVER = re.compile(r"Path\(\s*(['\"])([^'\"]*)\1\s*\)\s*\.\s*$")
PY_OPEN_FOR_WRITE = re.compile(
    r"\bopen\(\s*(?:(['\"])([^'\"]*)\1|[^,)]*?)\s*,\s*(?:mode\s*=\s*)?['\"][wax][bt+]*['\"]"
)
NODE_WRITE = re.compile(r"(?:writeFile|writeFileSync|appendFile|appendFileSync|createWriteStream)\(\s*")
FIRST_ARG_LITERAL = re.compile(r"(['\"])([^'\"]*)\1")
HEREDOC_OPENER = re.compile(r"<<-?\s*(['\"]?)[A-Za-z_]\w*\1")
SED_IN_PLACE = re.compile(r"^(?:-[a-zA-Z]*i\S*|--in-place\S*)$")
PERL_IN_PLACE = re.compile(r"^-(?![MI])[a-zA-Z]*i")
INLINE_FLAG = {"python": "-c", "python3": "-c", "node": "-e"}
LONG_LIVED = re.compile(r"--watch\b|\bwatch\b|\bdev\b")
POLL_MESSAGE = (
    "Blocked: a sleep loop that polls holds this turn and hits the Bash timeout. "
    "Start the job with run_in_background: true and you are notified when it exits. "
    "To wait for a file, a port or a log line, use the Monitor tool with an until-loop."
)
SHELL_EDIT_MESSAGE = (
    "Blocked: edit files with the Edit or Write tool, so the lint hook sees each change and the diff is readable. "
    "Scratch output may go under /tmp, .pstack/ or .scratch/."
)
FILTERED_GATE_MESSAGE = (
    "Blocked: do not filter gate output; a failure line can hide. Run it plain; the harness saves long output "
    "to a file you can read."
)
CURL_RETRY_MESSAGE = (
    "Blocked: a long curl retry holds the turn and ignores a dead server; start the server with "
    "run_in_background and wait with Monitor, using an until-loop that also exits when the server process dies."
)

DOCKER_DB = re.compile(
    COMMAND_START + r"docker(?:-compose)?\b[^\n]*\b(?:supabase|postgres|psql|pg_dump)",
    re.IGNORECASE,
)
DOCKER_DB_MESSAGE = (
    "Blocked: local Supabase and Postgres run in the Supabase CLI's native runtime, one stack per checkout, "
    "never in Docker. Read ~/.agents/skills/local-supabase/SKILL.md: run `supabase start --runtime native "
    "--output-format json` and connect with its env.DB_URL. For a task already in progress, start the native "
    "stack against this checkout's supabase/ folder and carry on; do not ask Kolin to exempt this hook."
)


def is_scratch(path: str) -> bool:
    return ".." not in path.split("/") and bool(SCRATCH_PATH.search(path))


def outside_any_work_tree(path: str) -> bool:
    if not path.startswith(("/", "~")):
        return False
    target = pathlib.Path(path).expanduser().resolve()
    parent = target if path.endswith("/") else target.parent
    while not parent.exists():
        parent = parent.parent
    probe = subprocess.run(
        ["git", "-C", str(parent), "rev-parse", "--is-inside-work-tree"], capture_output=True, text=True
    )
    return probe.returncode != 0


@dataclass
class ScratchContext:
    in_scratch_dir: bool = False
    scratch_names: set = field(default_factory=set)

    def accepts(self, path: str) -> bool:
        path = path.strip("'\"")
        if is_scratch(path):
            return True
        if not path or ".." in path.split("/"):
            return False
        variable = VARIABLE_PATH.match(path)
        if variable:
            return (variable.group(1) or variable.group(2)) in self.scratch_names
        return self.in_scratch_dir and bool(PLAIN_RELATIVE.match(path))

    def accepts_write(self, path: str) -> bool:
        if self.accepts(path):
            return True
        path = path.strip("'\"")
        return ".." not in path.split("/") and outside_any_work_tree(path)

    def enters_scratch_dir(self, segment: str, followed_by_and: bool) -> bool:
        tokens = TOKEN.findall(segment)
        return (
            followed_by_and
            and len(tokens) == 2
            and tokens[0] == "cd"
            and self.accepts(tokens[1].strip("'\"").rstrip("/") + "/")
        )

    def track(self, segment: str, followed_by_and: bool) -> None:
        if DIRECTORY_WORD.search(segment):
            self.in_scratch_dir = self.enters_scratch_dir(segment, followed_by_and)
            if self.in_scratch_dir:
                return
        assignment = ASSIGNMENT.match(segment)
        if assignment:
            name, value = assignment.group(1), assignment.group(2).strip()
            if SCRATCH_VALUE.match(value) and ".." not in value:
                self.scratch_names.add(name)
            else:
                self.scratch_names.discard(name)
            return
        self.scratch_names = {
            name for name in self.scratch_names if not re.search(rf"(?<![\w${{]){re.escape(name)}(?!\w)", segment)
        }


def write_targets(script: str):
    for match in PY_WRITE_TEXT.finditer(script):
        receiver = PY_PATH_RECEIVER.search(script[:match.start()])
        yield receiver.group(2) if receiver else None
    for match in PY_OPEN_FOR_WRITE.finditer(script):
        yield match.group(2)
    for match in NODE_WRITE.finditer(script):
        literal = FIRST_ARG_LITERAL.match(script, match.end())
        yield literal.group(2) if literal else None


def writes_outside_scratch(script: str, context: ScratchContext) -> bool:
    return any(target is None or not context.accepts_write(target) for target in write_targets(script))


def redirect_targets(tokens):
    for index, token in enumerate(tokens):
        if token in (">", ">>") and index + 1 < len(tokens):
            yield tokens[index + 1]
        elif re.match(r"^>>?[^>&]", token):
            yield token.lstrip(">")


def operands(tokens):
    return [token for token in tokens if not token.startswith(("-", ">"))]


def segment_edits_outside_scratch(tokens, context: ScratchContext) -> bool:
    while tokens and (tokens[0] in SHELL_KEYWORDS or re.match(r"^\w+=", tokens[0])):
        tokens = tokens[1:]
    if not tokens:
        return False
    command, args = tokens[0].rsplit("/", 1)[-1], tokens[1:]
    if command == "sed" and any(SED_IN_PLACE.match(arg) for arg in args):
        files = operands(args)[-1:]
    elif command == "perl" and any(PERL_IN_PLACE.match(arg) for arg in args):
        files = operands(args)[-1:]
    elif command in ("cat", "echo", "printf"):
        files = list(redirect_targets(args))
        return not all(context.accepts_write(path) for path in files)
    elif command == "tee":
        files = operands(args)
    elif command in INLINE_FLAG and INLINE_FLAG[command] in args:
        script = args[args.index(INLINE_FLAG[command]) + 1:][:1]
        return any(writes_outside_scratch(item, context) for item in script)
    else:
        return False
    return not files or not all(context.accepts_write(path) for path in files)


def heredoc_header_tail(match) -> str:
    text = match.group(0)
    return " " + text[HEREDOC_OPENER.match(text).end():].split("\n", 1)[0]


def tracked_segments(command: str):
    bare = HEREDOC.sub(heredoc_header_tail, command)
    context = ScratchContext()
    for segment in SEGMENT.finditer(bare):
        context.track(segment.group(0), bare.startswith("&&", segment.end()))
        yield segment.group(0), context


def context_before(command: str, start: int) -> ScratchContext:
    end = start + 1 if command[start:start + 1] in (";", "&", "|", "(", "\n") else start
    context = ScratchContext()
    for _, context in tracked_segments(command[:end]):
        pass
    return context


def heredoc_script_edits_outside_scratch(command: str, match) -> bool:
    script = match.group(3)
    context = ScratchContext() if "chdir" in script else context_before(command, match.start())
    return writes_outside_scratch(script, context)


def edits_files_from_shell(command: str) -> bool:
    if any(heredoc_script_edits_outside_scratch(command, match) for match in HEREDOC_SCRIPT.finditer(command)):
        return True
    return any(
        segment_edits_outside_scratch(TOKEN.findall(text), context)
        for text, context in tracked_segments(command)
    )


def quote_globs(command: str) -> str:
    return UNQUOTED_GLOB.sub(
        lambda match: match.group(0) if match.group(3) is None else f"{match.group(3)}='{match.group(4)}'",
        command,
    )


def drop_gate_filters(command: str):
    while True:
        masked = MASKED.sub(lambda match: "x" * len(match.group(0)), command)
        gate = FILTERED_GATE.search(masked)
        if gate is None:
            return command
        start = gate.start("filters")
        end = FILTER_STAGES.match(masked, start).end()
        stages = masked[start:end].replace("2>&1", "")
        unsafe = ")" in stages or ">" in stages or "\\" in stages or STATUS_FLAG.search(stages) or "$?" in masked[end:]
        if unsafe or masked[end:end + 1] not in ("", ";", "\n"):
            return None
        command = command[:start].rstrip(" \t") + command[end:]


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

    if edits_files_from_shell(command):
        print(SHELL_EDIT_MESSAGE, file=sys.stderr)
        return 2

    unfiltered = drop_gate_filters(command)
    if unfiltered is None:
        print(FILTERED_GATE_MESSAGE, file=sys.stderr)
        return 2
    command = unfiltered
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
    if HEAVY.search(code) and not LONG_LIVED.search(code):
        default_ms, ceiling_ms = TIMEOUT_MS[background]
        timeout_ms = tool_input.get("timeout") or default_ms
        max_wait_ms = max(0, min(timeout_ms // 2, ceiling_ms - timeout_ms))
        prefix = f"python3 {shlex.quote(str(SLOT))} $$ {max_wait_ms // 1000}\n"
        updated = {**updated, "command": prefix + updated["command"], "timeout": timeout_ms + max_wait_ms}
    if updated == tool_input:
        return 0
    print(json.dumps({"hookSpecificOutput": {"hookEventName": "PreToolUse", "updatedInput": updated}}))
    return 0


if __name__ == "__main__":
    sys.exit(main())

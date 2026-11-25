#!/usr/bin/env python3
import json
import pathlib
import re
import subprocess
import sys

import ag_notes

DIFF_AUDIT = pathlib.Path(__file__).resolve().parent.parent / "bin/diff-audit"
TRIGGER = re.compile(r"(?:^|[;&|(\n])\s*(?:\w+=\S*\s+)*gh\s+pr\s+(create|ready)\b([^;&|)\n]*)")
MCP_CREATE_TOOLS = {"mcp__t3-code__pull_request_create", "mcp_t3-code_pull_request_create"}
MCP_UPDATE_TOOLS = {"mcp__t3-code__pull_request_update", "mcp_t3-code_pull_request_update"}
REPO_FLAG = re.compile(r"(?:--repo[=\s]|-R\s*)(\S+)")
PR_URL = re.compile(r"https://github\.com/[\w.-]+/[\w.-]+/pull/\d+")
HTML_COMMENT = re.compile(r"<!--.*?(?:-->|\Z)", re.DOTALL)
HEREDOC = re.compile(r"<<-?\s*(['\"]?)([A-Za-z_][\w]*)\1.*?^\s*\2\s*$", re.DOTALL | re.MULTILINE)
QUOTED = re.compile(r"\"(?:\\.|[^\"\\])*\"|'[^']*'")
VERIFICATION = re.compile(r"^##[ \t]+Verification[ \t]*$(.*?)(?=^##[ \t]|\Z)", re.MULTILINE | re.DOTALL | re.IGNORECASE)
VISUAL_PROOF = re.compile(r"^##[ \t]+Visual[ \t]+proof[ \t]*$(.*?)(?=^##[ \t]|\Z)", re.MULTILINE | re.DOTALL | re.IGNORECASE)
VISUAL_EVIDENCE = re.compile(r"!\[[^\]]*\]\([^)]+\)|<img\b|<video\b|https?://\S+|\.(?:png|jpe?g|webp|gif|mp4|mov|webm)\b", re.IGNORECASE)
VISUAL_WAIVED = re.compile(r"^[ \t]*(?:[-*][ \t]*)?Not run:[ \t]*[^\n]*\b(?:visual|screenshots?|ui|videos?)\b[^\n]*\bbecause\b.*\S", re.MULTILINE | re.IGNORECASE)
UI_FILE = re.compile(r"\.(?:tsx|jsx)$")
TEST_FILE = re.compile(r"(?:\.test\.|\.spec\.|(^|/)(?:__tests__|tests?)/)")
EXCLUDED_SIZE_FILE = re.compile(
    r"(?:^|/)(?:package-lock\.json|pnpm-lock\.yaml|yarn\.lock|bun\.lockb?|Cargo\.lock|poetry\.lock|uv\.lock|Gemfile\.lock|composer\.lock)$"
    r"|\.(?:snap|min\.js|min\.css|generated\.\w+|d\.ts|md)$"
    r"|(?:^|/)(?:generated|__generated__|dist|build)/"
)
MAX_PR_LINES = 800
MAX_BODY_CHARS = 2500
UNFILLED = re.compile(r"<(?:command|result|check|why|kind|who and where|screenshot[^>]*)>|\b(?:TODO|TBD)\b")
LINE_START = r"^[ \t]*(?:[-*][ \t]*)?"
RAN_LINE = re.compile(LINE_START + r"Ran:[ \t]*\S", re.MULTILINE)
RAN_COMMAND = re.compile(LINE_START + r"Ran:[ \t]*`([^`]+)`", re.MULTILINE)
NOT_RUN_LINE = re.compile(LINE_START + r"Not run:[ \t]*\S.*\bbecause\b.*\S", re.MULTILINE | re.IGNORECASE)
AUDIT_WAIVED = re.compile(LINE_START + r"Not run:[ \t]*`?diff-audit`?,?[ \t]+because\b.*\S", re.MULTILINE | re.IGNORECASE)
ALLOWED = re.compile(LINE_START + r"Allowed ([\w-]+):[ \t]*\S", re.MULTILINE)
PR_FIELDS = "url,body,baseRefName,headRefName,headRefOid,isCrossRepository,isDraft,state"
NO_PR = "no pull requests found"
FORMAT = "`- Ran: `the command` the result` or `- Not run: the check, because the reason`"


def parse_emit(argv):
    if "--emit" in argv:
        index = argv.index("--emit")
        if index + 1 < len(argv):
            return argv[index + 1]
    return "claude"


def run(cwd, *args, timeout=30):
    try:
        return subprocess.run(args, cwd=cwd, capture_output=True, text=True, errors="replace", timeout=timeout)
    except (subprocess.TimeoutExpired, OSError) as error:
        return subprocess.CompletedProcess(args, 1, "", str(error))


def named_pr(verb, rest, payload):
    if verb == "create":
        return PR_URL.findall(json.dumps(payload.get("tool_response") or ""))[-1:]
    repo = REPO_FLAG.search(rest)
    words = [word for word in REPO_FLAG.sub(" ", rest).split() if not word.startswith("-") and ">" not in word]
    return [*words[:1], *(["--repo", repo.group(1)] if repo else [])]


def mcp_pr_selector(tool_name, tool_input, payload):
    if tool_name in MCP_CREATE_TOOLS:
        if tool_input.get("draft"):
            return None
        urls = PR_URL.findall(json.dumps(payload.get("tool_response") or ""))
        return urls[-1:]
    if tool_name in MCP_UPDATE_TOOLS:
        if tool_input.get("ready") is not True and tool_input.get("body") is None:
            return None
        if tool_input.get("ready") is False:
            return None
        urls = PR_URL.findall(json.dumps(payload.get("tool_response") or ""))
        if urls:
            return urls[-1:]
        selector = []
        if tool_input.get("number"):
            selector.append(str(tool_input["number"]))
        if tool_input.get("repository"):
            selector.extend(["--repo", str(tool_input["repository"])])
        return selector
    return None


def is_release(pr):
    return pr["baseRefName"] == "main" and pr["headRefName"] == "staging" and not pr["isCrossRepository"]


def tool_uses(path):
    with path.open(errors="ignore") as handle:
        for line in handle:
            if '"tool_use"' not in line and '"tool_calls"' not in line:
                continue
            try:
                record = json.loads(line)
            except ValueError:
                continue
            if not isinstance(record, dict):
                continue
            message = record.get("message")
            content = message.get("content") if isinstance(message, dict) else None
            for block in content if isinstance(content, list) else []:
                if isinstance(block, dict) and block.get("type") == "tool_use":
                    tool_input = block.get("input")
                    yield str(block.get("name") or ""), tool_input if isinstance(tool_input, dict) else {}
            for call in record.get("tool_calls") if isinstance(record.get("tool_calls"), list) else []:
                if not isinstance(call, dict):
                    continue
                name = str(call.get("name") or "")
                args = call.get("args") or call.get("arguments") or {}
                if isinstance(args, str):
                    try:
                        args = json.loads(args)
                    except ValueError:
                        args = {}
                if not isinstance(args, dict):
                    args = {}
                if name == "run_command":
                    yield "Bash", {"command": str(args.get("CommandLine") or args.get("command") or "")}
                else:
                    yield name, args


def session_tool_uses(transcript):
    main = pathlib.Path(transcript)
    files = [main, *sorted(main.with_suffix("").glob("subagents/*.jsonl"))] if transcript and main.is_file() else []
    return [use for path in files for use in tool_uses(path)]


def audit_problems(base, body, cwd):
    allowed = [f"--allow={kind}" for kind in ALLOWED.findall(body)]
    result = run(cwd, sys.executable, str(DIFF_AUDIT), base, "HEAD", *allowed, timeout=60)
    blocks = [line[len("block "):] for line in result.stdout.splitlines() if line.startswith("block ")]
    if result.returncode and not blocks:
        return [f"diff-audit could not run ({result.stderr.strip()[-200:]}), so nothing checked this diff for slop. Fix that, or add a filled-in line `- Not run: diff-audit, because ...`."]
    return [f"diff-audit: {block}. Fix it, or add a filled-in line `Allowed <kind>: ...`." for block in blocks]


def without_quoted_text(command):
    return QUOTED.sub(" ", HEREDOC.sub(" ", command))


def unseen_ran_lines(section, uses):
    commands = [without_quoted_text(str(tool_input.get("command") or "")) for name, tool_input in uses if name == "Bash"]
    return [ran for ran in RAN_COMMAND.findall(section) if not any(without_quoted_text(ran) in command for command in commands)] if commands else []


def ui_changed_files(base, cwd):
    listed = run(cwd, "git", "diff", "--name-only", f"{base}...HEAD")
    if listed.returncode:
        return []
    return [path for path in listed.stdout.splitlines() if UI_FILE.search(path) and not TEST_FILE.search(path)]


def non_test_changed_lines(base, cwd):
    listed = run(cwd, "git", "diff", "--numstat", f"{base}...HEAD")
    if listed.returncode:
        return 0
    total = 0
    for line in listed.stdout.splitlines():
        parts = line.split("\t", 2)
        if len(parts) != 3 or parts[0] == "-" or parts[1] == "-":
            continue
        path = parts[2]
        if TEST_FILE.search(path) or EXCLUDED_SIZE_FILE.search(path):
            continue
        total += int(parts[0]) + int(parts[1])
    return total


def check(pr, payload, cwd):
    visible = HTML_COMMENT.sub("", pr["body"] or "")
    body = "\n".join(line for line in visible.splitlines() if not UNFILLED.search(line))
    match = VERIFICATION.search(body)
    section = match.group(1) if match else ""
    problems, notes = [], []
    if not RAN_LINE.search(section) and not NOT_RUN_LINE.search(section):
        problems.append(f"The body has no filled-in `## Verification` section with one line per check: {FORMAT}.")
    if len(visible) > MAX_BODY_CHARS:
        notes.append(f"PR body is {len(visible):,} chars (target ~1,500 chars); trim it to one screen with `pr-body`.")
    base_ref = pr["baseRefName"]
    base = f"origin/{base_ref}"
    fetched = run(cwd, "git", "fetch", "-q", "origin", f"+refs/heads/{base_ref}:refs/remotes/{base}")
    if fetched.returncode:
        notes.append(f"pr-proof could not fetch {base}, so it compared against the last copy it has: {fetched.stderr.strip()[-200:]}")
    if run(cwd, "git", "rev-parse", "HEAD").stdout.strip() != pr["headRefOid"]:
        notes.append("This checkout's HEAD is not the PR's head, so pr-proof did not check the diff. Push your commits, or check the PR from its own branch.")
        return problems, notes
    ui_files = ui_changed_files(base, cwd)
    visual = VISUAL_PROOF.search(body)
    visual_section = visual.group(1) if visual else ""
    if ui_files and not VISUAL_EVIDENCE.search(visual_section) and not VISUAL_WAIVED.search(body):
        problems.append(
            f"The diff changes UI files ({', '.join(ui_files[:3])}) with no filled-in `## Visual proof` 390 px and 1440 px screenshots "
            "(or `- Not run: visual proof, because <why>`)."
        )
    changed = non_test_changed_lines(base, cwd)
    allowed_kinds = set(ALLOWED.findall(body))
    if changed > MAX_PR_LINES and "large-pr" not in allowed_kinds:
        problems.append(
            f"Diff has {changed:,} non-test changed lines (limit {MAX_PR_LINES}; policy stacks PRs over ~600 lines). "
            "Stack it into smaller PRs, or add a filled-in line `Allowed large-pr: <why>`."
        )
    if not AUDIT_WAIVED.search(section):
        problems += audit_problems(base, body, cwd)
    uses = session_tool_uses(payload.get("transcript_path") or payload.get("transcriptPath") or "")
    unseen = unseen_ran_lines(section, uses)
    if unseen:
        notes.append("These `Ran:` lines match no command in this session, so check that each really ran, or say what ran it: " + "; ".join(unseen[:5]))
    return problems, notes


def finish_ok(emit, payload=None, note=None):
    if emit == "antigravity":
        if note:
            ag_notes.append_note(payload, note)
        print("{}")
        return 0
    if note:
        print(json.dumps({"hookSpecificOutput": {"hookEventName": "PostToolUse", "additionalContext": note}}))
    return 0


def main():
    emit = parse_emit(sys.argv[1:])
    try:
        payload = json.load(sys.stdin)
    except (json.JSONDecodeError, ValueError):
        return finish_ok(emit)
    if not isinstance(payload, dict):
        return finish_ok(emit)
    tool_call = payload.get("toolCall") if isinstance(payload.get("toolCall"), dict) else {}
    tool_name = str(payload.get("tool_name") or payload.get("toolName") or tool_call.get("name") or "")
    raw_input = payload.get("tool_input") or payload.get("toolInput") or tool_call.get("args") or {}
    tool_input = raw_input if isinstance(raw_input, dict) else {}
    if tool_name in MCP_CREATE_TOOLS or tool_name in MCP_UPDATE_TOOLS:
        selector = mcp_pr_selector(tool_name, tool_input, payload)
        if selector is None:
            return finish_ok(emit)
    else:
        command = str(tool_input.get("command") or tool_input.get("CommandLine") or "")
        trigger = TRIGGER.search(without_quoted_text(command))
        if not trigger:
            return finish_ok(emit)
        selector = named_pr(*trigger.groups(), payload)
    cwd = payload.get("cwd") or "."
    result = run(cwd, "gh", "pr", "view", *selector, "--json", PR_FIELDS)
    if result.returncode:
        if NO_PR not in result.stderr:
            return finish_ok(emit, payload, f"pr-proof could not read the PR, so it checked nothing: {result.stderr.strip()[-200:]}")
        return finish_ok(emit)
    try:
        pr = json.loads(result.stdout)
    except ValueError:
        return finish_ok(emit, payload, f"pr-proof could not parse the PR from gh, so it checked nothing: {result.stdout.strip()[:200]}")
    if pr["state"] != "OPEN" or pr["isDraft"] or is_release(pr):
        return finish_ok(emit)
    problems, notes = check(pr, payload, cwd)
    if problems:
        undo = run(cwd, "gh", "pr", "ready", pr["url"], "--undo")
        drafted = "It is now a draft." if undo.returncode == 0 else f"Marking it draft failed: {undo.stderr.strip()[-200:]}"
        message = (
            f"This PR is not ready for Kolin to trust yet. {drafted} "
            "Fix these, update it with `gh pr edit` or `pull_request_update`, then mark it ready.\n- "
            + "\n- ".join(problems)
        )
        if emit == "antigravity":
            ag_notes.append_note(payload, message)
            print("{}")
            return 0
        print(message, file=sys.stderr)
        return 2
    if notes:
        return finish_ok(emit, payload, " ".join(notes))
    return finish_ok(emit)


if __name__ == "__main__":
    sys.exit(main())

#!/usr/bin/env python3
import json
import pathlib
import re
import subprocess
import sys

DIFF_AUDIT = pathlib.Path(__file__).resolve().parent.parent / "bin/diff-audit"
TRIGGER = re.compile(r"(?:^|[;&|(\n])\s*(?:\w+=\S*\s+)*gh\s+pr\s+(create|ready)\b([^;&|)\n]*)")
REPO_FLAG = re.compile(r"(?:--repo[=\s]|-R\s*)(\S+)")
PR_URL = re.compile(r"https://github\.com/[\w.-]+/[\w.-]+/pull/\d+")
HTML_COMMENT = re.compile(r"<!--.*?(?:-->|\Z)", re.DOTALL)
HEREDOC = re.compile(r"<<-?\s*(['\"]?)([A-Za-z_][\w]*)\1.*?^\s*\2\s*$", re.DOTALL | re.MULTILINE)
QUOTED = re.compile(r"\"(?:\\.|[^\"\\])*\"|'[^']*'")
VERIFICATION = re.compile(r"^##[ \t]+Verification[ \t]*$(.*?)(?=^##[ \t]|\Z)", re.MULTILINE | re.DOTALL)
UNFILLED = re.compile(r"<(?:command|result|check|why|kind|who and where)>|\b(?:TODO|TBD)\b")
LINE_START = r"^[ \t]*(?:[-*][ \t]*)?"
RAN_LINE = re.compile(LINE_START + r"Ran:[ \t]*\S", re.MULTILINE)
RAN_COMMAND = re.compile(LINE_START + r"Ran:[ \t]*`([^`]+)`", re.MULTILINE)
NOT_RUN_LINE = re.compile(LINE_START + r"Not run:[ \t]*\S.*\bbecause\b.*\S", re.MULTILINE | re.IGNORECASE)
REVIEW_STATED = re.compile(LINE_START + r"(?:Ran:[ \t]*`?(?:fresh[ \t]+)?(?:review[ \t]+by|senior-reviewer|interrogate)\b.*\S|Not run:[ \t]*`?(?:fresh[ \t]+)?review`?,?[ \t]+because\b.*\S)", re.MULTILINE | re.IGNORECASE)
AUDIT_WAIVED = re.compile(LINE_START + r"Not run:[ \t]*`?diff-audit`?,?[ \t]+because\b.*\S", re.MULTILINE | re.IGNORECASE)
ALLOWED = re.compile(LINE_START + r"Allowed ([\w-]+):[ \t]*\S", re.MULTILINE)
REVIEW_LINES = 150
WORD_BREAK = re.compile(r"(?<=[a-z])(?=[A-Z])")
RISKY_PATH = re.compile(r"(?:^|[/_.-])(?:auth|authz|permissions?|access|roles?|rls|polic(?:y|ies)|schema|migrations?|billing|payments?|stripe)(?:[/_.-]|$)|\.sql$", re.IGNORECASE)
GENERATED_PATH = re.compile(r"(?:^|/)(?:pnpm-lock\.yaml|package-lock\.json|yarn\.lock|bun\.lockb?|Cargo\.lock|poetry\.lock)$|\.generated\.|(?:^|/)dist/")
REVIEW_SKILLS = {"interrogate"}
PR_FIELDS = "url,body,baseRefName,headRefName,headRefOid,isCrossRepository,isDraft,state"
NO_PR = "no pull requests found"
FORMAT = "`- Ran: `the command` the result` or `- Not run: the check, because the reason`"


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


def is_release(pr):
    return pr["baseRefName"] == "main" and pr["headRefName"] == "staging" and not pr["isCrossRepository"]


def needs_review(base, cwd):
    result = run(cwd, "git", "diff", "--numstat", f"{base}...HEAD")
    if result.returncode:
        return f"pr-proof could not read its diff ({result.stderr.strip()[-200:]})"
    changed = 0
    risky = []
    for line in result.stdout.splitlines():
        added, removed, path = line.split("\t", 2)
        if GENERATED_PATH.search(path):
            continue
        changed += sum(int(count) for count in (added, removed) if count.isdigit())
        if RISKY_PATH.search(WORD_BREAK.sub("-", path)):
            risky.append(path)
    if risky:
        return f"it touches {', '.join(risky[:3])}"
    return f"it changes {changed} lines" if changed > REVIEW_LINES else None


def tool_uses(path):
    with path.open(errors="ignore") as handle:
        for line in handle:
            if '"tool_use"' not in line:
                continue
            try:
                record = json.loads(line)
            except ValueError:
                continue
            message = record.get("message") if isinstance(record, dict) else None
            content = message.get("content") if isinstance(message, dict) else None
            for block in content if isinstance(content, list) else []:
                if isinstance(block, dict) and block.get("type") == "tool_use":
                    tool_input = block.get("input")
                    yield str(block.get("name") or ""), tool_input if isinstance(tool_input, dict) else {}


def session_tool_uses(transcript):
    main = pathlib.Path(transcript)
    files = [main, *sorted(main.with_suffix("").glob("subagents/*.jsonl"))] if transcript and main.is_file() else []
    return [use for path in files for use in tool_uses(path)]


def is_review(name, tool_input):
    if name in ("Agent", "Task"):
        return "reviewer" in str(tool_input.get("subagent_type") or "").lower()
    if name == "Skill":
        return tool_input.get("skill") in REVIEW_SKILLS
    return name.endswith("delegate_task") and tool_input.get("role") == "review"


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


def check(pr, payload, cwd):
    visible = HTML_COMMENT.sub("", pr["body"] or "")
    body = "\n".join(line for line in visible.splitlines() if not UNFILLED.search(line))
    match = VERIFICATION.search(body)
    section = match.group(1) if match else ""
    problems, notes = [], []
    if not RAN_LINE.search(section) and not NOT_RUN_LINE.search(section):
        problems.append(f"The body has no filled-in `## Verification` section with one line per check: {FORMAT}.")
    base_ref = pr["baseRefName"]
    base = f"origin/{base_ref}"
    fetched = run(cwd, "git", "fetch", "-q", "origin", f"+refs/heads/{base_ref}:refs/remotes/{base}")
    if fetched.returncode:
        notes.append(f"pr-proof could not fetch {base}, so it compared against the last copy it has: {fetched.stderr.strip()[-200:]}")
    if run(cwd, "git", "rev-parse", "HEAD").stdout.strip() != pr["headRefOid"]:
        notes.append("This checkout's HEAD is not the PR's head, so pr-proof did not check the diff. Push your commits, or check the PR from its own branch.")
        return problems, notes
    if not AUDIT_WAIVED.search(section):
        problems += audit_problems(base, body, cwd)
    uses = session_tool_uses(payload.get("transcript_path") or "")
    reason = needs_review(base, cwd)
    if reason and not REVIEW_STATED.search(section):
        if not uses:
            notes.append(f"A fresh review is due because {reason}. pr-proof could not read this session's tool calls, so it did not confirm one ran.")
        elif not any(is_review(name, tool_input) for name, tool_input in uses):
            problems.append(f"No fresh review ran in this session, and one is due because {reason}. Run `interrogate` or `senior-reviewer`. If it ran elsewhere, add a filled-in line `- Ran: review by ...`. If it should not run, add `- Not run: review, because ...`.")
    unseen = unseen_ran_lines(section, uses)
    if unseen:
        notes.append("These `Ran:` lines match no command in this session, so check that each really ran, or say what ran it: " + "; ".join(unseen[:5]))
    return problems, notes


def say_note(text):
    print(json.dumps({"hookSpecificOutput": {"hookEventName": "PostToolUse", "additionalContext": text}}))


def main():
    try:
        payload = json.load(sys.stdin)
    except (json.JSONDecodeError, ValueError):
        return 0
    command = str((payload.get("tool_input") or {}).get("command") or "")
    trigger = TRIGGER.search(without_quoted_text(command))
    if not trigger:
        return 0
    cwd = payload.get("cwd") or "."
    result = run(cwd, "gh", "pr", "view", *named_pr(*trigger.groups(), payload), "--json", PR_FIELDS)
    if result.returncode:
        if NO_PR not in result.stderr:
            say_note(f"pr-proof could not read the PR, so it checked nothing: {result.stderr.strip()[-200:]}")
        return 0
    try:
        pr = json.loads(result.stdout)
    except ValueError:
        say_note(f"pr-proof could not parse the PR from gh, so it checked nothing: {result.stdout.strip()[:200]}")
        return 0
    if pr["state"] != "OPEN" or pr["isDraft"] or is_release(pr):
        return 0
    problems, notes = check(pr, payload, cwd)
    if problems:
        undo = run(cwd, "gh", "pr", "ready", pr["url"], "--undo")
        drafted = "It is now a draft." if undo.returncode == 0 else f"Marking it draft failed: {undo.stderr.strip()[-200:]}"
        print(f"This PR is not ready for Kolin to trust yet. {drafted} Fix these, update it with `gh pr edit`, then run `gh pr ready`.\n- " + "\n- ".join(problems), file=sys.stderr)
        return 2
    if notes:
        say_note(" ".join(notes))
    return 0


if __name__ == "__main__":
    sys.exit(main())

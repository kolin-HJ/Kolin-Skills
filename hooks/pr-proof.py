#!/usr/bin/env python3
import json
import pathlib
import re
import shlex
import subprocess
import sys

DIFF_AUDIT = pathlib.Path(__file__).resolve().parent.parent / "bin/diff-audit"
HEREDOC = re.compile(r"<<-?\s*(['\"]?)([A-Za-z_][\w]*)\1.*?^\s*\2\s*$", re.DOTALL | re.MULTILINE)
QUOTED = re.compile(r"\"(?:\\.|[^\"\\])*\"|'[^']*'")
PR_CREATE = re.compile(r"(?:^|[;&|(\n])\s*(?:\w+=\S*\s+)*gh\s+pr\s+create\b")
VERIFICATION = re.compile(r"^##\s+Verification\s*$(.*?)(?=^##\s|\Z)", re.MULTILINE | re.DOTALL)
CHECK_LINE = re.compile(r"^\s*[-*]?\s*(?:Ran|Not run):\s*\S", re.MULTILINE)
RAN_COMMAND = re.compile(r"^\s*[-*]?\s*Ran:\s*`([^`]+)`", re.MULTILINE)
REVIEW_WAIVED = re.compile(r"Not run:\s*(?:fresh\s+)?review\b.*\b(?:because|since)\b.*\S", re.IGNORECASE)
ALLOWED = re.compile(r"^\s*[-*]?\s*Allowed ([\w-]+):\s*\S", re.MULTILINE)
REVIEW_LINES = 150
RISKY_PATH = re.compile(r"migrations?/|schema|auth|permission|\brls\b|polic(?:y|ies)|payment|billing", re.IGNORECASE)
GENERATED_PATH = re.compile(r"(?:^|/)(?:pnpm-lock\.yaml|package-lock\.json|yarn\.lock|bun\.lockb?|Cargo\.lock|poetry\.lock)$|\.generated\.|(?:^|/)dist/")
REVIEW_SKILLS = {"interrogate", "council", "code-review"}


def git(cwd, *args):
    return subprocess.run(["git", *args], cwd=cwd, capture_output=True, text=True, timeout=20)


def command_words(command):
    try:
        return shlex.split(command, posix=True)
    except ValueError:
        return []


def body_text(command, cwd):
    words = command_words(command)
    for flag, value in zip(words, words[1:]):
        if flag in ("--body", "-b"):
            return value
        if flag in ("--body-file", "-F") and value != "-" and pathlib.Path(cwd, value).is_file():
            return pathlib.Path(cwd, value).read_text(errors="ignore")
    for word in words:
        if word.startswith("--body="):
            return word[len("--body="):]
    return command


def base_ref(command, cwd):
    named = re.search(r"(?:--base|-B)[= ]+['\"]?([\w./-]+)", command)
    candidates = [f"origin/{named.group(1)}"] if named else ["origin/staging", "origin/HEAD", "origin/main", "origin/master"]
    for ref in candidates:
        if git(cwd, "rev-parse", "--verify", "-q", ref).returncode == 0:
            return ref
    return None


def needs_review(base, cwd):
    changed = 0
    risky = []
    for line in git(cwd, "diff", "--numstat", f"{base}...HEAD").stdout.splitlines():
        added, removed, path = line.split("\t", 2)
        if GENERATED_PATH.search(path):
            continue
        changed += sum(int(count) for count in (added, removed) if count.isdigit())
        if RISKY_PATH.search(path):
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
                message = json.loads(line).get("message")
            except ValueError:
                continue
            content = message.get("content") if isinstance(message, dict) else None
            for block in content if isinstance(content, list) else []:
                if isinstance(block, dict) and block.get("type") == "tool_use":
                    yield block.get("name") or "", block.get("input") or {}


def session_tool_uses(transcript):
    main = pathlib.Path(transcript)
    files = [main, *sorted(main.with_suffix("").glob("subagents/*.jsonl"))] if main.is_file() else []
    return [use for path in files for use in tool_uses(path)]


def is_review(name, tool_input):
    if name in ("Agent", "Task"):
        return "review" in str(tool_input.get("subagent_type") or "").lower()
    if name == "Skill":
        return tool_input.get("skill") in REVIEW_SKILLS
    return name.endswith("delegate_task") and tool_input.get("role") == "review"


def audit_blocks(base, body, cwd):
    allowed = [f"--allow={kind}" for kind in ALLOWED.findall(body)]
    result = subprocess.run([sys.executable, str(DIFF_AUDIT), base, *allowed], cwd=cwd, capture_output=True, text=True, timeout=45)
    return [line[len("block "):] for line in result.stdout.splitlines() if line.startswith("block ")]


def problems_and_notes(command, payload, cwd):
    body = body_text(command, cwd)
    problems, notes = [], []
    section = VERIFICATION.search(body)
    if not section or not CHECK_LINE.search(section.group(1)):
        problems.append("The body has no `## Verification` section with one line per check: `Ran: <command> <result>` or `Not run: <check>, because <why>`.")
    base = base_ref(command, cwd)
    if base is None:
        notes.append("pr-proof could not find the base branch, so it did not check the diff or the review.")
        return problems, notes
    for block in audit_blocks(base, body, cwd):
        problems.append(f"diff-audit: {block}. Fix it, or add a line `Allowed <kind>: <why>` to the body.")
    uses = session_tool_uses(payload.get("transcript_path") or "")
    reason = needs_review(base, cwd)
    if reason and not REVIEW_WAIVED.search(body):
        if not uses:
            notes.append(f"A fresh review is due because {reason}. pr-proof could not read this session's transcript, so it did not confirm one ran.")
        elif not any(is_review(name, tool_input) for name, tool_input in uses):
            problems.append(f"No fresh review ran in this session, and one is due because {reason}. Run `interrogate` or `senior-reviewer`, or add `Not run: review, because <why>`.")
    commands = [str(tool_input.get("command") or "") for name, tool_input in uses if name == "Bash"]
    if commands:
        unseen = [ran for ran in RAN_COMMAND.findall(body) if not any(ran in command_run for command_run in commands)]
        if unseen:
            notes.append("These `Ran:` lines match no command in this session, so check that each really ran, or say what ran it: " + "; ".join(unseen[:5]))
    return problems, notes


def main():
    try:
        payload = json.load(sys.stdin)
    except (json.JSONDecodeError, ValueError):
        return 0
    command = (payload.get("tool_input") or {}).get("command") or ""
    if not PR_CREATE.search(QUOTED.sub(" ", HEREDOC.sub(" ", command))):
        return 0
    problems, notes = problems_and_notes(command, payload, payload.get("cwd") or ".")
    if problems:
        print("Blocked: this PR is not ready for Kolin to trust yet.\n- " + "\n- ".join(problems), file=sys.stderr)
        return 2
    if notes:
        print(json.dumps({"hookSpecificOutput": {"hookEventName": "PreToolUse", "additionalContext": " ".join(notes)}}))
    return 0


if __name__ == "__main__":
    sys.exit(main())

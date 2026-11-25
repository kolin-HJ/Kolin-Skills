import json
import os
import pathlib
import re
import sys

SEAT_FLOORS = {"senior-reviewer": "opus"}
MEETS_FLOOR = {"opus": ("opus", "fable", "mythos")}
SEAT_CEILINGS = {"poteto-agent": "sonnet"}
ABOVE_CEILING = {"sonnet": ("opus", "fable", "mythos")}
MODEL_REASON = re.compile(r"^Model reason:[ \t]*\S", re.M | re.I)
BUILT_IN_DEFAULTS = {"Explore": "sonnet"}
PINNED = re.compile(r"^model:[ \t]*(\S+)", re.M)
INTERROGATE_DESC = re.compile(
    r"(?:^|\b)interrogate\s*[:\-]"
    r"|\binterrogate\b[^\n]*\b(?:lens|review|audit|pass|diff|correctness|security|operations)\b"
    r"|\b(?:lens|review|audit|pass)\b[^\n]*\binterrogate\b",
    re.I,
)
INTERROGATE_PROMPT = re.compile(
    r"(?:^|\s)/interrogate\b"
    r"|\binterrogate\b[^.\n]{0,60}\b(?:lens|correctness|security|operations|adversarial)\b",
    re.I,
)
REVIEW_WARN_AFTER = 4
REVIEW_BLOCK_AFTER = 8


def definition(agent, cwd):
    folders = []
    directory = cwd
    while True:
        folders.append(os.path.join(directory, ".claude", "agents"))
        parent = os.path.dirname(directory)
        if parent == directory:
            break
        directory = parent
    for home in dict.fromkeys([os.environ.get("CLAUDE_CONFIG_DIR"), os.path.expanduser("~/.claude")]):
        if home:
            folders.append(os.path.join(home, "agents"))
    for folder in folders:
        path = os.path.join(folder, agent + ".md")
        if os.path.isfile(path):
            with open(path, encoding="utf-8") as handle:
                return handle.read()
    return None


def pinned_model(text):
    header = text.split("---", 2)[1] if text.startswith("---") else ""
    match = PINNED.search(header)
    return match.group(1) if match else None


def chosen_model(agent, cwd):
    text = definition(agent, cwd)
    if text is None and agent in BUILT_IN_DEFAULTS:
        return BUILT_IN_DEFAULTS[agent], f"{agent} ignores CLAUDE_CODE_SUBAGENT_MODEL, so it runs on {BUILT_IN_DEFAULTS[agent]} unless the call passes a model"
    seat = SEAT_FLOORS.get(agent)
    pinned = pinned_model(text) if seat and text else None
    if pinned and not any(tier in pinned.lower() for tier in MEETS_FLOOR[seat]):
        return seat, f"{agent} runs on {seat}; this repo's copy pins a lower model"
    return None, None


def is_interrogate_call(tool_input):
    desc = str(tool_input.get("description") or "")
    prompt = str(tool_input.get("prompt") or "")[:300]
    return bool(INTERROGATE_DESC.search(desc) or INTERROGATE_PROMPT.search(prompt))


def is_user_prompt(record):
    if record.get("type") != "user" or record.get("promptSource") == "system":
        return False
    if any(record.get(key) for key in ("isMeta", "isSidechain", "isCompactSummary", "origin")):
        return False
    message = record.get("message")
    content = message.get("content") if isinstance(message, dict) else None
    if isinstance(content, str):
        return True
    return isinstance(content, list) and not any(isinstance(block, dict) and block.get("type") == "tool_result" for block in content)


def reviews_since_user_spoke(transcript_path, exclude_id=None):
    if not transcript_path:
        return 0
    path = pathlib.Path(transcript_path)
    if not path.is_file():
        return 0
    seen = set()
    count = 0
    with path.open(errors="ignore") as handle:
        for line in handle:
            spoke = '"type":"user"' in line and '"toolUseResult"' not in line
            if not spoke and '"tool_use"' not in line:
                continue
            try:
                record = json.loads(line)
            except ValueError:
                continue
            if not isinstance(record, dict):
                continue
            if is_user_prompt(record):
                count = 0
                continue
            message = record.get("message")
            content = message.get("content") if isinstance(message, dict) else None
            for block in content if isinstance(content, list) else []:
                if not isinstance(block, dict) or block.get("type") != "tool_use":
                    continue
                if block.get("name") not in ("Agent", "Task"):
                    continue
                call_id = block.get("id")
                if call_id:
                    if call_id == exclude_id or call_id in seen:
                        continue
                    seen.add(call_id)
                inp = block.get("input") or {}
                if not isinstance(inp, dict):
                    continue
                agent = str(inp.get("subagent_type") or "")
                if agent == "senior-reviewer" or is_interrogate_call(inp):
                    count += 1
    return count


def main():
    event = json.load(sys.stdin)
    tool_input = event.get("tool_input") or {}
    agent = str(tool_input.get("subagent_type") or "")
    if agent == "Plan":
        print(
            "Blocked: Plan starts without CLAUDE.md or AGENTS.md. "
            "Use `senior-reviewer` (Opus, read-only) for a diff or a judgment call, or `Explore` (Sonnet) for search.",
            file=sys.stderr,
        )
        return 2

    updated = dict(tool_input)
    reasons = []
    interrogate = is_interrogate_call(tool_input)
    if agent in ("", "general-purpose") and interrogate:
        updated["subagent_type"] = "senior-reviewer"
        agent = "senior-reviewer"
        if not updated.get("model"):
            updated["model"] = "opus"
        reasons.append("Interrogate must run read-only; redirected general-purpose to senior-reviewer")

    notes = []
    ceiling = SEAT_CEILINGS.get(agent)
    asked = str(updated.get("model") or "").lower()
    if ceiling and any(tier in asked for tier in ABOVE_CEILING[ceiling]) and not MODEL_REASON.search(str(tool_input.get("prompt") or "")):
        updated["model"] = ceiling
        reasons.append(f"{agent} runs on {ceiling} unless the brief has a `Model reason:` line")
        notes.append(
            f"This {agent} runs on {ceiling}, not {asked}: the brief gives no reason for the higher model. "
            "To run one unit higher, add a `Model reason: <why this unit needs it>` line to the brief."
        )

    if not updated.get("model"):
        model, reason = chosen_model(agent, event.get("cwd") or os.getcwd())
        if model:
            updated["model"] = model
            reasons.append(reason)

    if agent == "senior-reviewer" or interrogate:
        prior = reviews_since_user_spoke(event.get("transcript_path") or "", exclude_id=event.get("tool_use_id"))
        if prior >= REVIEW_BLOCK_AFTER:
            print(
                f"Blocked: {prior} review subagents since Kolin's last message. "
                "Policy caps review at 1 pass plus 1 fix-delta re-check. "
                "Stop patching, report the open findings to Kolin, and wait for a reply.",
                file=sys.stderr,
            )
            return 2
        if prior >= REVIEW_WARN_AFTER:
            notes.append(
                f"This session spawned {prior} review subagents since Kolin's last message. "
                "Policy caps review at 1 pass plus 1 fix-delta re-check; "
                "if findings keep returning, stop patching, rethink the design, and tell Kolin."
            )

    if updated == tool_input and not notes:
        return 0
    output = {"hookEventName": "PreToolUse"}
    if updated != tool_input:
        output["permissionDecision"] = "allow"
        output["permissionDecisionReason"] = "; ".join(reasons)
        output["updatedInput"] = updated
    if notes:
        output["additionalContext"] = " ".join(notes)
    json.dump({"hookSpecificOutput": output}, sys.stdout)
    return 0


if __name__ == "__main__":
    sys.exit(main())

import json
import os
import pathlib
import re
import sys

import ag_notes

SEAT_FLOORS = {"senior-reviewer": "opus"}
MEETS_FLOOR = {"opus": ("opus", "fable", "mythos")}
SEAT_CEILINGS = {"poteto-agent": "sonnet"}
ABOVE_CEILING = {"sonnet": ("opus", "fable", "mythos")}
DELEGATE_TOOLS = {"mcp__t3-code__delegate_task", "mcp_t3-code_delegate_task"}
DELEGATE_SONNET_ROLES = {"implementation", "research", "test"}
DELEGATE_SONNET_MODEL = "claude-sonnet-5-5"
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


def parse_emit(argv):
    if "--emit" in argv:
        index = argv.index("--emit")
        if index + 1 < len(argv):
            return argv[index + 1]
    return "claude"


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
    desc = str(tool_input.get("description") or tool_input.get("title") or "")
    prompt = str(tool_input.get("prompt") or tool_input.get("task") or "")[:300]
    return bool(INTERROGATE_DESC.search(desc) or INTERROGATE_PROMPT.search(prompt))


def is_review_seat(agent, tool_input, tool_name=""):
    if tool_name in DELEGATE_TOOLS:
        role = str(tool_input.get("role") or "").lower()
        return role == "review" or is_interrogate_call(tool_input)
    return agent in ("senior-reviewer", "judge") or agent.endswith("-reviewer") or is_interrogate_call(tool_input)


def is_user_prompt(record):
    if record.get("type") == "USER_INPUT" or record.get("source") == "USER":
        return True
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
            spoke = ('"type":"user"' in line and '"toolUseResult"' not in line) or '"USER_INPUT"' in line or '"source":"USER"' in line or '"source": "USER"' in line
            if not spoke and '"tool_use"' not in line and '"tool_calls"' not in line:
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
                name = str(block.get("name") or "")
                if name not in ("Agent", "Task") and name not in DELEGATE_TOOLS:
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
                if is_review_seat(agent, inp, name):
                    count += 1
            for call in record.get("tool_calls") if isinstance(record.get("tool_calls"), list) else []:
                if not isinstance(call, dict):
                    continue
                name = str(call.get("name") or "")
                if name not in DELEGATE_TOOLS:
                    continue
                call_id = call.get("id")
                if call_id:
                    if call_id == exclude_id or call_id in seen:
                        continue
                    seen.add(call_id)
                args = call.get("args") or call.get("arguments") or {}
                if isinstance(args, str):
                    try:
                        args = json.loads(args)
                    except ValueError:
                        args = {}
                if isinstance(args, dict) and is_review_seat("", args, name):
                    count += 1
    return count


def sonnet_equivalent(asked):
    return DELEGATE_SONNET_MODEL if asked.startswith("claude-") else "sonnet"


def main():
    emit = parse_emit(sys.argv[1:])
    try:
        event = json.load(sys.stdin)
    except (json.JSONDecodeError, ValueError):
        if emit == "antigravity":
            print(json.dumps({"decision": "allow"}))
        return 0
    if not isinstance(event, dict):
        if emit == "antigravity":
            print(json.dumps({"decision": "allow"}))
        return 0
    tool_call = event.get("toolCall") if isinstance(event.get("toolCall"), dict) else {}
    tool_name = str(event.get("tool_name") or event.get("toolName") or tool_call.get("name") or "")
    raw_input = event.get("tool_input") or tool_call.get("args") or {}
    tool_input = raw_input if isinstance(raw_input, dict) else {}
    agent = str(tool_input.get("subagent_type") or "")
    is_delegate = tool_name in DELEGATE_TOOLS

    if not is_delegate and agent == "Plan":
        msg = (
            "Blocked: Plan starts without CLAUDE.md or AGENTS.md. "
            "Use `senior-reviewer` (Opus, read-only) for a diff or a judgment call, or `Explore` (Sonnet) for search."
        )
        if emit == "antigravity":
            print(json.dumps({"decision": "deny", "reason": msg}))
            return 0
        print(msg, file=sys.stderr)
        return 2

    updated = dict(tool_input)
    reasons = []
    notes = []

    if is_delegate:
        role = str(tool_input.get("role") or "").lower()
        task_text = str(tool_input.get("task") or "")
        target = tool_input.get("target") if isinstance(tool_input.get("target"), dict) else {}
        asked = str(target.get("model") or "").lower()
        if role in DELEGATE_SONNET_ROLES and any(tier in asked for tier in ABOVE_CEILING["sonnet"]) and not MODEL_REASON.search(task_text):
            capped = sonnet_equivalent(asked)
            updated["target"] = {**target, "model": capped}
            reasons.append(f"delegate_task {role} runs on {capped} unless the task has a `Model reason:` line")
            notes.append(
                f"This {role} delegate runs on {capped}, not {asked}: the task gives no reason for the higher model. "
                "To run one unit higher, add a `Model reason: <why this unit needs it>` line to the task."
            )
    else:
        interrogate = is_interrogate_call(tool_input)
        if agent in ("", "general-purpose") and interrogate:
            updated["subagent_type"] = "senior-reviewer"
            agent = "senior-reviewer"
            if not updated.get("model"):
                updated["model"] = "opus"
            reasons.append("Interrogate must run read-only; redirected general-purpose to senior-reviewer")

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

    if is_review_seat(agent, tool_input, tool_name):
        transcript = event.get("transcript_path") or event.get("transcriptPath") or ""
        exclude = event.get("tool_use_id") or tool_call.get("id")
        prior = reviews_since_user_spoke(transcript, exclude_id=exclude)
        if prior >= REVIEW_BLOCK_AFTER:
            msg = (
                f"Blocked: {prior} review subagents since Kolin's last message. "
                "Policy caps review at 1 pass plus 1 fix-delta re-check. "
                "Stop patching, report the open findings to Kolin, and wait for a reply."
            )
            if emit == "antigravity":
                print(json.dumps({"decision": "deny", "reason": msg}))
                return 0
            print(msg, file=sys.stderr)
            return 2
        if prior >= REVIEW_WARN_AFTER:
            notes.append(
                f"This session spawned {prior} review subagents since Kolin's last message. "
                "Policy caps review at 1 pass plus 1 fix-delta re-check; "
                "if findings keep returning, stop patching, rethink the design, and tell Kolin."
            )

    if emit == "antigravity":
        if notes:
            ag_notes.append_note(event, " ".join(notes))
        if updated != tool_input and "target" in updated:
            print(json.dumps({"decision": "allow", "overwrite": {"target": updated["target"]}}))
        else:
            print(json.dumps({"decision": "allow"}))
        return 0

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

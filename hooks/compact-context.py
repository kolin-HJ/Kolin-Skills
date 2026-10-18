import json
import pathlib
import subprocess
import sys

INSTRUCTIONS = pathlib.Path.home() / ".codex/compact-instructions.md"
STATUS_LINES = 40
AFTER_COMPACT = (
    "The conversation was just compacted; the summary above replaces it. "
    "The live state below was read after compaction and outranks the summary where they differ. "
    "Re-read each file before editing it, because the summary's excerpts may be stale. "
    "If a skill or playbook was guiding the work, re-open its SKILL.md before continuing."
)


def git(cwd, *args):
    result = subprocess.run(["git", *args], cwd=cwd, capture_output=True, text=True, timeout=10)
    return result.stdout.strip() if result.returncode == 0 else None


def live_state(cwd):
    root = git(cwd, "rev-parse", "--show-toplevel")
    if root is None:
        return f"Working directory: {cwd} (not a git repository)"
    status = git(cwd, "status", "--short").splitlines()
    shown = "\n".join(status[:STATUS_LINES])
    more = f"\n...and {len(status) - STATUS_LINES} more" if len(status) > STATUS_LINES else ""
    lines = [
        f"Working directory: {cwd}",
        f"Repository root: {root}",
        f"Branch: {git(cwd, 'branch', '--show-current') or 'detached HEAD'}",
        f"Last commit: {git(cwd, 'log', '-1', '--format=%h %s')}",
        f"Uncommitted changes: {git(cwd, 'diff', 'HEAD', '--shortstat') or 'none'}",
        f"Changed files ({len(status)}):\n{shown}{more}" if status else "Changed files: none",
    ]
    return "\n".join(lines)


def main():
    mode = sys.argv[1]
    payload = json.load(sys.stdin)
    state = live_state(payload.get("cwd") or str(pathlib.Path.cwd()))
    if mode == "before":
        print(f"{INSTRUCTIONS.read_text()}\n## Live state at compaction\n\n{state}")
        return
    context = f"{AFTER_COMPACT}\n\n{state}"
    print(json.dumps({"hookSpecificOutput": {"hookEventName": "SessionStart", "additionalContext": context}}))


main()

import datetime
import json
import os
import pathlib
import re
import signal
import subprocess
import time

from kolin_skills.helpers import HOME

STACKS_DIR = HOME / ".supabase/stacks"
FRESH_TRANSCRIPT_HOURS = 2
STOP_WAIT_SECONDS = 15
STACK_NOTICE_AT = 24


def process_commands(*selector):
    return subprocess.run(["ps", *(selector or ["-axww"]), "-o", "command="], capture_output=True, text=True).stdout


def postgres_running(directory):
    return f".postgres-wrapped -D {directory}/" in process_commands()


def running_stacks():
    commands = process_commands()
    stacks_found = []
    for directory in sorted(STACKS_DIR.iterdir()) if STACKS_DIR.is_dir() else []:
        if f".postgres-wrapped -D {directory}/data" not in commands:
            continue
        state = json.loads((directory / "state.json").read_text())
        if state.get("runtime") != "native":
            continue
        started = json.loads((directory / "owner.json").read_text())["startedAt"]
        stacks_found.append({"id": directory.name, "pid": json.loads((directory / "owner.json").read_text())["pid"], "root": state["identity"]["projectRoot"], "started": datetime.datetime.fromisoformat(started.replace("Z", "+00:00"))})
    return stacks_found


def hours_since_transcript(root):
    name = re.sub(r"[^A-Za-z0-9]", "-", root)
    config_dirs = {pathlib.Path(os.environ.get("CLAUDE_CONFIG_DIR", HOME / ".claude")), HOME / ".claude", HOME / ".claude_personal"}
    writes = [path.stat().st_mtime for config in config_dirs for path in (config / "projects" / name).rglob("*") if path.is_file()]
    return (datetime.datetime.now().timestamp() - max(writes)) / 3600 if writes else None


def is_idle(stack, idle_hours):
    started_hours = (datetime.datetime.now(datetime.timezone.utc) - stack["started"]).total_seconds() / 3600
    quiet = stack["transcript_hours"] is None or stack["transcript_hours"] > FRESH_TRANSCRIPT_HOURS
    return started_hours > idle_hours and quiet


def signal_owner(stack):
    if "supabase" not in process_commands("-p", str(stack["pid"])):
        return False
    os.kill(stack["pid"], signal.SIGTERM)
    return True


def stop_stacks(targets):
    signalled = [stack for stack in targets if signal_owner(stack)]
    deadline = time.monotonic() + STOP_WAIT_SECONDS
    while time.monotonic() < deadline and any(postgres_running(STACKS_DIR / stack["id"]) for stack in signalled):
        time.sleep(0.5)
    for stack in targets:
        if stack not in signalled:
            print(f"  {stack['root']}: owner pid {stack['pid']} is not a supabase process")
        else:
            print(f"  {stack['root']}: {'still running' if postgres_running(STACKS_DIR / stack['id']) else 'stopped'}")
    return all(stack in signalled and not postgres_running(STACKS_DIR / stack["id"]) for stack in targets)


def busy_roots(roots):
    listing = subprocess.run(["lsof", "-a", "-d", "cwd", "-F", "cn"], capture_output=True, text=True).stdout
    busy, command = set(), ""
    for line in listing.splitlines():
        if line.startswith("c"):
            command = line[1:]
        elif line.startswith("n") and not command.startswith(("supabase", "postgres", ".postgres")):
            busy.update(root for root in roots if line[1:] == root or line[1:].startswith(root + "/"))
    return busy


def stacks(stop, idle_hours, notice):
    found = running_stacks()
    for stack in found:
        stack["transcript_hours"] = hours_since_transcript(stack["root"])
        stack["idle"] = is_idle(stack, idle_hours)
    idle = [stack for stack in found if stack["idle"]]
    if notice:
        if idle and len(found) >= STACK_NOTICE_AT:
            message = f"{len(idle)} idle local Supabase stacks hold shared-memory segments (macOS allows 32). Run: kolin-skills stacks --stop"
            print(json.dumps({"systemMessage": message}))
        return 0
    busy = busy_roots({stack["root"] for stack in idle}) if stop and idle else set()
    for stack in found:
        transcript = "none" if stack["transcript_hours"] is None else f"{stack['transcript_hours']:.1f}h ago"
        print(f"{'idle' if stack['idle'] else 'keep'}  {stack['root']}  started {stack['started'].astimezone():%Y-%m-%d %H:%M}  transcript {transcript}")
    print(f"{len(found)} running, {len(idle)} idle")
    if not stop:
        return 0
    for stack in idle:
        if stack["root"] in busy:
            print(f"  skipped: a process works in {stack['root']}")
    return 0 if stop_stacks([stack for stack in idle if stack["root"] not in busy]) else 1

import datetime
import glob
import json
import subprocess
from concurrent.futures import ThreadPoolExecutor

from kolin_skills.helpers import HOME
from kolin_skills.stacks import hours_since_transcript, is_idle

STATE_GLOBS = (".t3/worktrees/*/*/.verify/state.json", ".codex/worktrees/*/*/.verify/state.json")
CLEANUP_SECONDS = 25


def verify_servers_found():
    found = []
    for pattern in STATE_GLOBS:
        for path in sorted(glob.glob(str(HOME / pattern))):
            state = json.loads(open(path).read())
            root = str(path).removesuffix("/.verify/state.json")
            started = datetime.datetime.fromisoformat(state["startedAt"].replace("Z", "+00:00"))
            found.append({"root": root, "started": started, "transcript_hours": hours_since_transcript(root)})
    return found


def run_cleanup(server):
    try:
        done = subprocess.run(["pnpm", "-s", "verify", "cleanup"], cwd=server["root"], capture_output=True, text=True, timeout=CLEANUP_SECONDS)
    except subprocess.TimeoutExpired:
        return f"  {server['root']}: verify cleanup took over {CLEANUP_SECONDS}s", False
    if done.returncode:
        return f"  {server['root']}: verify cleanup failed: {done.stderr.strip() or done.stdout.strip()}", False
    return f"  {server['root']}: stopped", True


def verify_servers(stop, idle_hours):
    found = verify_servers_found()
    for server in found:
        server["idle"] = is_idle(server, idle_hours)
        transcript = "none" if server["transcript_hours"] is None else f"{server['transcript_hours']:.1f}h ago"
        print(f"{'idle' if server['idle'] else 'keep'}  {server['root']}  verify server started {server['started'].astimezone():%Y-%m-%d %H:%M}  transcript {transcript}")
    idle = [server for server in found if server["idle"]]
    print(f"{len(found)} verify servers, {len(idle)} idle")
    if not stop or not idle:
        return 0
    with ThreadPoolExecutor(len(idle)) as pool:
        results = list(pool.map(run_cleanup, idle))
    for line, _ in results:
        print(line)
    return 0 if all(stopped for _, stopped in results) else 1

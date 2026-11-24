import datetime
import glob
import json
import pathlib
import subprocess
from concurrent.futures import ThreadPoolExecutor

from kolin_skills.helpers import HOME
from kolin_skills.stacks import busy_roots, hours_since_transcript, is_idle, process_table, process_tree

STATE_GLOBS = (".t3/worktrees/*/*/.verify/state.json", ".codex/worktrees/*/*/.verify/state.json")
CLEANUP_SECONDS = 25
RUN_SILENT = {"bun": ["bun", "run", "--silent"], "pnpm": ["pnpm", "-s"], "npm": ["npm", "run", "-s"]}


def read_state(path):
    root = str(path).removesuffix("/.verify/state.json")
    try:
        state = json.loads(pathlib.Path(path).read_text())
        started = datetime.datetime.fromisoformat(state["startedAt"].replace("Z", "+00:00"))
    except (OSError, ValueError, KeyError, TypeError, AttributeError) as error:
        return None, f"  {root}: unreadable verify state ({type(error).__name__}: {error})"
    if started.tzinfo is None:
        return None, f"  {root}: unreadable verify state (startedAt {state['startedAt']} has no timezone)"
    pids = {pid for pid in (state.get("serverPid"), state.get("chromePid")) if isinstance(pid, int)}
    return {"root": root, "started": started, "pids": pids, "transcript_hours": hours_since_transcript(root)}, None


def verify_servers_found():
    found, problems = [], []
    for pattern in STATE_GLOBS:
        for path in sorted(glob.glob(str(HOME / pattern))):
            server, problem = read_state(path)
            if server:
                found.append(server)
            else:
                problems.append(problem)
    return found, problems


def cleanup_command(root):
    try:
        manager = json.loads(pathlib.Path(root, "package.json").read_text()).get("packageManager", "npm").split("@")[0]
    except (OSError, ValueError, AttributeError) as error:
        return None, f"no readable package.json ({type(error).__name__})"
    if manager not in RUN_SILENT:
        return None, f"no cleanup runner for packageManager {manager}"
    return [*RUN_SILENT[manager], "verify", "cleanup"], None


def run_cleanup(server):
    command, problem = cleanup_command(server["root"])
    if problem:
        return f"  {server['root']}: verify cleanup not run: {problem}", False
    try:
        done = subprocess.run(command, cwd=server["root"], capture_output=True, text=True, timeout=CLEANUP_SECONDS)
    except subprocess.TimeoutExpired:
        return f"  {server['root']}: verify cleanup took over {CLEANUP_SECONDS}s", False
    except FileNotFoundError:
        return f"  {server['root']}: verify cleanup not run: {command[0]} is not on PATH", False
    if done.returncode:
        return f"  {server['root']}: verify cleanup failed: {done.stderr.strip() or done.stdout.strip()}", False
    return f"  {server['root']}: stopped", True


def verify_servers(stop, idle_hours):
    found, problems = verify_servers_found()
    for server in found:
        server["idle"] = is_idle(server, idle_hours)
        transcript = "none" if server["transcript_hours"] is None else f"{server['transcript_hours']:.1f}h ago"
        print(f"{'idle' if server['idle'] else 'keep'}  {server['root']}  verify server started {server['started'].astimezone():%Y-%m-%d %H:%M}  transcript {transcript}")
    for problem in problems:
        print(problem)
    idle = [server for server in found if server["idle"]]
    print(f"{len(found)} verify servers, {len(idle)} idle")
    if not stop or not idle:
        return 1 if problems else 0
    own = process_tree(process_table(), set().union(*(server["pids"] for server in idle)))
    busy = busy_roots({server["root"] for server in idle}, own)
    for server in idle:
        if server["root"] in busy:
            print(f"  skipped: a process works in {server['root']}")
    stoppable = [server for server in idle if server["root"] not in busy]
    results = []
    if stoppable:
        with ThreadPoolExecutor(len(stoppable)) as pool:
            results = list(pool.map(run_cleanup, stoppable))
    for line, _ in results:
        print(line)
    return 0 if all(stopped for _, stopped in results) and not problems else 1

#!/usr/bin/env python3
import fcntl
import os
import select
import sys
import time


SLOTS = int(os.environ.get("HEAVY_SLOTS") or 3)
SLOT_DIR = os.environ.get("HEAVY_SLOT_DIR") or f"/tmp/heavy-slots-{os.getuid()}"
# HEAVY_SLOT_LOCK: one shared lock file (e.g. /workspace/runs/heavy.lock); implies a single slot.
SLOT_LOCK = os.environ.get("HEAVY_SLOT_LOCK")


def take_free_slot():
    paths = [SLOT_LOCK] if SLOT_LOCK else [os.path.join(SLOT_DIR, str(i)) for i in range(SLOTS)]
    if not SLOT_LOCK:
        os.makedirs(SLOT_DIR, exist_ok=True)
    for path in paths:
        fd = os.open(path, os.O_CREAT | os.O_RDWR, 0o600)
        try:
            fcntl.flock(fd, fcntl.LOCK_EX | fcntl.LOCK_NB)
            return fd
        except BlockingIOError:
            os.close(fd)
    return None


def hold_until_exit(fd, shell_pid):
    if os.fork():
        return
    os.setsid()
    devnull = os.open(os.devnull, os.O_RDWR)
    for stream in (0, 1, 2):
        os.dup2(devnull, stream)
    try:
        wait_for_exit(shell_pid)
    except ProcessLookupError:
        pass
    os._exit(0)


def wait_for_exit(pid):
    if hasattr(os, "pidfd_open"):
        select.select([os.pidfd_open(pid)], [], [])
        return
    queue = select.kqueue()
    queue.control([select.kevent(pid, select.KQ_FILTER_PROC, select.KQ_EV_ADD, select.KQ_NOTE_EXIT)], 0)
    queue.control(None, 1)


def main() -> int:
    shell_pid, max_wait = int(sys.argv[1]), float(sys.argv[2])
    started = time.monotonic()
    fd = take_free_slot()
    while fd is None and time.monotonic() - started < max_wait:
        time.sleep(1)
        fd = take_free_slot()
    waited = round(time.monotonic() - started)
    if fd is None:
        print(f"heavy-slot: all {SLOTS} heavy-job slots stayed busy for {waited}s; running anyway.", file=sys.stderr)
        return 0
    hold_until_exit(fd, shell_pid)
    if waited:
        print(f"heavy-slot: waited {waited}s for one of {SLOTS} heavy-job slots.", file=sys.stderr)
    return 0


if __name__ == "__main__":
    sys.exit(main())

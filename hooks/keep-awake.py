#!/usr/bin/env python3
import os
import shutil
import subprocess
import sys


SHELLS = {"sh", "bash", "zsh", "dash"}
HOLD_SECONDS = "3600"


def parent_and_name(pid):
    out = subprocess.run(["ps", "-o", "ppid=,comm=", "-p", str(pid)], capture_output=True, text=True).stdout
    parent, _, command = out.strip().partition(" ")
    return int(parent), os.path.basename(command.strip())


def claude_pid():
    pid = os.getppid()
    while True:
        parent, name = parent_and_name(pid)
        if name not in SHELLS:
            return pid
        pid = parent


def main():
    caffeinate = shutil.which("caffeinate")
    if caffeinate is None:
        return 0
    subprocess.Popen(
        [caffeinate, "-i", "-t", HOLD_SECONDS, "-w", str(claude_pid())],
        stdin=subprocess.DEVNULL,
        stdout=subprocess.DEVNULL,
        stderr=subprocess.DEVNULL,
        start_new_session=True,
    )
    return 0


if __name__ == "__main__":
    sys.exit(main())

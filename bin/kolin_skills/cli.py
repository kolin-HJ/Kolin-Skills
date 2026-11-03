import argparse

from kolin_skills.apply import import_into_repo, pull, run_apply
from kolin_skills.check import check, check_drift, check_quick
from kolin_skills.helpers import QUICK_CHECK_SECONDS
from kolin_skills.stacks import stacks
from kolin_skills.vendor import upstream


def main():
    parser = argparse.ArgumentParser(prog="kolin-skills", description="Make every agent harness on this machine match the Kolin-Skills repo.")
    commands = parser.add_subparsers(dest="command", required=True)
    apply_parser = commands.add_parser("apply", help="link and render the repo into home; idempotent and offline")
    apply_parser.add_argument("--check", action="store_true", help="report drift and change nothing")
    apply_parser.add_argument("--quiet", action="store_true", help="print only changes")
    apply_parser.add_argument("--adopt", action="store_true", help="wire home to this checkout when another one owns it")
    apply_parser.add_argument("--if-wired", action="store_true", help="do nothing unless home is wired to this checkout")
    pull_parser = commands.add_parser("pull", help="fast-forward the repo from its remote, then apply")
    pull_parser.add_argument("--quiet", action="store_true", help="print only changes")
    import_parser = commands.add_parser("import", help="move a skill or agent made in home into the repo, or list an npx skill in upstream/skills.json, then apply")
    import_parser.add_argument("path")
    upstream_parser = commands.add_parser("upstream", help="check out vendored pstack and cursor-team-kit at their pins, add missing third-party skills, then apply")
    upstream_parser.add_argument("--bump", action="store_true", help="move each vendor pin to its newest upstream commit and print what changed")
    stacks_parser = commands.add_parser("stacks", help="list running native Supabase stacks; --stop stops the idle ones")
    stacks_parser.add_argument("--stop", action="store_true", help="send SIGTERM to each idle stack's supabase owner process and wait for postgres to exit; skips a root another process works in")
    stacks_parser.add_argument("--idle-hours", type=float, default=6, help="a stack is idle only after it has run this many hours; the 2-hour transcript window stays fixed")
    stacks_parser.add_argument("--notice", action="store_true", help="session-start hook: one JSON line when idle stacks exist and 24 or more stacks run, else nothing")
    check_parser = commands.add_parser("check", help="the gate: drift, strays, missing skills, spend caps, file length and tests")
    check_mode = check_parser.add_mutually_exclusive_group()
    check_mode.add_argument("--files", action="store_true", help="only the 1,000-line file limit")
    check_mode.add_argument("--quick", action="store_true", help=f"home only, under {QUICK_CHECK_SECONDS}s: links resolve, hooks and policy are wired, self-invoking skills are not model-locked")
    check_parser.add_argument("target", nargs="?", help="scan this tree for a vendored pstack pin, synced senior-reviewer, or every-PR reviewer gate that drifted from this repo (skips the rest of the gate)")
    drift_parser = commands.add_parser("check-drift", help="fail when a tree's vendored pstack, synced senior-reviewer, or every-PR reviewer gate drifts from this repo")
    drift_parser.add_argument("target", help="repo root to scan")
    commands.add_parser("install", help="first run on a machine: upstream, apply, check")
    args = parser.parse_args()
    if args.command == "apply":
        return run_apply(args.check, args.quiet, args.adopt, args.if_wired)
    if args.command == "pull":
        return pull(args.quiet)
    if args.command == "import":
        return import_into_repo(args.path)
    if args.command == "upstream":
        return upstream(args.bump)
    if args.command == "stacks":
        return stacks(args.stop, args.idle_hours, args.notice)
    if args.command == "check":
        if args.quick:
            return check_quick()
        if args.target and not args.files:
            return check_drift(args.target)
        return check(files_only=args.files)
    if args.command == "check-drift":
        return check_drift(args.target)
    fetched = upstream()
    return check() or fetched

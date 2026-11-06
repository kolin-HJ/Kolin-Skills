import contextlib
import json
import os
import pathlib
import shutil
import subprocess
import sys

from kolin_skills.helpers import (
    DERIVED, DROPPED_SKILLS, GIT, HOME, LINKS, MERGED_JSON, NPX_SKILL_LOCK, OTHER_INSTALLERS,
    OWN_SKILL_HOMES, READ_ONLY_EXECUTABLES, RENDERED, REPO, STATE_DIR, TRUNK,
    VENDOR, VENDOR_AGENTS, VENDOR_SKILL_HOMES, WATCHED_HOMES, Plan, codex_agent_toml,
    declared_upstream_skills, git, merge_settings, model_locked, render_template, self_invoking,
    state_lock, vendor_pin_problems, vendor_skills, wired_repo, without_model_lock,
)


def derive_unlocked_skill(plan, name, skill):
    derived = DERIVED / name
    if derived.is_symlink():
        plan.discard(derived)
    plan.owned.add(derived)
    for entry in sorted(skill.iterdir()):
        if entry.name != "SKILL.md":
            plan.link(entry, derived / entry.name)
    plan.write(derived / "SKILL.md", without_model_lock((skill / "SKILL.md").read_text()))
    return derived


def mirror_vendored_skill(plan, name, skill):
    mirror = DERIVED / name
    if mirror.exists() and not mirror.is_symlink():
        plan.discard(mirror)
    plan.link(skill, mirror)


def prune_derived(plan):
    for top in sorted(DERIVED.iterdir()) if DERIVED.is_dir() else []:
        if top not in plan.owned:
            plan.discard(top)
        elif top.is_dir() and not top.is_symlink():
            for child in sorted(top.iterdir()):
                if child not in plan.owned:
                    plan.discard(child)


def points_into_managed_tree(path, roots):
    text = os.readlink(path)
    return text.startswith((*(f"{root}/" for root in roots), str(VENDOR), str(DERIVED), "../../.agents/skills/"))


def repoint_dangling_upstream_links(plan):
    for name in sorted(declared_upstream_skills()):
        if not (HOME / ".agents/skills" / name).exists():
            continue
        for home in VENDOR_SKILL_HOMES[1:]:
            path = HOME / home / name
            if path.is_symlink() and not path.exists():
                plan.link(pathlib.Path(f"../../.agents/skills/{name}"), path)


def prune_stale_links(plan, directory):
    if not directory.is_dir():
        return
    for path in sorted(directory.iterdir()):
        if not path.is_symlink() or path in plan.owned:
            continue
        if not path.exists() or os.readlink(path).startswith((str(VENDOR), str(DERIVED))):
            plan.remove(path)


def apply(plan, roots):
    for source, destinations in LINKS.items():
        if (REPO / source).exists():
            for destination in destinations:
                plan.link(REPO / source, HOME / destination)

    own = sorted(path.parent for path in (REPO / "skills").glob("*/SKILL.md"))
    vendored = vendor_skills()
    for skill in own:
        plan.link(skill, HOME / ".agents/skills" / skill.name)
        for home in OWN_SKILL_HOMES[1:]:
            plan.link(pathlib.Path(f"../../.agents/skills/{skill.name}"), HOME / home / skill.name)
    for name, skill in vendored.items():
        if name in {path.name for path in own}:
            continue
        if self_invoking(name) and model_locked(skill / "SKILL.md"):
            source = derive_unlocked_skill(plan, name, skill)
        else:
            source = skill
            mirror_vendored_skill(plan, name, skill)
        plan.link(source, HOME / ".agents/skills" / name)
        for home in VENDOR_SKILL_HOMES[1:]:
            existing = HOME / home / name
            if existing.exists() and not existing.is_symlink():
                plan.owned.add(existing)
                continue
            plan.link(pathlib.Path(f"../../.agents/skills/{name}"), existing)
    prune_derived(plan)

    for name in sorted(DROPPED_SKILLS - declared_upstream_skills()):
        for home in WATCHED_HOMES:
            path = HOME / home / name
            if path.is_symlink() or path.exists():
                plan.retire(path)

    own_agents = sorted((REPO / "agents").glob("*.md"))
    vendored_agents = [VENDOR / path for path in VENDOR_AGENTS if (VENDOR / path).is_file()]
    agents = own_agents + [agent for agent in vendored_agents if agent.name not in {own.name for own in own_agents}]
    for agent in agents:
        plan.link(agent, HOME / ".claude/agents" / agent.name)
        plan.write(HOME / ".codex/agents" / f"{agent.stem}.toml", codex_agent_toml(agent.read_text()))
    repoint_dangling_upstream_links(plan)
    for home in WATCHED_HOMES:
        prune_stale_links(plan, HOME / home)
    state_file = STATE_DIR / "state.json"
    generated = {str(HOME / ".codex/agents" / f"{agent.stem}.toml") for agent in agents}
    previous = set(json.loads(state_file.read_text())["generated"]) if state_file.is_file() else set()
    for stale in sorted(previous - generated):
        if pathlib.Path(stale).is_file():
            plan.remove(pathlib.Path(stale))

    for source, destination in MERGED_JSON.items():
        wanted = json.loads(render_template((REPO / source).read_text()))
        path = HOME / destination
        current = json.loads(path.read_text()) if path.is_file() else {}
        plan.write_json(path, merge_settings(current, wanted, roots))
    for source, destination in RENDERED.items():
        plan.write(HOME / destination, render_template((REPO / source).read_text()))
    for source, destination in READ_ONLY_EXECUTABLES.items():
        plan.write(HOME / destination, (REPO / source).read_text(), mode=0o555)

    hooks_path = subprocess.run(["git", "-C", str(REPO), "config", "core.hooksPath"], text=True, capture_output=True).stdout.strip()
    if (REPO / ".git").exists() and hooks_path != ".githooks":
        plan.note("git config core.hooksPath .githooks")
        if not plan.check:
            subprocess.run(["git", "-C", str(REPO), "config", "core.hooksPath", ".githooks"], check=True)

    if not plan.check:
        STATE_DIR.mkdir(exist_ok=True)
        temporary = state_file.with_name(".state.json.tmp")
        temporary.write_text(json.dumps({"repo": str(REPO), "generated": sorted(generated)}, indent=2) + "\n")
        temporary.replace(state_file)


def ownership_problems(owned):
    declared = declared_upstream_skills()
    known = declared | {name for names in OTHER_INSTALLERS.values() for name in names}
    problems = []
    for home in WATCHED_HOMES:
        directory = HOME / home
        for path in sorted(directory.iterdir()) if directory.is_dir() else []:
            if not path.name.startswith(".") and path not in owned and path.name not in known:
                shown = f"~/{path.relative_to(HOME)}"
                fix = "delete the link" if path.is_symlink() else f"run kolin-skills import {shown}, or delete it"
                problems.append(f"not from the repo: {shown}; {fix}")
    for skill in sorted(declared):
        if not (HOME / ".agents/skills" / skill).exists():
            problems.append(f"not installed: {skill} from upstream/skills.json; run kolin-skills upstream")
    return problems + vendor_pin_problems()


def run_apply(check, quiet, adopt=False, if_wired=False):
    owner = wired_repo()
    if if_wired and owner != str(REPO):
        return 0
    if owner and owner != str(REPO) and not adopt:
        print(f"kolin-skills: home is wired to {owner}, not this checkout ({REPO}). "
              "Run `kolin-skills apply --adopt` from this checkout to switch.", file=sys.stderr)
        return 1
    plan = Plan(check)
    with state_lock():
        apply(plan, {str(REPO), owner} - {None})
    for change in plan.changes:
        print(change)
    problems = ownership_problems(plan.owned)
    for problem in problems:
        print(problem)
    if not plan.changes and not problems and not quiet:
        print("already in sync")
    return 1 if check and (plan.changes or problems) else 0


def import_into_repo(raw):
    path = pathlib.Path(raw).expanduser().absolute()
    if path.is_symlink():
        raise SystemExit(f"{path} is a link to {os.readlink(path)}; delete it, or copy what it points to into the repo")
    is_skill = (path / "SKILL.md").is_file()
    locked = json.loads(NPX_SKILL_LOCK.read_text())["skills"] if NPX_SKILL_LOCK.is_file() else {}
    if is_skill and path.name in locked:
        manifest_file = REPO / "upstream/skills.json"
        manifest = json.loads(manifest_file.read_text())
        source = locked[path.name]["source"]
        manifest.setdefault(source, []).append(path.name)
        manifest_file.write_text(json.dumps(manifest, indent=2) + "\n")
        print(f"listed {path.name} under {source} in upstream/skills.json")
        return run_apply(check=False, quiet=False)
    if is_skill:
        destination = REPO / "skills" / path.name
        provided = vendor_skills().keys() | declared_upstream_skills()
    elif path.suffix == ".md" and path.parent.name == "agents":
        destination = REPO / "agents" / path.name
        provided = set()
    else:
        raise SystemExit(f"{path} is not a skill folder or an agent file; add it to the repo by hand")
    if destination.exists() or path.name in provided:
        raise SystemExit(f"the repo already provides {path.name}; compare the two and keep one")
    shutil.move(str(path), str(destination))
    print(f"moved {path} to {destination.relative_to(REPO)}")
    return run_apply(check=False, quiet=False)


def fast_forward_to_trunk():
    fetched = git("fetch", "--quiet", "--prune", "origin", timeout=10)
    if fetched.returncode or git("rev-parse", "--verify", "--quiet", f"origin/{TRUNK}").returncode:
        return None
    dirty = bool(git("status", "--porcelain").stdout.strip())
    branch = git("rev-parse", "--abbrev-ref", "HEAD").stdout.strip()
    merged = git("for-each-ref", "--format=%(upstream:track)", f"refs/heads/{branch}").stdout.strip() == "[gone]"
    if not dirty and branch != TRUNK and merged and git("switch", "--quiet", TRUNK).returncode == 0:
        print(f"kolin-skills: {branch} is merged; switched to {TRUNK}")
        branch = TRUNK
    before = git("rev-parse", "HEAD").stdout.strip()
    merge_failure = None
    if not dirty and branch == TRUNK:
        merge = git("merge", "--ff-only", "--quiet", f"origin/{TRUNK}")
        if merge.returncode:
            merge_failure = (merge.stderr.strip() or merge.stdout.strip() or f"exit {merge.returncode}").splitlines()[-1]
    if git("rev-parse", "HEAD").stdout.strip() != before:
        print(f"kolin-skills pulled {git('log', '--oneline', f'{before}..HEAD').stdout.strip()}")
    behind = int(git("rev-list", "--count", f"HEAD..origin/{TRUNK}").stdout.strip())
    if not behind:
        return None
    blocker = (f"git merge --ff-only failed: {merge_failure}" if merge_failure
               else "it has local edits" if dirty else f"it is on {branch}, not {TRUNK}" if branch != TRUNK else "it has commits origin lacks")
    return (f"stale setup: {REPO} is {behind} commits behind origin/{TRUNK} and was not updated, because {blocker}. "
            f"Commit or discard the edits and switch to {TRUNK}, then run kolin-skills pull")


def pull(quiet):
    chatter = sys.stderr if quiet else sys.stdout
    with contextlib.redirect_stdout(chatter):
        try:
            with state_lock():
                problem = fast_forward_to_trunk()
        except subprocess.TimeoutExpired as timed_out:
            problem = f"{' '.join(timed_out.cmd[len(GIT):])} timed out after {timed_out.timeout}s; {TRUNK} was not updated"
        message = f"kolin-skills: {problem}" if problem else None
        if message:
            print(message)
        status = run_apply(check=False, quiet=quiet)
    if message and quiet:
        print(json.dumps({"systemMessage": message,
                          "hookSpecificOutput": {"hookEventName": "SessionStart", "additionalContext": message}}))
    return status

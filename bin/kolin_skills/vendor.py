import json
import subprocess
import sys

import third_party
from kolin_skills.apply import run_apply
from kolin_skills.helpers import HOME, REPO, STATE_DIR, VENDOR, profile_catalog, vendor_git


def sync_vendor(name, source, bump):
    path = VENDOR / name
    if not (path / ".git").is_dir():
        VENDOR.mkdir(parents=True, exist_ok=True)
        clone = ["git", "clone", "--quiet", "--no-checkout", source["url"], str(path)]
        if source.get("sparse"):
            clone[3:3] = ["--filter=blob:none", "--sparse"]
        subprocess.run(clone, check=True)
    if source.get("sparse"):
        vendor_git(path, "sparse-checkout", "set", *source["sparse"])
    vendor_git(path, "fetch", "--quiet", "origin")
    pinned = source.get("rev") or vendor_git(path, "rev-parse", "origin/HEAD")
    target = vendor_git(path, "rev-parse", "origin/HEAD") if bump else pinned
    if target != pinned:
        print(f"{name} pin moves {pinned[:12]}..{target[:12]}. Review before trusting it:")
        print(vendor_git(path, "log", "--oneline", f"{pinned}..{target}"))
        print(vendor_git(path, "diff", "--stat", pinned, target))
    vendor_git(path, "checkout", "--quiet", "--detach", target)
    print(f"{name} at {target[:12]}")
    return target


def remember_profile(name):
    STATE_DIR.mkdir(exist_ok=True)
    state_file = STATE_DIR / "state.json"
    state = json.loads(state_file.read_text()) if state_file.is_file() else {}
    profiles = [item for item in state.get("profiles") or [] if item != name]
    profiles.append(name)
    state["profiles"] = profiles
    state.setdefault("repo", str(REPO))
    state.setdefault("generated", [])
    temporary = state_file.with_name(".state.json.tmp")
    temporary.write_text(json.dumps(state, indent=2) + "\n")
    temporary.replace(state_file)


def upstream(bump=False, profile=None):
    extra = {}
    if profile:
        catalog = profile_catalog()
        if profile not in catalog:
            raise SystemExit(f"unknown profile {profile!r}; known: {', '.join(sorted(catalog)) or 'none'}")
        extra = catalog[profile]
        remember_profile(profile)
    manifest_file = REPO / "upstream/vendor.json"
    manifest = json.loads(manifest_file.read_text())
    failed = []
    for name, source in manifest.items():
        try:
            source["rev"] = sync_vendor(name, source, bump)
        except subprocess.CalledProcessError as error:
            failed.append(name)
            print(f"kolin-skills: could not fetch {name} ({error.stderr or 'git clone failed'}); continuing", file=sys.stderr)
    manifest_file.write_text(json.dumps(manifest, indent=2) + "\n")
    installed = {path.name for path in (HOME / ".agents/skills").iterdir()} if (HOME / ".agents/skills").is_dir() else set()
    problem = third_party.node_problem()
    if problem:
        print(f"kolin-skills: skipped third-party skills and tools: {problem}", file=sys.stderr)
    else:
        third_party.install_skills(REPO, installed, extra)
        failed += third_party.install_npm_tools(REPO)
    return run_apply(check=False, quiet=False) or (1 if failed else 0)

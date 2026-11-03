import json
import subprocess
import sys

import third_party
from kolin_skills.apply import run_apply
from kolin_skills.helpers import HOME, REPO, VENDOR, vendor_git


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


def upstream(bump=False):
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
        third_party.install_skills(REPO, installed)
        failed += third_party.install_npm_tools(REPO)
    return run_apply(check=False, quiet=False) or (1 if failed else 0)

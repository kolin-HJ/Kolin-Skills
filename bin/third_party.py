import json
import pathlib
import shutil
import subprocess
import sys

MIN_NODE = (22, 20)
NPX_AGENTS = ("claude-code", "codex", "cursor")


def node_problem():
    node = shutil.which("node")
    floor = f"{MIN_NODE[0]}.{MIN_NODE[1]}"
    if node is None:
        return f"Node is missing from PATH; third-party skills and tools need Node >= {floor}"
    try:
        raw = subprocess.run([node, "--version"], text=True, capture_output=True, timeout=10).stdout.strip()
        version = tuple(int(part) for part in raw.lstrip("v").split(".")[:2])
    except (OSError, ValueError, subprocess.TimeoutExpired):
        return f"could not read the Node version; third-party skills and tools need Node >= {floor}"
    if version < MIN_NODE:
        return f"Node {raw} is too old; third-party skills and tools need Node >= {floor}. Upgrade Node, then run kolin-skills upstream"
    return None


def install_skills(repo, installed):
    for package, skills in json.loads((repo / "upstream/skills.json").read_text()).items():
        missing = [skill for skill in skills if skill not in installed]
        if not missing:
            continue
        agents = [flag for agent in NPX_AGENTS for flag in ("--agent", agent)]
        result = subprocess.run(["npx", "--yes", "skills", "add", package, "--global", "--yes", *agents,
                                 *[flag for skill in missing for flag in ("--skill", skill)]])
        if result.returncode:
            print(f"kolin-skills: npx skills add {package} failed (exit {result.returncode}); continuing", file=sys.stderr)


def npm_tool_pins(repo):
    return json.loads((repo / "upstream/tools.json").read_text())["npm"]


def npm_global_versions(names):
    try:
        result = subprocess.run(["npm", "root", "--global"], text=True, capture_output=True, timeout=30)
    except subprocess.TimeoutExpired:
        return None, "npm root --global timed out after 30s"
    if result.returncode:
        return None, f"npm root --global failed (exit {result.returncode}): {result.stderr.strip()}"
    root = pathlib.Path(result.stdout.strip())
    manifests = {name: root / name / "package.json" for name in names}
    return {name: json.loads(path.read_text())["version"] if path.is_file() else None
            for name, path in manifests.items()}, None


def install_npm_tools(repo):
    pins = npm_tool_pins(repo)
    versions, problem = npm_global_versions(pins)
    if problem:
        print(f"kolin-skills: skipped pinned CLIs: {problem}", file=sys.stderr)
        return list(pins)
    failed = []
    for name, version in pins.items():
        if versions[name] == version:
            continue
        result = subprocess.run(["npm", "install", "--global", f"--allow-scripts={name}", f"{name}@{version}"])
        if result.returncode:
            failed.append(name)
            print(f"kolin-skills: npm install {name}@{version} failed (exit {result.returncode}); a global prefix you cannot write needs Node from Homebrew, nvm, fnm or Volta", file=sys.stderr)
    return failed


def npm_tool_problems(repo):
    problem = node_problem()
    if problem:
        return [f"pinned CLIs in upstream/tools.json not checked: {problem}"]
    if shutil.which("npm") is None:
        return ["npm is missing from PATH; upstream/tools.json CLIs need it. Install Node with npm, then run kolin-skills upstream"]
    pins = npm_tool_pins(repo)
    versions, problem = npm_global_versions(pins)
    if problem:
        return [f"pinned CLIs in upstream/tools.json not checked: {problem}"]
    problems = []
    for name, version in pins.items():
        if versions[name] != version:
            state = "not installed" if versions[name] is None else f"{versions[name]} installed"
            problems.append(f"{name} is {state}, pinned at {version} in upstream/tools.json; run kolin-skills upstream")
    return problems

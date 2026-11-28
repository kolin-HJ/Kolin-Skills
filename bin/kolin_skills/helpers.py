import contextlib
import datetime
import fcntl
import json
import os
import pathlib
import re
import shutil
import stat
import subprocess


def on_disk_case(path):
    resolved = pathlib.Path("/")
    for part in path.parts[1:]:
        names = {entry.name.casefold(): entry.name for entry in resolved.iterdir()}
        resolved = resolved / (part if part in names.values() else names.get(part.casefold(), part))
    return resolved


REPO = on_disk_case(pathlib.Path(__file__).resolve().parents[2])
HOME = pathlib.Path.home()
STATE_DIR = HOME / ".kolin-skills"
VENDOR = HOME / ".agents/vendor"
DERIVED = STATE_DIR / "derived"
OWN_SKILL_HOMES = [".agents/skills", ".claude/skills", ".cursor/skills"]
VENDOR_SKILL_HOMES = [".agents/skills", ".claude/skills"]
VENDOR_SKILL_DIRS = {
    "cursor-plugins/pstack/skills": None,
    "cursor-plugins/cursor-team-kit/skills": None,
}
VENDOR_SKIP = {"setup-pstack"}
SELF_INVOKING_SKILLS = {"architect", "how", "statechart", "thermo-nuclear-code-quality-review"}
MODEL_LOCK_KEY = "disable-model-invocation"
POLICY_MAX_BYTES = 2048
PSTACK_LOCAL_MAX_BYTES = 1024
QUICK_CHECK_SECONDS = 30
TEST_FILES_AT_ONCE = 6
TEST_FILE_SECONDS = 300
VENDOR_AGENTS = []
WATCHED_HOMES = [
    ".agents/skills", ".claude/skills", ".cursor/skills", ".codex/skills", ".grok/skills",
    ".gemini/config/skills",
    ".claude/agents", ".codex/agents", ".cursor/agents", ".grok/agents", ".gemini/config/agents",
    ".claude/commands", ".cursor/commands", ".grok/commands", ".codex/prompts",
    ".claude/rules", ".cursor/rules", ".grok/rules", ".claude/output-styles",
    ".claude/hooks", ".codex/hooks",
]
OTHER_INSTALLERS = {
    "REA": ["reverse-engineer-anything"],
    "claude.ai skill sync": ["synced"],
    "herdr": ["herdr-agent-state.sh"],
}
DROPPED_SKILLS = {
    "break-ui", "full-stop", "emil-design-eng", "loop-refactor-to-pstack", "mobile-native",
    "modernize", "firecrawl", "firecrawl-crawl", "firecrawl-map", "firecrawl-scrape",
    "firecrawl-search", "improve", "ponytail", "ponytail-audit",
    "ask-matt", "code-review", "codebase-design", "domain-modeling", "grill-me",
    "grill-with-docs", "grilling", "to-spec", "to-tickets", "implement", "implement-spec",
    "prototype", "research", "triage", "wayfinder", "retro", "handoff", "to-questionnaire",
    "wait-what", "improve-codebase-architecture", "setup-matt-pocock-skills",
    "hyperframes", "hyperframes-cli", "hyperframes-registry", "media-use",
    "reverse-any-video", "style-sampling", "slideshow", "stageshow",
}
PROFILES_JSON = REPO / "upstream/profiles.json"
NPX_SKILL_LOCK = HOME / ".agents/.skill-lock.json"
LINKS = {
    "policy/AGENTS.md": [".codex/AGENTS.md", ".claude/CLAUDE.md", ".grok/AGENTS.md"],
    "policy/compact-instructions.md": [".codex/compact-instructions.md"],
    "claude/statusline.sh": [".claude/statusline.sh"],
    "claude/output-styles/ste-visual.md": [".claude/output-styles/ste-visual.md"],
    "codex/rules/agent-tools.rules": [".codex/rules/agent-tools.rules"],
    "hooks/heavy-slot.py": [".kolin-skills/bin/heavy-slot.py"],
    "bin/kolin-skills": [".local/bin/kolin-skills"],
    "bin/context-audit": [".local/bin/context-audit"],
    "bin/feature-budget": [".local/bin/feature-budget"],
    "bin/pr-body": [".local/bin/pr-body"],
    "bin/diff-audit": [".local/bin/diff-audit"],
    "bin/pglite-replay": [".local/bin/pglite-replay"],
    "bin/disk-cleanup": [".local/bin/disk-cleanup"],
}
MERGED_JSON = {
    "claude/settings.json": ".claude/settings.json",
    "codex/hooks.json": ".codex/hooks.json",
    "cursor/hooks.json": ".cursor/hooks.json",
}
RENDERED = {"cursor/agent-policy.mdc": ".cursor/rules/agent-policy.mdc"}
READ_ONLY_EXECUTABLES = {"bin/agent-browser-guard": ".local/bin/agent-browser-guard"}
LEGACY_HOOK_PATHS = [
    str(HOME / path) for path in (
        ".codex/hooks/lint-changed-lines.py",
        ".codex/hooks/compact-context.py",
        ".claude/hooks/block-env-reads.py",
        ".claude/hooks/agent-default-model.py",
        ".claude/hooks/block-forbidden-git.sh",
        ".kolin-skills/bin/heavy-slot.py",
        ".claude/statusline.sh",
    )
]
LEGACY_HOOK_PATHS.append("pstack-local/scripts/mode-reminder")
WRITE_TOOLS = {"Edit", "Write", "NotebookEdit"}
SPEND_CAPS = {"subagent_model": "sonnet", "max_compact_window": 250_000}
TRUNK = "main"
REQUIRED_TOOLS = {
    "jq": "claude/statusline.sh formats the status line with it",
    "node": "the repo-standard PR proof script is tested with it, and npx skills needs it",
}
SKILL_INDEXES = ["README.md"]
MAX_FILE_LINES = 1000
CI_VALUES = {"1", "true", "yes"}
GIT = ["git", "-C", str(REPO), "-c", "core.hooksPath=/dev/null"]


def render_template(text):
    return text.replace("{{HOME}}", str(HOME)).replace("{{REPO}}", str(REPO))


def wired_repo():
    state_file = STATE_DIR / "state.json"
    return json.loads(state_file.read_text())["repo"] if state_file.is_file() else None


def is_managed_hook(entry, roots):
    text = json.dumps(entry)
    return any(f"{root}/" in text for root in roots) or any(path in text for path in LEGACY_HOOK_PATHS)


def merge_hooks(current, wanted, roots):
    merged = {}
    for event in [*current, *(event for event in wanted if event not in current)]:
        entries = [entry for entry in current.get(event, []) if not is_managed_hook(entry, roots)]
        entries += wanted.get(event, [])
        if entries:
            merged[event] = entries
    return merged


def merge_settings(current, wanted, roots):
    merged = dict(current)
    for key, value in wanted.items():
        if key == "hooks":
            merged[key] = merge_hooks(current.get(key, {}), value, roots)
        elif isinstance(value, dict) and isinstance(current.get(key), dict):
            merged[key] = {**current[key], **value}
        else:
            merged[key] = value
    if "skillOverrides" in merged:
        merged["skillOverrides"] = {name: level for name, level in merged["skillOverrides"].items() if name not in DROPPED_SKILLS}
    return merged


def antigravity_config_dirs():
    candidates = [HOME / ".gemini/config"]
    t3_providers = HOME / ".t3/userdata/providers/antigravity"
    if t3_providers.is_dir():
        for entry in sorted(t3_providers.iterdir()):
            if entry.is_dir():
                candidates.append(entry / "config")
    env_home = os.environ.get("GEMINI_HOME")
    if env_home:
        home_resolved = HOME.resolve()
        candidate = pathlib.Path(env_home).expanduser().resolve()
        if candidate.is_relative_to(home_resolved):
            candidates.append(HOME / candidate.relative_to(home_resolved) / "config")
    unique = []
    seen = set()
    for path in candidates:
        key = str(path.resolve())
        if key not in seen:
            seen.add(key)
            unique.append(path)
    return unique


def expand_skill_path(value):
    if not isinstance(value, str):
        return None
    if value == "~":
        return os.path.normpath(str(HOME))
    if value.startswith("~/"):
        return os.path.normpath(str(HOME / value[2:]))
    return os.path.normpath(value)


def merge_antigravity_skills(current, wanted):
    merged = dict(current)
    existing = [entry for entry in current.get("entries", []) if isinstance(entry, dict)]
    wanted_entries = [entry for entry in wanted.get("entries", []) if isinstance(entry, dict)]
    wanted_paths = {expanded for entry in wanted_entries if (expanded := expand_skill_path(entry.get("path"))) is not None}
    kept = [entry for entry in existing if expand_skill_path(entry.get("path")) not in wanted_paths]
    merged["entries"] = [*kept, *wanted_entries]
    return merged


def merge_antigravity_hooks(current, wanted, roots):
    merged = {
        name: value
        for name, value in current.items()
        if name not in wanted and not is_managed_hook(value, roots)
    }
    merged.update(wanted)
    return merged


def codex_agent_toml(markdown):
    _, header, body = markdown.split("---\n", 2)
    fields = {}
    for line in header.splitlines():
        key, _, value = line.partition(":")
        fields[key.strip()] = value.strip()
    body = body.strip("\n")
    if "'''" in body:
        raise SystemExit(f"{fields['name']}: body contains ''', which a TOML literal string cannot hold")
    lines = [f"name = {json.dumps(fields['name'], ensure_ascii=False)}",
             f"description = {json.dumps(fields['description'], ensure_ascii=False)}"]
    tools = {tool.strip() for tool in fields.get("tools", "").split(",") if tool.strip()}
    if tools and not tools & WRITE_TOOLS:
        lines.append('sandbox_mode = "read-only"')
    lines.append(f"developer_instructions = '''\n{body}\n'''")
    return "\n".join(lines) + "\n"


class Plan:
    def __init__(self, check):
        self.check = check
        self.changes = []
        self.owned = set()
        self.stamp = datetime.datetime.now().strftime("%Y%m%d-%H%M%S")

    def note(self, message):
        self.changes.append(message)

    def backup(self, path):
        destination = STATE_DIR / "backup" / self.stamp / path.relative_to(HOME)
        destination.parent.mkdir(parents=True, exist_ok=True)
        shutil.move(str(path), str(destination))

    def link(self, target, path):
        self.owned.add(path)
        if path.is_symlink() and os.readlink(path) == str(target):
            return
        self.note(f"link ~/{path.relative_to(HOME)} -> {target}")
        if self.check:
            return
        if path.is_symlink():
            path.unlink()
        elif path.exists():
            self.backup(path)
        path.parent.mkdir(parents=True, exist_ok=True)
        path.symlink_to(target)

    def write(self, path, text, mode=None):
        self.owned.add(path)
        same_mode = mode is None or (path.is_file() and stat.S_IMODE(path.stat().st_mode) == mode)
        if path.is_file() and not path.is_symlink() and path.read_text() == text and same_mode:
            return
        self.note(f"write ~/{path.relative_to(HOME)}")
        if self.check:
            return
        if path.is_symlink():
            path.unlink()
        elif path.exists():
            self.backup(path)
        path.parent.mkdir(parents=True, exist_ok=True)
        temporary = path.with_name(f".{path.name}.kolin-skills")
        temporary.unlink(missing_ok=True)
        temporary.write_text(text)
        if mode is not None:
            temporary.chmod(mode)
        temporary.replace(path)

    def write_json(self, path, data):
        current = json.loads(path.read_text()) if path.is_file() else None
        if current == data:
            return
        self.write(path, json.dumps(data, indent=2) + "\n")

    def retire(self, path):
        self.owned.add(path)
        self.note(f"retire ~/{path.relative_to(HOME)}")
        if self.check:
            return
        if path.is_symlink():
            path.unlink()
        else:
            self.backup(path)

    def discard(self, path):
        self.note(f"remove ~/{path.relative_to(HOME)}")
        if not self.check:
            (shutil.rmtree if path.is_dir() and not path.is_symlink() else os.unlink)(path)

    def remove(self, path):
        self.owned.add(path)
        self.note(f"remove ~/{path.relative_to(HOME)}")
        if not self.check:
            path.unlink()


def vendor_skills():
    skills = {}
    for directory, chosen in VENDOR_SKILL_DIRS.items():
        for skill in sorted((VENDOR / directory).glob("*/SKILL.md")):
            if skill.parent.name not in VENDOR_SKIP and (chosen is None or skill.parent.name in chosen):
                skills[skill.parent.name] = skill.parent
    return skills


def self_invoking(name):
    return name in SELF_INVOKING_SKILLS


def without_model_lock(text):
    header = re.match(r"---\n.*?\n---\n", text, re.S)
    if not header:
        return text
    return re.sub(rf"^{MODEL_LOCK_KEY}:.*\n", "", header.group(0), flags=re.M) + text[header.end():]


def declared_upstream_skills():
    return {skill for skills in json.loads((REPO / "upstream/skills.json").read_text()).values() for skill in skills}


def profile_catalog():
    return json.loads(PROFILES_JSON.read_text()) if PROFILES_JSON.is_file() else {}


def active_profiles(state=None):
    if state is None:
        state_file = STATE_DIR / "state.json"
        state = json.loads(state_file.read_text()) if state_file.is_file() else {}
    return [name for name in state.get("profiles") or [] if isinstance(name, str)]


def profile_skill_names(state=None):
    catalog = profile_catalog()
    return {skill for name in active_profiles(state) for skills in catalog.get(name, {}).values() for skill in skills}


@contextlib.contextmanager
def state_lock():
    STATE_DIR.mkdir(exist_ok=True)
    with open(STATE_DIR / "lock", "w") as lock:
        fcntl.flock(lock, fcntl.LOCK_EX)
        yield


def git(*args, timeout=5):
    return subprocess.run([*GIT, *args], text=True, capture_output=True, timeout=timeout,
                          env={**os.environ, "GIT_TERMINAL_PROMPT": "0"})


def vendor_git(path, *args):
    return subprocess.run(["git", "-C", str(path), *args], text=True, capture_output=True, check=True).stdout.strip()


def vendor_pin_problems():
    problems = []
    for name, source in json.loads((REPO / "upstream/vendor.json").read_text()).items():
        path = VENDOR / name
        if not re.fullmatch(r"[0-9a-f]{40}", source.get("rev", "")):
            problems.append(f"no full pinned rev for {name} in upstream/vendor.json; run kolin-skills upstream --bump")
        elif (path / ".git").is_dir() and vendor_git(path, "rev-parse", "HEAD") != source["rev"]:
            problems.append(f"{name} is not at its pinned rev {source['rev'][:12]}; run kolin-skills upstream")
    return problems


def frontmatter_keys(skill_file):
    lines = skill_file.read_text().splitlines()
    if not lines or lines[0].strip() != "---":
        return {}
    keys = {}
    for line in lines[1:]:
        if line.strip() == "---":
            return keys
        key, separator, value = line.partition(":")
        if separator and not line.startswith((" ", "\t")):
            keys[key.strip()] = value.strip()
    return {}


def model_locked(skill_file):
    return skill_file.is_file() and MODEL_LOCK_KEY in frontmatter_keys(skill_file)


def without_git_repo_env():
    local = git("rev-parse", "--local-env-vars").stdout.split()
    return {key: value for key, value in os.environ.items() if key not in local}


def running_in_ci():
    return os.environ.get("CI", "").lower() in CI_VALUES


def line_count(path):
    data = path.read_bytes()
    if not data or b"\0" in data:
        return 0
    return data.count(b"\n") + (0 if data.endswith(b"\n") else 1)

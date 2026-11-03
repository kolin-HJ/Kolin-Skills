import hashlib
import json
import os
import pathlib
import re
import shutil
import subprocess
import sys
import time

import third_party
from kolin_skills.apply import points_into_managed_tree, run_apply
from kolin_skills.helpers import (
    DERIVED, HOME, LINKS, MAX_FILE_LINES, MODEL_LOCK_KEY, OWN_SKILL_HOMES, QUICK_CHECK_SECONDS,
    REPO, REQUIRED_TOOLS, SELF_INVOKING_SKILLS, SKILL_INDEXES, SPEND_CAPS, VENDOR,
    VENDOR_SKILL_HOMES, frontmatter_keys, line_count, model_locked, running_in_ci, self_invoking,
    vendor_skills, wired_repo, without_git_repo_env,
)

PSTACK_SOURCE = ".agents/PSTACK.SOURCE"
VENDOR_JSONS = ("upstream/vendor.json", ".agents/vendor.json")
VENDOR_CLONE = ".agents/vendor/cursor-plugins"
SYNCED_REVIEWER = ".claude/agents/senior-reviewer.md"
REV_LINE = re.compile(r"(?im)^(commit|rev|sha):\s*([0-9a-f]{7,40})\b")
CONSUMER_POLICY_PATHS = (
    "AGENTS.md", "CLAUDE.md", ".claude/CLAUDE.md", ".claude/AGENTS.md", "policy/AGENTS.md",
)
REVIEWER_ACTOR = re.compile(
    r"(?i)\b(senior-reviewer|interrogate|thermo(?:-nuclear[\w-]*)?|(?:ai\s+)?(?:code\s+)?reviewer|formal\s+verification|statechart)s?\b"
)
EVERY_REVIEWER_GATE = re.compile(r"(?i)\b(every|each)\s+(?:\w+\s+){0,2}?(pr\b|pull\s+request|staging\s+merge)")
REVIEW_RECEIPT_GATE = re.compile(
    r"(?i)\bran:\s*(?:senior-reviewer|interrogate|thermo[\w-]*|(?:ai\s+)?(?:code\s+)?reviewer)\b"
    r"|\bno\s+not\s+run\s+line\s+excuses?\b"
)
REVIEWER_WINDOW = 3
PRE_PR_LINE_GATE = re.compile(
    r"(?i)before\s+the\s+pr\s+opens.{0,160}150\s+lines|150\s+lines.{0,160}(?:interrogate|senior-reviewer)"
)
ASK_ONLY_REVIEW = re.compile(
    r"(?i)only on high-risk|high-risk or ask|ask-only|on demand|when kolin|when the ceo|"
    r"not a quality gate|do not spawn|never spawn|proof of behavior"
)


def spend_failures():
    settings = json.loads((REPO / "claude/settings.json").read_text())
    failures = []
    if settings.get("env", {}).get("CLAUDE_CODE_SUBAGENT_MODEL") != SPEND_CAPS["subagent_model"]:
        failures.append(f"claude settings env.CLAUDE_CODE_SUBAGENT_MODEL must be {SPEND_CAPS['subagent_model']} so subagents without a model skip Opus")
    window = settings.get("autoCompactWindow")
    if not isinstance(window, int) or window > SPEND_CAPS["max_compact_window"]:
        failures.append(f"claude settings autoCompactWindow must be at most {SPEND_CAPS['max_compact_window']}")
    if "agent-default-model.py" not in json.dumps(settings.get("hooks", {}).get("PreToolUse", [])):
        failures.append("claude settings PreToolUse must run hooks/agent-default-model.py so a repo copy of senior-reviewer cannot pin below Opus")
    return failures


def overlong_files(root=REPO, limit=MAX_FILE_LINES):
    listed = subprocess.run(["git", "-C", str(root), "ls-files", "-z"], capture_output=True)
    if listed.returncode:
        return []
    found = []
    for raw in listed.stdout.split(b"\0"):
        if not raw:
            continue
        name = os.fsdecode(raw)
        path = root / name
        if path.is_file():
            lines = line_count(path)
            if lines > limit:
                found.append(f"{name}: {lines} lines")
    return found


def pinned_cursor_plugins_rev():
    return json.loads((REPO / "upstream/vendor.json").read_text())["cursor-plugins"]["rev"]


def same_git_rev(recorded, pinned):
    left, right = recorded.lower(), pinned.lower()
    return left == right or (len(left) >= 7 and right.startswith(left)) or (len(right) >= 7 and left.startswith(right))


def rev_from_source(path):
    text = path.read_text()
    match = REV_LINE.search(text)
    if match:
        return match.group(2)
    stripped = text.strip()
    return stripped if re.fullmatch(r"[0-9a-f]{7,40}", stripped, re.I) else None


def cursor_plugins_rev(data):
    plugin = data.get("cursor-plugins") if isinstance(data, dict) else None
    if not isinstance(plugin, dict):
        return None
    rev = plugin.get("rev") or plugin.get("commit")
    if isinstance(rev, str) and re.fullmatch(r"[0-9a-f]{7,40}", rev.lower()):
        return rev
    return None


def recorded_pstack_revs(target):
    found = []
    source = target / PSTACK_SOURCE
    if source.is_file():
        found.append((PSTACK_SOURCE, rev_from_source(source)))
    for relative in VENDOR_JSONS:
        path = target / relative
        if not path.is_file():
            continue
        try:
            data = json.loads(path.read_text())
        except json.JSONDecodeError:
            found.append((f"{relative} cursor-plugins.rev", None))
            continue
        if isinstance(data, dict) and "cursor-plugins" in data:
            found.append((f"{relative} cursor-plugins.rev", cursor_plugins_rev(data)))
    clone = target / VENDOR_CLONE
    if (clone / ".git").exists():
        result = subprocess.run(["git", "-C", str(clone), "rev-parse", "HEAD"], text=True, capture_output=True, timeout=5)
        found.append((VENDOR_CLONE, result.stdout.strip() if result.returncode == 0 else None))
    return found


def policy_paragraphs(text):
    stripped = re.sub(r"`+", "", text)
    stripped = re.sub(r"\[([^\]]+)\]\([^)]+\)", r"\1", stripped)
    paragraphs = []
    for para in re.split(r"\n\s*\n", stripped):
        chunks = []
        for item in re.split(r"(?:\n\s*[-*]\s+|(?<=[.!?])\s+)", para):
            chunk = re.sub(r"\s+", " ", item).strip(" -*")
            if chunk:
                chunks.append(chunk)
        if chunks:
            paragraphs.append(chunks)
    return paragraphs


def requires_reviewer_everywhere(chunks):
    for index, chunk in enumerate(chunks):
        window = " ".join(chunks[max(0, index - REVIEWER_WINDOW + 1):index + 1])
        if ASK_ONLY_REVIEW.search(window) or not REVIEWER_ACTOR.search(window):
            continue
        if (EVERY_REVIEWER_GATE.search(chunk) or REVIEW_RECEIPT_GATE.search(chunk)
                or PRE_PR_LINE_GATE.search(chunk)):
            return True
    return False


def reviewer_gate_problems(target):
    problems = []
    for relative in CONSUMER_POLICY_PATHS:
        path = target / relative
        if not path.is_file():
            continue
        if any(requires_reviewer_everywhere(chunks) for chunks in policy_paragraphs(path.read_text())):
            problems.append(
                f"{relative} still requires a separate reviewer on every PR or every staging merge; "
                "same-session proof is the quality gate (Kolin-Skills #90). "
                "Replace it with high-risk or ask-only language, as in Kolin-Skills policy/AGENTS.md"
            )
    return problems


def consumer_drift_problems(target):
    pin = pinned_cursor_plugins_rev()
    problems = []
    for label, rev in recorded_pstack_revs(target):
        if not rev:
            problems.append(f"{label} has no cursor/plugins rev; record the pin from Kolin-Skills upstream/vendor.json ({pin[:12]})")
        elif not same_git_rev(rev, pin):
            problems.append(f"{label} is {rev[:12]}, not the Kolin-Skills pin {pin[:12]} in upstream/vendor.json; refresh from that rev or stop vendoring and run kolin-skills apply")
    reviewer = target / SYNCED_REVIEWER
    canonical = REPO / "agents/senior-reviewer.md"
    if reviewer.is_symlink() and not reviewer.exists():
        problems.append(f"{SYNCED_REVIEWER} is a broken symlink; replace it from Kolin-Skills agents/senior-reviewer.md or run kolin-skills apply")
    elif reviewer.is_file() and reviewer.resolve() != canonical.resolve() and hashlib.sha256(reviewer.read_bytes()).digest() != hashlib.sha256(canonical.read_bytes()).digest():
        problems.append(f"{SYNCED_REVIEWER} does not match Kolin-Skills agents/senior-reviewer.md ({line_count(reviewer)} lines vs {line_count(canonical)}); replace it from the repo or delete the copy and run kolin-skills apply")
    return problems + reviewer_gate_problems(target)


def check_drift(target_raw):
    target = pathlib.Path(target_raw).expanduser().resolve()
    if not target.is_dir():
        print(f"FAIL: {target} is not a directory", file=sys.stderr)
        return 1
    problems = consumer_drift_problems(target)
    for problem in problems:
        print(f"FAIL: {problem}", file=sys.stderr)
    if problems:
        return 1
    print(f"Passed: vendored pstack SOURCE/rev, synced senior-reviewer, and consumer reviewer-gate policy match Kolin-Skills, or are absent, at {target}")
    return 0


def unloadable_skill_problems():
    problems = []
    for skill in sorted((REPO / "skills").glob("*/SKILL.md")):
        keys = frontmatter_keys(skill)
        for required in ("name", "description"):
            if not keys.get(required):
                problems.append(f"skills/{skill.parent.name}/SKILL.md has no frontmatter {required}; Claude Code cannot list it")
    for home in OWN_SKILL_HOMES:
        directory = HOME / home
        for path in sorted(directory.iterdir()) if directory.is_dir() else []:
            if path.is_symlink() and points_into_managed_tree(path, [str(REPO / "skills"), str(VENDOR)]) and not (path / "SKILL.md").is_file():
                problems.append(f"~/{home}/{path.name} links to {os.readlink(path)}, which has no SKILL.md; run kolin-skills apply")
    return problems


def broken_link_problems():
    candidates = [HOME / destination for destinations in LINKS.values() for destination in destinations]
    for home in [*OWN_SKILL_HOMES, ".claude/agents"]:
        directory = HOME / home
        candidates += sorted(directory.iterdir()) if directory.is_dir() else []
    tops = sorted(DERIVED.iterdir()) if DERIVED.is_dir() else []
    candidates += tops + [child for top in tops if top.is_dir() and not top.is_symlink() for child in top.iterdir()]
    return [f"~/{path.relative_to(HOME)} links to {os.readlink(path)}, which does not exist; run kolin-skills apply"
            for path in candidates if path.is_symlink() and not path.exists()]


def self_invoking_skill_problems():
    problems = [f"~/.agents/skills/{name} is not installed; run kolin-skills upstream"
                for name in sorted(SELF_INVOKING_SKILLS) if not (HOME / ".agents/skills" / name / "SKILL.md").is_file()]
    for home in VENDOR_SKILL_HOMES:
        directory = HOME / home
        for path in sorted(directory.iterdir()) if directory.is_dir() else []:
            if self_invoking(path.name) and model_locked(path / "SKILL.md"):
                problems.append(f"~/{home}/{path.name}/SKILL.md sets {MODEL_LOCK_KEY}, so the agent cannot start it; run kolin-skills apply")
    return problems


def check_quick():
    started = time.monotonic()
    owner = wired_repo()
    failures = []
    if owner is None:
        failures.append("home is not wired to any checkout; run kolin-skills install")
    elif owner != str(REPO):
        failures.append(f"home is wired to {owner}, not this checkout ({REPO}); run kolin-skills apply --adopt")
    elif run_apply(check=True, quiet=True):
        failures.append("home differs from the repo; fix each line above")
    failures += broken_link_problems() + self_invoking_skill_problems()
    elapsed = time.monotonic() - started
    if elapsed > QUICK_CHECK_SECONDS:
        failures.append(f"the quick check took {elapsed:.1f}s, over its {QUICK_CHECK_SECONDS}s budget")
    for failure in failures:
        print(f"FAIL: {failure}", file=sys.stderr)
    if failures:
        return 1
    print(f"Passed: quick check, links, hooks, policy and self-invoking skills, in {elapsed:.2f}s")
    return 0


def check(files_only=False):
    failures = [f"{entry}, over the {MAX_FILE_LINES}-line limit; split it in its own change"
                for entry in overlong_files()]
    failures += unloadable_skill_problems()
    if files_only:
        for failure in failures:
            print(f"FAIL: {failure}", file=sys.stderr)
        return 1 if failures else 0
    test_env = without_git_repo_env()
    if running_in_ci():
        print("CI: skipped home drift and vendored skills.")
    else:
        owner = wired_repo()
        if owner not in (None, str(REPO)):
            print(f"Home is wired to {owner}, so home drift was not checked; this run checks the repo only.")
        elif run_apply(check=True, quiet=True):
            failures.append("home differs from the repo; fix each line above")
        if not vendor_skills():
            failures.append(f"no vendored skills under {VENDOR}; run kolin-skills upstream")
        failures += third_party.npm_tool_problems(REPO)
    failures += spend_failures()
    skills = sorted(path.parent.name for path in (REPO / "skills").glob("*/SKILL.md"))
    for index in SKILL_INDEXES:
        text = (REPO / index).read_text()
        missing = [name for name in skills if f"`{name}`" not in text and f"{name}/" not in text]
        if missing:
            failures.append(f"{index} does not list {', '.join(missing)}; add each to its skill index")
    for tool, purpose in REQUIRED_TOOLS.items():
        if shutil.which(tool) is None:
            failures.append(f"{tool} is missing from PATH; {purpose}")
    try:
        tests = subprocess.run([sys.executable, "-m", "unittest", "discover", "-s", str(REPO / "tests")],
                               cwd=REPO, env=test_env, text=True, capture_output=True, timeout=300)
        summary = tests.stderr.strip().splitlines()
        if summary:
            print(summary[-1])
        if tests.returncode:
            print(tests.stderr, file=sys.stderr)
            failures.append("tests failed")
    except subprocess.TimeoutExpired:
        failures.append("python tests timed out after 300s; run python3 -m unittest discover -s tests to find the hang")
    try:
        template_tests = subprocess.CompletedProcess([], 0) if shutil.which("node") is None else subprocess.run(["node", "--test", "skills/*/assets/**/*.test.mjs"],
                                        cwd=REPO, env=test_env, text=True, capture_output=True, timeout=300)
        if template_tests.returncode:
            print(template_tests.stdout, file=sys.stderr)
            failures.append("skill asset tests failed")
    except subprocess.TimeoutExpired:
        failures.append("skill asset tests timed out after 300s; run node --test on skills/*/assets to find the hang")
    try:
        budget = subprocess.run([sys.executable, str(REPO / "bin/feature-budget"), str(REPO)],
                                cwd=REPO, env=test_env, text=True, capture_output=True, timeout=60)
        sys.stdout.write(budget.stdout)
        sys.stderr.write(budget.stderr)
    except subprocess.TimeoutExpired:
        print("feature-budget timed out (report-only)")
    for failure in failures:
        print(f"FAIL: {failure}", file=sys.stderr)
    if failures:
        return 1
    print("Passed: home drift and strays (unless skipped above), spend caps, 1,000-line files, skill indexes, required tools, vendored and third-party skills, pinned CLIs, Python and Node tests, feature-budget (report-only).")
    print("Live agent routing and model-role readiness are not checked.")
    return 0

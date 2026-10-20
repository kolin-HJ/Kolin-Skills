#!/usr/bin/env python3
import json
import os
import re
import subprocess
import sys
import time

LINTABLE = {".js", ".jsx", ".mjs", ".cjs", ".ts", ".tsx"}
COSMETIC = {
    "arrow-parens", "block-spacing", "brace-style", "comma-dangle",
    "comma-spacing", "eol-last", "indent", "key-spacing", "linebreak-style",
    "max-len", "no-irregular-whitespace", "no-multi-spaces", "no-tabs",
    "no-trailing-spaces", "object-curly-spacing", "one-var",
    "operator-linebreak", "padded-blocks", "prettier/prettier", "quote-props",
    "quotes", "semi", "semi-spacing", "space-before-blocks",
    "space-before-function-paren", "space-infix-ops", "spaced-comment",
}
MAX_REPORT = 12
HUNK = re.compile(r"^@@ -\d+(?:,\d+)? \+(\d+)(?:,(\d+))? @@")
PATCH_FILE = re.compile(r"^\*\*\* (?:Add|Update) File: (.+?)\s*$", re.M)
PATH_KEYS = ("file_path", "path", "target_file", "filePath", "relative_workspace_path")
PATCH_KEYS = ("command", "input", "patch")
SHELL_WRITE = re.compile(
    r"\bsed\b[^|;&\n]*\s(?:-\w*i|--in-place)|\bperl\s+-\w*i|write_text|\.write\(|open\([^\n]*?,\s*['\"][wa]"
    r"|<<|\btee\b|>>?\s*['\"]?[^\s'\"&]+\.(?:tsx?|jsx?|mjs|cjs)\b")
SHELL_WRITE_WINDOW = 120
MAX_PATHS = 4
DEADLINE_SECONDS = 40
LINT_TIMEOUT_SECONDS = 45


def find_up(start, rel):
    d = start
    while True:
        candidate = os.path.join(d, rel)
        if os.path.exists(candidate):
            return candidate
        parent = os.path.dirname(d)
        if parent == d:
            return None
        d = parent


def touched_paths(payload, cwd):
    tool_input = payload.get("tool_input") or payload.get("toolInput") or {}
    if isinstance(tool_input, str):
        tool_input = {"command": tool_input}
    found = []
    for key in PATH_KEYS:
        value = tool_input.get(key)
        if isinstance(value, str):
            found.append(value)
    for key in PATCH_KEYS:
        value = tool_input.get(key)
        if isinstance(value, list):
            value = "\n".join(map(str, value))
        if isinstance(value, str) and "*** Begin Patch" in value:
            found.extend(PATCH_FILE.findall(value))
    if payload.get("tool_name") == "Bash" and isinstance(tool_input.get("command"), str):
        found.extend(shell_written_paths(tool_input["command"], cwd))
    top = payload.get("file_path")
    if isinstance(top, str):
        found.append(top)
    return [p if os.path.isabs(p) else os.path.join(cwd, p) for p in found]


def shell_written_paths(command, cwd):
    if not SHELL_WRITE.search(command):
        return []
    top = subprocess.run(["git", "-C", cwd, "rev-parse", "--show-toplevel"],
                         capture_output=True, text=True).stdout.strip()
    if not top:
        return []
    listed = subprocess.run(
        ["git", "-C", top, "ls-files", "-m", "-o", "--exclude-standard"],
        capture_output=True, text=True,
    )
    if listed.returncode != 0:
        return []
    cutoff = time.time() - SHELL_WRITE_WINDOW
    paths = [os.path.join(top, name) for name in listed.stdout.splitlines()]
    return [p for p in paths if os.path.basename(p) in command
            and os.path.isfile(p) and os.path.getmtime(p) >= cutoff]


def changed_lines(path):
    d = os.path.dirname(path)
    if subprocess.run(["git", "-C", d, "rev-parse"], capture_output=True).returncode != 0:
        return None
    tracked = subprocess.run(
        ["git", "-C", d, "ls-files", "--error-unmatch", path],
        capture_output=True,
    ).returncode == 0
    if not tracked:
        return None
    diff = subprocess.run(
        ["git", "-C", d, "diff", "-U0", "--no-color", "HEAD", "--", path],
        capture_output=True, text=True,
    ).stdout
    lines = set()
    for m in filter(None, map(HUNK.match, diff.splitlines())):
        start, count = int(m.group(1)), int(m.group(2) or 1)
        lines.update(range(start, start + count))
    return lines


OXLINT_CONFIGS = (".oxlintrc.json", "oxlint.config.ts")


def lint_did_not_run(linter, outcome, output):
    reason = output.strip().splitlines()
    return {
        "ruleId": "lint-did-not-run",
        "line": 0,
        "column": 0,
        "severity": 1,
        "message": "{} {} and checked nothing: {}".format(
            linter, outcome, reason[0][:200] if reason else "no output"),
    }


def lint(path):
    pkg = find_up(os.path.dirname(path), "package.json")
    if not pkg:
        return []
    root = os.path.dirname(pkg)
    messages = []
    for name, linter in (("eslint", eslint_messages), ("oxlint", oxlint_messages)):
        try:
            messages += linter(path, root)
        except subprocess.TimeoutExpired:
            messages.append(lint_did_not_run(name, "timed out after {}s".format(LINT_TIMEOUT_SECONDS), ""))
    return messages


def eslint_messages(path, root):
    eslint = os.path.join(root, "node_modules/.bin/eslint")
    if not os.path.exists(eslint):
        return []
    base = [eslint, "--format", "json", "--no-error-on-unmatched-pattern"]
    run = subprocess.run(base + ["--pass-on-unpruned-suppressions", path],
                         cwd=root, capture_output=True, text=True, timeout=LINT_TIMEOUT_SECONDS)
    if run.returncode == 2 and "pass-on-unpruned-suppressions" in run.stderr:
        run = subprocess.run(base + [path], cwd=root, capture_output=True, text=True, timeout=LINT_TIMEOUT_SECONDS)
    if run.returncode not in (0, 1):
        return [lint_did_not_run("eslint", "exited {}".format(run.returncode), run.stderr or run.stdout)]
    try:
        results = json.loads(run.stdout)
    except json.JSONDecodeError:
        return [lint_did_not_run("eslint", "exited {}".format(run.returncode), run.stdout)]
    return [m for r in results for m in r.get("messages", []) if m.get("ruleId")]


def oxlint_messages(path, root):
    oxlint = os.path.join(root, "node_modules/.bin/oxlint")
    if not os.path.exists(oxlint) or not any(
            os.path.exists(os.path.join(root, c)) for c in OXLINT_CONFIGS):
        return []
    cmd = [oxlint, "--format", "json"]
    if os.path.exists(os.path.join(root, "node_modules/.bin/tsgolint")):
        cmd.append("--type-aware")
    run = subprocess.run(cmd + [path], cwd=root, capture_output=True, text=True, timeout=LINT_TIMEOUT_SECONDS)
    if run.returncode not in (0, 1):
        return [lint_did_not_run("oxlint", "exited {}".format(run.returncode), run.stderr or run.stdout)]
    try:
        diagnostics = json.loads(run.stdout).get("diagnostics", [])
    except json.JSONDecodeError:
        return [lint_did_not_run("oxlint", "exited {}".format(run.returncode), run.stdout)]
    messages = []
    for d in diagnostics:
        spans = [label["span"] for label in d.get("labels", []) if "span" in label]
        if not spans or not d.get("code"):
            continue
        messages.append({
            "ruleId": d["code"],
            "line": spans[0]["line"],
            "column": spans[0]["column"],
            "severity": 2 if d.get("severity") == "error" else 1,
            "message": d["message"],
        })
    return messages


def report_for(path, cwd):
    messages = lint(path)
    if not messages:
        return None
    touched = changed_lines(path)
    relevant = [
        m for m in messages
        if m["ruleId"] not in COSMETIC
        and (touched is None or m["line"] in touched or m["ruleId"] == "lint-did-not-run")
    ]
    if not relevant:
        return None
    errors = sum(1 for m in relevant if m["severity"] == 2)
    label = "error" if errors else "warning"
    header = "Lint: {} {}{} on lines you changed in {}".format(
        len(relevant), label, "" if len(relevant) == 1 else "s",
        os.path.relpath(os.path.realpath(path), os.path.realpath(cwd)))
    body = "\n".join(
        "  {}:{}  {}  {}  ({})".format(
            m["line"], m["column"], "error" if m["severity"] == 2 else "warn ",
            m["message"], m["ruleId"])
        for m in relevant[:MAX_REPORT]
    )
    if len(relevant) > MAX_REPORT:
        body += "\n  … {} more".format(len(relevant) - MAX_REPORT)
    return {"text": header + "\n" + body, "errors": errors}


def main(argv):
    emit = "exit2"
    if "--emit" in argv:
        i = argv.index("--emit")
        emit = argv[i + 1]
        argv = argv[:i] + argv[i + 2:]

    payload = {}
    if not sys.stdin.isatty():
        raw = sys.stdin.read().strip()
        if raw:
            payload = json.loads(raw)
    cwd = payload.get("cwd") or os.getcwd()
    paths = [os.path.abspath(p) for p in argv] or touched_paths(payload, cwd)
    paths = [p for p in dict.fromkeys(paths)
             if os.path.splitext(p)[1] in LINTABLE and os.path.isfile(p)]
    if not paths:
        return 0

    started = time.monotonic()
    reports, skipped = [], paths[MAX_PATHS:]
    for i, path in enumerate(paths[:MAX_PATHS]):
        if time.monotonic() - started > DEADLINE_SECONDS:
            skipped = paths[i:]
            break
        report = report_for(path, cwd)
        if report:
            reports.append(report)
    footer = "Problems on lines you did not touch are not shown."
    if skipped:
        footer += " Not linted, so run the repo's lint for: {}.".format(
            ", ".join(os.path.relpath(os.path.realpath(p), os.path.realpath(cwd)) for p in skipped))
    if not reports and not skipped:
        return 0

    text = "\n\n".join(r["text"] for r in reports) or "Lint: no problems in the files checked."
    has_errors = any(r["errors"] for r in reports)

    if emit == "cursor":
        print(json.dumps({"additional_context": text + "\n" + footer}))
        return 0
    if has_errors:
        print(text + "\nFix these before continuing. " + footer, file=sys.stderr)
        return 2
    print(json.dumps({"hookSpecificOutput": {
        "hookEventName": "PostToolUse",
        "systemMessage": text + "\n" + footer,
    }}))
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))

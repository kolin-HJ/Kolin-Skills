#!/usr/bin/env python3
import json
import os
import posixpath
import re
import shlex
import subprocess
import sys
from urllib.parse import unquote

SKIP_FLAG = "--no-" + "verify"
SEPARATORS = {";", "&&", "||", "|", "&", "|&", "(", ")", "`", "{", "}"}
PREFIX_WORDS = {"env", "sudo", "command", "exec", "time", "nohup", "builtin", "nice", "xargs", "timeout"}
PREFIX_WITH_VALUE = {"env": {"-u", "-C", "-S"}, "timeout": {"-k", "-s", "--kill-after", "--signal"}}
SHELLS = {"bash", "sh", "zsh", "dash"}
GIT_OPTS_WITH_VALUE = {"-C", "-c", "--git-dir", "--work-tree", "--namespace", "--exec-path"}
PUSH_OPTS_WITH_VALUE = {"-o", "--push-option", "--receive-pack", "--exec", "--repo", "--signed", "--recurse-submodules", "--force-with-lease"}
HOOK_SUBCOMMANDS = {"commit", "push", "merge", "rebase", "am", "cherry-pick", "revert"}
MERGE_WORDS = re.compile(r"merge|automerge|auto_merge|enablePullRequestAutoMerge", re.I)
PROTECTED_BRANCH = re.compile(r"^(main|master|staging|sandbox)$", re.I)
PROTECTED_REF = re.compile(r"(git/refs/heads/(main|master|staging|sandbox)$|branches/(main|master|staging|sandbox)(/|$))", re.I)
REF_MUTATIONS = re.compile(r"\b(updateRefs?|deleteRef|createCommitOnBranch)\b")
API_FIELD_FLAGS = {"-f", "-F", "--field", "--raw-field", "--input"}
COMMENT_HIDES_CODE = re.compile(r"[;&|`$()<>'\"\\\r]")
HEREDOC = re.compile(r"<<-?\s*(['\"]?)([A-Za-z_][A-Za-z0-9_]*)\1")
API_OPTS_WITH_VALUE = {"-H", "--header", "-q", "--jq", "-t", "--template", "--hostname", "--cache", "-p", "--preview"}
HOOK_DIRS = (r"\.claude/hooks", r"\.git/hooks", r"\.git/config", r"\.githooks", r"\.husky", r"lefthook\.ya?ml")
HOOK_PATH = re.compile("(" + "|".join((r"kolin-skills/hooks",) + HOOK_DIRS) + ")")
FILE_HOOK_PATH = re.compile("(" + "|".join(HOOK_DIRS) + ")", re.I)
HOOKS_PATH_CONFIG = re.compile(r"^(--config-env=)?core\.hookspath(=|$)", re.I)
SUBSTITUTION = re.compile(r"\$\((.*)\)|`([^`]*)`", re.S)
HOOK_ENV_OFF = re.compile(r"^(HUSKY=0|LEFTHOOK=(0|false)|LEFTHOOK_EXCLUDE=.+|LEFTHOOK_BIN=.+|SKIP=.+)$")
SIGN_SKIP_FLAG = "--no-gpg-sign"
GIT_CONFIG_HOOKS_ENV = re.compile(r"^(GIT_CONFIG_KEY_\d+=core\.hookspath$|GIT_CONFIG_PARAMETERS=.*core\.hookspath)", re.I)
ENV_DECLARERS = {"export", "declare", "typeset"}
READ_ONLY_GIT = {"status", "log", "diff", "show", "rev-parse", "ls-files", "blame", "grep", "fetch", "rev-list",
                 "merge-base", "for-each-ref", "ls-remote", "describe", "cat-file"}
BRANCH_VALUE_FLAGS = {"--merged", "--no-merged", "--contains", "--no-contains"}
BRANCH_READS = {"--show-current", "--list", "-a", "-r", "-v", "-vv"} | BRANCH_VALUE_FLAGS
CONFIG_READS = {"--get", "--get-all", "--get-regexp", "--list", "-l", "get", "list"}
CONFIG_SCOPE_OPTS = {"--global", "--system", "--local", "--worktree", "--show-origin", "--show-scope", "--includes",
                     "--no-includes", "--null", "-z"}
WORKTREE_ALLOWED = {"add", "list", "prune", "remove"}
INSTALL_FILE_MESSAGE = (
    "This checkout is the live install every session runs from. "
    "Make the change in a Kolin-Skills worktree and ship it through a PR."
)
INSTALL_MESSAGE = (
    "This checkout is the live install every session runs from. Only `kolin-skills pull` updates it. "
    "Work in a worktree: `git -C {install} worktree add ~/.t3/worktrees/Kolin-Skills/<name> -b <branch> origin/main`."
)
WRITERS = {"cp", "mv", "rm", "ln", "tee", "chmod", "install", "truncate", "touch", "dd", "rsync"}
DANGEROUS_PUSH_LONG = ("--force", "--delete", "--mirror", "--prune")
DANGEROUS_PUSH_PREFIX = ("--for", "--de", "--m", "--pru")
FORBIDDEN_PUSH_MSG = "force-push, delete and mirror pushes are forbidden. Push a new commit to a work branch instead."
MCP_MERGE_TOOLS = {"mcp__t3-code__pull_request_merge", "mcp_t3-code_pull_request_merge"}


class ParseError(Exception):
    pass


def split_heredocs(text):
    lines = text.split("\n")
    kept, bodies, i = [], [], 0
    while i < len(lines):
        line = lines[i]
        kept.append(line)
        tags = [m.group(2) for m in HEREDOC.finditer(line)]
        i += 1
        for tag in tags:
            body = []
            while i < len(lines) and lines[i].strip() != tag:
                body.append(lines[i])
                i += 1
            if i >= len(lines):
                raise ParseError("unterminated heredoc")
            i += 1
            bodies.append((line, "\n".join(body)))
    return "\n".join(kept), bodies


def strip_comment(line):
    i, quote, prev = 0, None, " "
    while i < len(line):
        c = line[i]
        if c == "\\" and quote != "'":
            prev, i = "x", i + 2
            continue
        if quote:
            quote = None if c == quote else quote
        elif c in "'\"":
            quote = c
        elif c == "#" and prev in " \t;&|()<>`" and not COMMENT_HIDES_CODE.search(line[i:]):
            return line[:i]
        prev, i = c, i + 1
    return line


def lex(line):
    lexer = shlex.shlex(strip_comment(line), posix=True, punctuation_chars=";&|()<>`")
    lexer.whitespace = " \t\r"
    lexer.whitespace_split = True
    lexer.commenters = ""
    return list(lexer)


def logical_lines(text):
    joined = re.sub(r"\\\n", " ", text)
    pending = None
    for line in joined.split("\n"):
        pending = line if pending is None else pending + "\n" + line
        try:
            tokens = lex(pending)
        except ValueError:
            continue
        pending = None
        yield tokens
    if pending is not None:
        raise ParseError("unterminated quote")


def segments(text):
    for tokens in logical_lines(text):
        current = []
        for token in tokens:
            if token in SEPARATORS:
                if current:
                    yield current
                current = []
            else:
                current.append(token)
        if current:
            yield current


def program(word):
    return word.rsplit("/", 1)[-1]


def strip_prefix(words):
    i = 0
    while i < len(words):
        word = words[i]
        if re.match(r"^[A-Za-z_][A-Za-z0-9_]*=", word):
            i += 1
        elif program(word) in PREFIX_WORDS:
            name = program(word)
            val_flags = PREFIX_WITH_VALUE.get(name, set())
            i += 1
            while i < len(words) and words[i].startswith("-") and words[i] != "--":
                flag = words[i]
                i += 2 if flag in val_flags and i + 1 < len(words) else 1
            if i < len(words) and words[i] == "--":
                i += 1
            if name == "timeout" and i < len(words) and re.fullmatch(r"\d+(?:\.\d+)?[smhd]?", words[i]):
                i += 1
        else:
            break
    return words[i:]


def git_subcommand(words):
    i, configs = 1, []
    while i < len(words):
        word = words[i]
        if word == "-c" and i + 1 < len(words):
            configs.append(words[i + 1])
            i += 2
        elif word.startswith("-c") and len(word) > 2:
            configs.append(word[2:])
            i += 1
        elif word.startswith("--config-env="):
            configs.append(word)
            i += 1
        elif word in GIT_OPTS_WITH_VALUE:
            i += 2
        elif word.startswith("-"):
            i += 1
        else:
            return word, words[i + 1:], configs
    return None, [], configs


def git_target(words, cwd):
    target = cwd
    i = 1
    while i < len(words):
        word = words[i]
        if word == "-C" and i + 1 < len(words):
            target = os.path.join(target, os.path.expanduser(words[i + 1]))
            i += 2
        elif word in GIT_OPTS_WITH_VALUE:
            i += 2
        elif word.startswith("-"):
            i += 1
        else:
            break
    return target


def toplevel(directory):
    if not os.path.isdir(directory):
        return None
    found = subprocess.run(["git", "-C", directory, "rev-parse", "--show-toplevel"], text=True, capture_output=True)
    return os.path.realpath(found.stdout.strip()) if found.returncode == 0 else None


def live_install():
    link = os.path.join(os.path.expanduser("~"), ".claude", "CLAUDE.md")
    return toplevel(os.path.dirname(os.path.realpath(link))) if os.path.exists(link) else None


def read_only_in_install(sub, args):
    if sub is None or sub in READ_ONLY_GIT:
        return True
    if sub == "worktree":
        return bool(args) and args[0] in WORKTREE_ALLOWED
    if sub == "stash":
        return args[:1] == ["list"]
    if sub == "branch":
        return all(arg in BRANCH_READS or (not arg.startswith("-") and previous in BRANCH_VALUE_FLAGS)
                   for previous, arg in zip([None] + args, args))
    if sub == "remote":
        return all(arg in ("-v", "--verbose") for arg in args)
    if sub == "config":
        return bool(args) and (args[0] in CONFIG_READS or (len(args) == 1 and not args[0].startswith("-")))
    return False


def install_guard(cwd):
    install = live_install()
    state = {"cwd": os.path.realpath(cwd or ".")}

    def check(words, raw):
        words = strip_prefix(words)
        if not install or not words:
            return False
        if words[0] in ("cd", "pushd"):
            destination = os.path.expanduser(words[1]) if len(words) > 1 else os.path.expanduser("~")
            state["cwd"] = os.path.realpath(os.path.join(state["cwd"], destination))
            return False
        if program(words[0]).lower() != "git":
            return False
        sub, args, _ = git_subcommand(words)
        if toplevel(git_target(words, state["cwd"])) != install or read_only_in_install(sub, args):
            return False
        return INSTALL_MESSAGE.format(install=install)

    return check


def skips_hooks(words, raw):
    if words[0] in ENV_DECLARERS and any(HOOK_ENV_OFF.match(w) or GIT_CONFIG_HOOKS_ENV.match(w) for w in words[1:]):
        return True
    stripped = strip_prefix(words)
    prefix = words[:len(words) - len(stripped)]
    prefix_skips = any(HOOK_ENV_OFF.match(w) or GIT_CONFIG_HOOKS_ENV.match(w) for w in prefix)
    if not stripped or program(stripped[0]) in SHELLS or stripped[0] == "eval":
        return prefix_skips
    if program(stripped[0]).lower() != "git":
        return False
    sub, args, configs = git_subcommand(stripped)
    reads = [a for a in args if a not in CONFIG_SCOPE_OPTS]
    if sub == "config" and reads and reads[0] not in CONFIG_READS and any(HOOKS_PATH_CONFIG.match(a) for a in args):
        return True
    if sub not in HOOK_SUBCOMMANDS:
        return False
    if any(HOOKS_PATH_CONFIG.match(c) for c in configs):
        return True
    if prefix_skips:
        return True
    for arg in args:
        if arg == "--":
            break
        if arg.startswith(SKIP_FLAG + "=") or (
            arg.startswith("--no-") and len(arg) > 5 and (SKIP_FLAG.startswith(arg) or SIGN_SKIP_FLAG.startswith(arg))
        ):
            return True
        if sub == "commit" and re.match(r"^-[A-Za-z]*n[A-Za-z]*$", arg):
            return True
    return False


def api_call(words):
    words = strip_prefix(words)
    if len(words) < 2 or program(words[0]).lower() != "gh" or words[1] != "api":
        return None
    args = words[2:]
    method, writes, endpoint, i = "GET", False, None, 0
    while i < len(args):
        arg = args[i]
        if arg in ("-X", "--method"):
            method = args[i + 1].upper() if i + 1 < len(args) else "?"
            i += 2
            continue
        if arg in API_OPTS_WITH_VALUE:
            i += 2
            continue
        if arg in API_FIELD_FLAGS:
            writes = True
            i += 2
            continue
        if arg.startswith("--method="):
            method = arg.split("=", 1)[1].upper()
        elif arg.startswith("-X"):
            method = arg[2:].upper()
        elif re.match(r"^(-[fF].|--(raw-)?field=|--input=)", arg):
            writes = True
        elif not arg.startswith("-") and endpoint is None:
            endpoint = arg
        i += 1
    return args, method != "GET" or writes, endpoint or ""


def api_merges(words, raw):
    call = api_call(words)
    if call is None:
        return False
    args, writes, endpoint = call
    if not any(MERGE_WORDS.search(a) for a in args):
        return False
    return writes or endpoint.strip("/").endswith(("merge", "merges")) or "graphql" in endpoint


def api_path(endpoint):
    decoded = None
    while decoded != endpoint:
        decoded, endpoint = endpoint, unquote(endpoint)
    return posixpath.normpath(re.sub(r"/+", "/", re.split(r"[?#]", endpoint)[0]))


def api_ref_writes(words, raw):
    call = api_call(words)
    if call is None:
        return False
    args, writes, endpoint = call
    path = api_path(endpoint)
    if writes and PROTECTED_REF.search(path):
        return True
    if path.endswith("graphql") and any(a == "--input" or a.startswith("--input=") or "=@" in a for a in args):
        return True
    return any(REF_MUTATIONS.search(a) for a in args)


def pr_merges(words, raw):
    words = strip_prefix(words)
    return len(words) >= 3 and program(words[0]).lower() == "gh" and words[1] == "pr" and words[2] == "merge"


def gh_auto_flag(words, raw):
    words = strip_prefix(words)
    if len(words) < 2 or program(words[0]).lower() != "gh":
        return False
    return "--auto" in words[1:] and not (len(words) >= 3 and words[1] == "pr" and words[2] == "merge")


def push_destination(refspec):
    target = refspec.split(":", 1)[1] if ":" in refspec else refspec
    target = target.lstrip("+")
    for prefix in ("refs/heads/", "heads/"):
        if target.lower().startswith(prefix):
            target = target[len(prefix):]
    return target


def dangerous_push_flag(arg):
    low = arg.lower()
    if low == "--dry-run":
        return False
    if low.startswith(DANGEROUS_PUSH_PREFIX) or any(low.startswith(flag + "=") for flag in DANGEROUS_PUSH_LONG):
        return True
    if low.startswith("-") and not low.startswith("--") and len(low) > 1:
        return any(ch in low[1:] for ch in ("f", "d"))
    return False


def forbidden_push_guard(cwd):
    state = {"cwd": os.path.realpath(cwd or ".")}

    def check(words, raw):
        words = strip_prefix(words)
        if not words:
            return False
        if words[0] in ("cd", "pushd"):
            destination = os.path.expanduser(words[1]) if len(words) > 1 else os.path.expanduser("~")
            state["cwd"] = os.path.realpath(os.path.join(state["cwd"], destination))
            return False
        if program(words[0]).lower() != "git":
            return False
        sub, args, _ = git_subcommand(words)
        if sub != "push":
            return False
        positionals, i, after_double = [], 0, False
        while i < len(args):
            arg = args[i]
            if not after_double and arg == "--":
                after_double = True
                i += 1
                continue
            if not after_double and arg.startswith("-"):
                if dangerous_push_flag(arg):
                    return FORBIDDEN_PUSH_MSG
                if arg in PUSH_OPTS_WITH_VALUE and i + 1 < len(args):
                    i += 2
                    continue
                i += 1
                continue
            positionals.append(arg)
            i += 1
        refspecs = positionals[1:] if len(positionals) > 1 else []
        for refspec in refspecs:
            if refspec.startswith(("+", ":")):
                return FORBIDDEN_PUSH_MSG
            dest = push_destination(refspec)
            if PROTECTED_BRANCH.match(dest):
                return (
                    f"pushing to {dest} is forbidden; it changes only through a PR. "
                    f"To create a missing one, use gh api repos/<owner>/<repo>/git/refs -f ref=refs/heads/{dest} -f sha=<sha>, "
                    "which GitHub rejects if it exists"
                )
        repo_dir = git_target(words, state["cwd"])
        branch = subprocess.run(["git", "-C", repo_dir, "rev-parse", "--abbrev-ref", "HEAD"],
                                text=True, capture_output=True).stdout.strip()
        if PROTECTED_BRANCH.match(branch):
            return f"pushing while on {branch} is forbidden; it changes only through a PR. Switch to a work branch, then push."
        return False

    return check


def d4_violation(words, raw):
    if any(w.startswith("SKIP_LOCAL_GATE=") for w in words):
        return True
    if words and words[0] == "export" and any(w.startswith("SKIP_LOCAL_GATE") for w in words[1:]):
        return True
    for i, w in enumerate(words):
        if w in (">", ">>") and i + 1 < len(words) and HOOK_PATH.search(words[i + 1]):
            return True
    words = strip_prefix(words)
    if not words:
        return False
    name = program(words[0])
    in_place = name in ("sed", "perl") and any(re.match(r"^-[a-zA-Z]*i", w) for w in words[1:])
    if name in WRITERS or in_place:
        return any(HOOK_PATH.search(w) for w in words[1:])
    return False


def scan(text, check, depth=0):
    if depth > 4:
        raise ParseError("nested too deeply")
    body_text, bodies = split_heredocs(text)
    for words in segments(body_text):
        hit = check(words, body_text)
        if hit:
            return hit
        for token in words:
            for match in SUBSTITUTION.finditer(token):
                hit = scan(match.group(1) or match.group(2), check, depth + 1)
                if hit:
                    return hit
        inner_words = strip_prefix(words)
        if not inner_words:
            continue
        name = program(inner_words[0])
        if name in SHELLS and "-c" in inner_words:
            at = inner_words.index("-c") + 1
            if at < len(inner_words):
                hit = scan(inner_words[at], check, depth + 1)
                if hit:
                    return hit
        if name == "eval":
            hit = scan(" ".join(inner_words[1:]), check, depth + 1)
            if hit:
                return hit
    for header, body in bodies:
        header_words = [program(w) for w in header.replace("<<", " << ").split()]
        if any(w in SHELLS or w == "eval" for w in header_words):
            hit = scan(body, check, depth + 1)
            if hit:
                return hit
    return False


def file_in_install(path, cwd):
    install = live_install()
    directory = os.path.dirname(os.path.realpath(os.path.join(cwd or ".", os.path.expanduser(path))))
    while directory and not os.path.isdir(directory):
        directory = os.path.dirname(directory)
    if install and toplevel(directory) == install:
        return INSTALL_FILE_MESSAGE
    return None


def pr_base_branch(cwd, pr=None, repo=None):
    args = ["gh", "pr", "view"]
    if pr:
        args.append(str(pr))
    if repo:
        args.extend(["-R", str(repo)])
    args.extend(["--json", "baseRefName", "-q", ".baseRefName"])
    try:
        result = subprocess.run(args, cwd=cwd or ".", text=True, capture_output=True, timeout=20)
    except (subprocess.TimeoutExpired, OSError):
        return ""
    return result.stdout.strip() if result.returncode == 0 else ""


def check_mcp_merge(tool_input, cwd):
    if tool_input.get("auto"):
        return "auto-merge is forbidden. Ask Kolin to merge."
    pr = tool_input.get("number")
    repo = tool_input.get("repository")
    base = pr_base_branch(cwd, pr=pr, repo=repo)
    if not base or PROTECTED_BRANCH.match(base):
        return f"merging into {base or 'an unknown base'} needs Kolin; it changes only through a PR that Kolin merges. Ask Kolin to merge."
    if tool_input.get("stack"):
        return "stack merge needs Kolin because it merges every open layer below this PR. Ask Kolin to merge."
    return None


def check_command(cmd, cwd):
    push_check = forbidden_push_guard(cwd)
    install_check = install_guard(cwd)
    parsed_error = False

    def run_check(check_fn):
        nonlocal parsed_error
        try:
            return scan(cmd, check_fn)
        except ParseError:
            parsed_error = True
            return None

    skip = run_check(skips_hooks)
    if skip:
        return "agents do not skip git hooks (--no-verify, commit -n, core.hooksPath). Fix what the hook reports."
    if skip is None and (SKIP_FLAG in cmd or re.search(r"git\s+commit[^;&|]*\s-[a-z]*n", cmd, re.I)):
        return "this command could not be parsed and may skip git hooks. Rewrite it so --no-verify or -n does not appear in the command, for example put a commit message in a file and use -F."

    merging = run_check(pr_merges)
    if merging is None and re.search(r"gh\s+pr\s+merge", cmd, re.I):
        merging = True
    if merging:
        if re.search(r"[;&|`]", cmd):
            return "run gh pr merge as one plain command, with no chained commands."
        pr_match = re.search(r"\s(\d+)(?:\s|$)", cmd)
        repo_match = re.search(r"(?:-R|--repo)[= ](\S+)", cmd)
        if not pr_match:
            return "gh pr merge needs a PR number. Pass it as an argument."
        base = pr_base_branch(cwd, pr=pr_match.group(1), repo=repo_match.group(1) if repo_match else None)
        if not base or PROTECTED_BRANCH.match(base):
            return f"merging into {base or 'an unknown base'} needs Kolin; it changes only through a PR that Kolin merges. Ask Kolin to merge."
    else:
        auto = run_check(gh_auto_flag)
        if auto or (auto is None and re.search(r"--auto(?:\s|$)", cmd, re.I) and re.search(r"gh\s", cmd, re.I)):
            return "auto-merge is forbidden. Ask Kolin to merge."

    api_m = run_check(api_merges)
    if api_m or (api_m is None and MERGE_WORDS.search(cmd) and re.search(r"gh\s+api", cmd, re.I)):
        return "merging via the API is forbidden. Ask Kolin to merge."

    api_r = run_check(api_ref_writes)
    if api_r or (api_r is None and re.search(r"(git/refs/heads/|updateRef|deleteRef)", cmd, re.I) and re.search(r"gh\s+api", cmd, re.I)):
        return "moving or deleting a protected branch via the API is forbidden; it changes only through a PR. Open a PR instead."

    push_hit = run_check(push_check)
    if push_hit:
        return push_hit
    if push_hit is None and re.search(r"git(?:\s+-\S+(?:\s+[^-\s]\S*)?)*\s+push\b", cmd, re.I):
        if re.search(r"(--for|--de|--m|--pru|\s-[^-\s]*[fd]|\s[+:][^\s])", cmd, re.I):
            return FORBIDDEN_PUSH_MSG
        branch_match = re.search(r"(?:^|\s|:|heads/)(main|master|staging|sandbox)(?:\s|\)|$)", cmd, re.I)
        if branch_match:
            return f"pushing to {branch_match.group(1)} is forbidden; it changes only through a PR."

    d4 = run_check(d4_violation)
    if d4 or (d4 is None and "SKIP_LOCAL_GATE=" in cmd):
        return "agents do not skip the local gate or write hook files. Fix what the gate reports."

    install_hit = run_check(install_check)
    if install_hit:
        return install_hit
    return None


def check_payload(raw):
    try:
        payload = json.loads(raw) if raw.strip() else {}
    except ValueError:
        return None
    if not isinstance(payload, dict):
        return None
    tool_call = payload.get("toolCall") if isinstance(payload.get("toolCall"), dict) else {}
    tool_name = str(payload.get("tool_name") or payload.get("toolName") or tool_call.get("name") or "")
    tool_input = payload.get("tool_input") or payload.get("toolInput") or tool_call.get("args") or {}
    if not isinstance(tool_input, dict):
        tool_input = {}
    cwd = str(payload.get("cwd") or ".")

    if tool_name in MCP_MERGE_TOOLS:
        return check_mcp_merge(tool_input, cwd)

    file_path = next(
        (str(tool_input[key]) for key in ("file_path", "Path", "TargetFile", "AbsolutePath", "path") if tool_input.get(key)),
        "",
    )
    if file_path:
        if FILE_HOOK_PATH.search(file_path):
            return "agents do not edit git or harness hook files. Ask Kolin to make the change."
        try:
            return file_in_install(file_path, cwd)
        except OSError:
            return "the install check could not run. Report this to Kolin; do not work around it."

    cmd = str(tool_input.get("command") or tool_input.get("CommandLine") or payload.get("command") or "")
    if not cmd:
        return None
    return check_command(cmd, cwd)


def main():
    mode = sys.argv[1]
    if mode == "payload":
        reason = check_payload(sys.stdin.read())
        if reason:
            print(reason)
            sys.exit(2)
        sys.exit(0)
    if mode == "file-hooks":
        sys.exit(0 if FILE_HOOK_PATH.search(sys.stdin.read()) else 1)
    if mode == "file-install":
        msg = file_in_install(sys.stdin.read().strip(), sys.argv[2])
        if msg:
            print(msg)
            sys.exit(0)
        sys.exit(3)
    checks = {"skip-hooks": skips_hooks, "api-merge": api_merges, "api-ref": api_ref_writes, "pr-merge": pr_merges,
              "d4": d4_violation}
    check = install_guard(sys.argv[2] if len(sys.argv) > 2 else None) if mode == "install" else checks[mode]
    try:
        found = scan(sys.stdin.read(), check)
    except ParseError:
        sys.exit(3)
    if isinstance(found, str):
        print(found)
        sys.exit(0)
    sys.exit(0 if found else 1)


if __name__ == "__main__":
    main()

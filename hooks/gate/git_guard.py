#!/usr/bin/env python3
import re
import shlex
import sys

SKIP_FLAG = "--no-" + "verify"
SEPARATORS = {";", "&&", "||", "|", "&", "|&", "(", ")", "`"}
PREFIX_WORDS = {"env", "sudo", "command", "exec", "time", "nohup", "builtin", "nice", "xargs"}
SHELLS = {"bash", "sh", "zsh", "dash"}
GIT_OPTS_WITH_VALUE = {"-C", "-c", "--git-dir", "--work-tree", "--namespace", "--exec-path"}
HOOK_SUBCOMMANDS = {"commit", "push", "merge", "rebase", "am", "cherry-pick", "revert"}
MERGE_WORDS = re.compile(r"merge|automerge|auto_merge|enablePullRequestAutoMerge", re.I)
HEREDOC = re.compile(r"<<-?\s*(['\"]?)([A-Za-z_][A-Za-z0-9_]*)\1")
API_OPTS_WITH_VALUE = {"-H", "--header", "-q", "--jq", "-t", "--template", "--hostname", "--cache", "-p", "--preview"}
HOOK_DIRS = (r"\.claude/hooks", r"\.git/hooks", r"\.git/config", r"\.githooks", r"\.husky", r"lefthook\.ya?ml")
HOOK_PATH = re.compile("(" + "|".join((r"kolin-skills/hooks",) + HOOK_DIRS) + ")")
FILE_HOOK_PATH = re.compile("(" + "|".join(HOOK_DIRS) + ")", re.I)
HOOKS_PATH_CONFIG = re.compile(r"^(--config-env=)?core\.hookspath(=|$)", re.I)
SUBSTITUTION = re.compile(r"\$\((.*)\)|`([^`]*)`", re.S)
HUSKY_OFF = re.compile(r"^HUSKY=0$")
GIT_CONFIG_HOOKS_ENV = re.compile(r"^GIT_CONFIG_KEY_\d+=core\.hookspath$", re.I)
WRITERS = {"cp", "mv", "rm", "ln", "tee", "chmod", "install", "truncate", "touch", "dd", "rsync"}


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


def lex(line):
    lexer = shlex.shlex(line, posix=True, punctuation_chars=";&|()<>`")
    lexer.whitespace = " \t\r"
    lexer.whitespace_split = True
    lexer.commenters = "#"
    return list(lexer)


def logical_lines(text):
    pending = None
    for line in text.split("\n"):
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
            i += 1
            while i < len(words) and words[i].startswith("-") and words[i] != "--":
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


def skips_hooks(words, raw):
    if words[0] == "export" and any(HUSKY_OFF.match(w) for w in words[1:]):
        return True
    stripped = strip_prefix(words)
    if not stripped or program(stripped[0]) != "git":
        return False
    sub, args, configs = git_subcommand(stripped)
    if sub == "config" and any(HOOKS_PATH_CONFIG.match(a) for a in args):
        return True
    if sub not in HOOK_SUBCOMMANDS:
        return False
    if any(HOOKS_PATH_CONFIG.match(c) for c in configs):
        return True
    prefix = words[:len(words) - len(stripped)]
    if any(HUSKY_OFF.match(w) or GIT_CONFIG_HOOKS_ENV.match(w) for w in prefix):
        return True
    for arg in args:
        if arg == "--":
            break
        if arg == SKIP_FLAG or arg.startswith(SKIP_FLAG + "="):
            return True
        if sub == "commit" and re.match(r"^-[A-Za-z]*n[A-Za-z]*$", arg):
            return True
    return False


def api_merges(words, raw):
    words = strip_prefix(words)
    if len(words) < 2 or program(words[0]) != "gh" or words[1] != "api":
        return False
    args = words[2:]
    if not any(MERGE_WORDS.search(a) for a in args):
        return False
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
        if arg.startswith("--method="):
            method = arg.split("=", 1)[1].upper()
        elif arg.startswith("-X"):
            method = arg[2:].upper()
        elif arg in ("-f", "-F", "--field", "--raw-field", "--input") or re.match(r"^(-[fF].|--(raw-)?field=|--input=)", arg):
            writes = True
        elif not arg.startswith("-") and endpoint is None:
            endpoint = arg
        i += 1
    if method != "GET" or writes:
        return True
    return bool(endpoint and (endpoint.strip("/").endswith(("merge", "merges")) or "graphql" in endpoint))


def pr_merges(words, raw):
    words = strip_prefix(words)
    return len(words) >= 3 and program(words[0]) == "gh" and words[1] == "pr" and words[2] == "merge"


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
        if check(words, body_text):
            return True
        for token in words:
            for match in SUBSTITUTION.finditer(token):
                if scan(match.group(1) or match.group(2), check, depth + 1):
                    return True
        inner_words = strip_prefix(words)
        if not inner_words:
            continue
        name = program(inner_words[0])
        if name in SHELLS and "-c" in inner_words:
            at = inner_words.index("-c") + 1
            if at < len(inner_words) and scan(inner_words[at], check, depth + 1):
                return True
        if name == "eval" and scan(" ".join(inner_words[1:]), check, depth + 1):
            return True
    for header, body in bodies:
        header_words = [program(w) for w in header.replace("<<", " << ").split()]
        if any(w in SHELLS or w == "eval" for w in header_words) and scan(body, check, depth + 1):
            return True
    return False


def main():
    if sys.argv[1] == "file-hooks":
        sys.exit(0 if FILE_HOOK_PATH.search(sys.stdin.read()) else 1)
    checks = {"skip-hooks": skips_hooks, "api-merge": api_merges, "pr-merge": pr_merges, "d4": d4_violation}
    try:
        found = scan(sys.stdin.read(), checks[sys.argv[1]])
    except ParseError:
        sys.exit(3)
    sys.exit(0 if found else 1)


if __name__ == "__main__":
    main()

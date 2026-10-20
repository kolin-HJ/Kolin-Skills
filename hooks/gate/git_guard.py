#!/usr/bin/env python3
"""Find real git / GitHub CLI invocations in a shell command, ignoring text that only mentions them.

Usage: git_guard.py skip-hooks|api-merge|d4   (command text on stdin)
Exit 0 = found a forbidden invocation, 1 = clean, 3 = could not parse (caller falls back, fail closed).
"""
import re
import shlex
import sys

SKIP_FLAG = "--no-" + "verify"
SEPARATORS = {";", "&&", "||", "|", "&", "|&", "(", ")", "\n"}
PREFIX_WORDS = {"env", "sudo", "command", "exec", "time", "nohup", "builtin", "nice", "xargs"}
SHELLS = {"bash", "sh", "zsh", "dash"}
GIT_OPTS_WITH_VALUE = {"-C", "-c", "--git-dir", "--work-tree", "--namespace", "--exec-path"}
HOOK_SUBCOMMANDS = {"commit", "push", "merge", "rebase", "am", "cherry-pick", "revert"}
MERGE_WORDS = re.compile(r"merge|automerge|auto_merge|enablePullRequestAutoMerge", re.I)
HEREDOC = re.compile(r"<<-?\s*(['\"]?)([A-Za-z_][A-Za-z0-9_]*)\1")
API_OPTS_WITH_VALUE = {"-H", "--header", "-q", "--jq", "-t", "--template", "--hostname", "--cache", "-p", "--preview"}
HOOK_PATH = re.compile(r"(\.claude/hooks|kolin-skills/hooks|\.git/hooks|\.husky|lefthook\.ya?ml)")
WRITERS = {"cp", "mv", "rm", "ln", "tee", "chmod", "install", "truncate", "touch", "dd", "rsync"}


class ParseError(Exception):
    pass


def split_heredocs(text):
    """Return the command text without heredoc bodies, plus [(header_line, body)]."""
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


def segments(text):
    """Split into simple commands (lists of words), respecting quotes."""
    text = text.replace("\n", " ; ")  # newlines end commands; inside quotes this only changes the text of one word
    lexer = shlex.shlex(text, posix=True, punctuation_chars=";&|()<>")
    lexer.whitespace = " \t\r"
    lexer.whitespace_split = True
    lexer.commenters = "#"
    try:
        tokens = list(lexer)
    except ValueError as error:
        raise ParseError(str(error))
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
    """Drop VAR=value assignments and wrappers such as env or sudo."""
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
    i = 1
    while i < len(words):
        word = words[i]
        if word in GIT_OPTS_WITH_VALUE:
            i += 2
        elif word.startswith("-"):
            i += 1
        else:
            return word, words[i + 1:]
    return None, []


def skips_hooks(words, raw):
    words = strip_prefix(words)
    if not words or program(words[0]) != "git":
        return False
    sub, args = git_subcommand(words)
    if sub not in HOOK_SUBCOMMANDS:
        return False
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


def d4_violation(words, raw):
    """D4: setting SKIP_LOCAL_GATE, or writing to hook paths."""
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
    checks = {"skip-hooks": skips_hooks, "api-merge": api_merges, "d4": d4_violation}
    try:
        found = scan(sys.stdin.read(), checks[sys.argv[1]])
    except ParseError:
        sys.exit(3)
    sys.exit(0 if found else 1)


if __name__ == "__main__":
    main()

#!/usr/bin/env python3
import argparse
import collections
import re
import subprocess
import sys

TEST = re.compile(r"(\.|/)(test|spec)\.[a-z]+$|/(fixtures|__tests__|tests)/")
NOT_PRODUCT = re.compile(
    r"\.(md|mdx|snap|png|jpg|svg|tla|cfg|mmd)$"
    r"|(^|/)(docs|scripts|\.scratch|\.github|\.agents|\.claude|\.cursor|\.codex)/"
    r"|(^|/)(package\.json|pnpm-lock\.yaml|package-lock\.json|yarn\.lock|bun\.lockb?)$"
)
MIGRATION = re.compile(r"(^|/)migrations?/")
PR_NUMBER = re.compile(r"#(\d+)")
FIX = re.compile(r"^(fix|revert|hotfix)\b", re.I)


def git(*args):
    return subprocess.run(["git", *args], check=True, capture_output=True, text=True).stdout


def numstat(before, after):
    fields = git("diff", "--numstat", "--find-renames", "-z", before, after).split("\0")
    index = 0
    while index < len(fields):
        parts = fields[index].split("\t")
        if len(parts) < 3:
            index += 1
            continue
        renamed = parts[2] == ""
        yield (fields[index + 2] if renamed else parts[2]), (0 if parts[0] == "-" else int(parts[0]))
        index += 3 if renamed else 1


def kind(path):
    if MIGRATION.search(path):
        return "migration"
    if TEST.search(path):
        return "test"
    return "other" if NOT_PRODUCT.search(path) else "product"


def subject_of(commit):
    subject, body = (git("log", "-1", "--format=%s%x00%b", commit).split("\0") + [""])[:2]
    merged = re.match(r"Merge pull request #(\d+)", subject)
    if merged:
        return merged.group(1), next((line for line in body.splitlines() if line.strip()), subject).strip()
    numbers = PR_NUMBER.findall(subject)
    return (numbers[-1] if numbers else commit[:9]), subject.strip()


def product_lines(before, after):
    return sum(added for path, added in numstat(before, after) if kind(path) == "product")


def steps(base, head):
    start = git("merge-base", base, head).strip()
    for line in git("rev-list", "--first-parent", "--reverse", "--parents", f"{start}..{head}").splitlines():
        commit, first_parent = line.split()[:2]
        number, title = subject_of(commit)
        lines = collections.Counter()
        product_files = set()
        for path, added in numstat(first_parent, commit):
            file_kind = kind(path)
            lines[file_kind] += added
            if file_kind == "product":
                product_files.add(path)
        yield {
            "commit": commit,
            "number": number,
            "title": title,
            "lines": lines,
            "files": product_files,
            "ships": product_lines(start, commit),
        }


def with_fix_candidates(rows):
    shipped = set()
    for index, row in enumerate(rows):
        shipped |= row["files"]
        yield row, [other["number"] for other in rows[index + 1:] if FIX.match(other["title"]) and other["files"] & shipped]


def main():
    parser = argparse.ArgumentParser(description="List each step on the head branch's first-parent line since it left the base, with what a release cut after that step would ship and which later fix PRs touch the files it ships.")
    parser.add_argument("base", help="the branch the release merges into, such as origin/main")
    parser.add_argument("head", help="the branch being released, such as origin/staging")
    args = parser.parse_args()
    rows = list(steps(args.base, args.head))
    if not rows:
        sys.exit(f"{args.head} has no commits that {args.base} lacks")
    print("step\tcommit\tpr\tproduct\ttests\tmigrations\tcut_ships\tfix_candidates\ttitle")
    for step, (row, later) in enumerate(with_fix_candidates(rows), start=1):
        lines = row["lines"]
        print(f"{step}\t{row['commit'][:9]}\t{row['number']}\t{lines['product']}\t{lines['test']}\t{lines['migration']}\t{row['ships']}\t{','.join(later) or '-'}\t{row['title'][:70]}")


if __name__ == "__main__":
    main()

#!/usr/bin/env python3
import argparse
import collections
import re
import subprocess
import sys

TEST = re.compile(r"(\.|/)(test|spec)\.[a-z]+$|/(fixtures|__tests__|tests)/")
NOT_PRODUCT = re.compile(r"\.(md|mdx|lock|snap|png|jpg|svg|tla|cfg|mmd)$|(^|/)(docs|\.scratch|\.github|\.agents|\.claude|\.cursor|\.codex)/|(^|/)[^/]*lock[^/]*$")
MIGRATION = re.compile(r"(^|/)migrations?/")
PR_NUMBER = re.compile(r"#(\d+)")
FIX = re.compile(r"^(fix|revert|hotfix)\b", re.I)


def git(*args):
    return subprocess.run(["git", *args], check=True, capture_output=True, text=True).stdout


def numstat(first_parent, commit):
    fields = git("diff", "--numstat", "-z", first_parent, commit).split("\0")
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


def area(path, depth):
    return "/".join(path.split("/")[:depth])


def subject_of(commit):
    subject, body = (git("log", "-1", "--format=%s%x00%b", commit).split("\0") + [""])[:2]
    merged = re.match(r"Merge pull request #(\d+)", subject)
    title = next((line for line in body.splitlines() if line.strip()), subject) if merged else subject
    number = merged.group(1) if merged else (PR_NUMBER.search(subject).group(1) if PR_NUMBER.search(subject) else commit[:9])
    return number, title.strip()


def steps(base, head):
    start = git("merge-base", base, head).strip()
    rows = []
    for line in git("rev-list", "--first-parent", "--reverse", "--parents", f"{start}..{head}").splitlines():
        commit, first_parent = line.split()[:2]
        number, title = subject_of(commit)
        lines = collections.Counter()
        areas = collections.Counter()
        product_files = set()
        for path, added in numstat(first_parent, commit):
            lines[kind(path)] += added
            if kind(path) == "product":
                product_files.add(path)
                areas[path] += added
        rows.append({"commit": commit, "number": number, "title": title, "lines": lines, "areas": areas, "files": product_files})
    return rows


def with_open_fixes(rows):
    shipped = set()
    for index, row in enumerate(rows):
        shipped |= row["files"]
        later = [other["number"] for other in rows[index + 1:] if FIX.match(other["title"]) and other["files"] & shipped]
        yield row, later


def main():
    parser = argparse.ArgumentParser(description="List each step on the head branch's first-parent line since it left the base, with what a release cut after that step would ship and which later fixes it would leave behind.")
    parser.add_argument("base", help="the branch the release merges into, such as origin/main")
    parser.add_argument("head", help="the branch being released, such as origin/staging")
    parser.add_argument("--depth", type=int, default=5, help="path segments that name an area (default 5)")
    args = parser.parse_args()
    rows = steps(args.base, args.head)
    if not rows:
        sys.exit(f"{args.head} has no commits that {args.base} lacks")
    running = 0
    print("step\tcommit\tpr\tproduct\ttests\tmigrations\trunning\tfixes_left\ttop_area\ttitle")
    for step, (row, later) in enumerate(with_open_fixes(rows), start=1):
        running += row["lines"]["product"]
        by_area = collections.Counter()
        for path, added in row["areas"].items():
            by_area[area(path, args.depth)] += added
        top = by_area.most_common(1)[0][0] if by_area else "-"
        left = f"{len(later)}:{','.join(later[:4])}" if later else "0"
        print(f"{step}\t{row['commit'][:9]}\t{row['number']}\t{row['lines']['product']}\t{row['lines']['test']}\t{row['lines']['migration']}\t{running}\t{left}\t{top}\t{row['title'][:70]}")


if __name__ == "__main__":
    main()

#!/usr/bin/env python3
import json
import pathlib
import sys


LIMIT = 10_000
SKILLS = [
    "principle-laziness-protocol",
    "principle-subtract-before-you-add",
    "principle-model-the-domain",
    "principle-boundary-discipline",
    "principle-type-system-discipline",
    "principle-minimize-reader-load",
]


def strip_frontmatter(text):
    if not text.startswith("---\n"):
        return text
    _, _, body = text[4:].partition("\n---\n")
    return body


def main():
    root = pathlib.Path.home() / ".agents/skills"
    sections = []
    for name in SKILLS:
        path = root / name / "SKILL.md"
        if not path.is_file():
            print(f"builder-context: missing {path}. Run `kolin-skills upstream`.", file=sys.stderr)
            return 1
        sections.append(f"# {name}: {path}\n\n{strip_frontmatter(path.read_text()).strip()}")
    context = "\n\n".join(sections)
    if len(context) > LIMIT:
        print(
            f"builder-context: context is {len(context)} characters, over the limit of {LIMIT}. "
            "Claude Code truncates longer SubagentStart context.",
            file=sys.stderr,
        )
        return 1
    print(json.dumps({"hookSpecificOutput": {"hookEventName": "SubagentStart", "additionalContext": context}}))
    return 0


if __name__ == "__main__":
    sys.exit(main())

import os
import pathlib
import re
import subprocess
import unittest

REPO = pathlib.Path(__file__).resolve().parent.parent
ORCH_CLI = re.compile(
    r"scripts/orch|orch\.ts|"
    r"\borch (?:init|unit|ledger|inbox|gate|status|standing|frontier)\b|"
    r"alias orch="
)


class OrchScriptsGoneTests(unittest.TestCase):
    def test_own_skills_do_not_call_the_deleted_orch_cli(self):
        listed = subprocess.run(
            ["git", "-C", str(REPO), "ls-files", "-z", "skills"],
            capture_output=True, check=True,
        )
        hits = []
        for raw in listed.stdout.split(b"\0"):
            if not raw:
                continue
            relative = os.fsdecode(raw)
            path = REPO / relative
            if not path.is_file():
                continue
            for number, line in enumerate(path.read_text().splitlines(), 1):
                if ORCH_CLI.search(line):
                    hits.append(f"{relative}:{number}:{line.strip()}")
        self.maxDiff = None
        self.assertEqual(
            hits, [],
            "pstack 0.15.36 deleted poteto-mode/scripts/orch; write the program store files directly",
        )


if __name__ == "__main__":
    unittest.main()

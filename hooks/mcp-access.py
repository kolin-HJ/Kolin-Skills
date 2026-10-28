#!/usr/bin/env python3
import json
import os
import pathlib
import re
import sys


ACCESS_ERROR = re.compile(
    r"do not have permission|not authorized|\b(?:unauthori[sz]ed|forbidden)\b|(?:HTTP|status)\s*40[13]\b",
    re.IGNORECASE,
)
NOTE = (
    "The {server} connector has no access in this Claude account ({account}). "
    "Do not call mcp__{server}__* again this session; use the service's CLI or the repo's scripts, "
    "and tell Kolin which account lacks it."
)


def main() -> int:
    try:
        payload = json.load(sys.stdin)
    except (json.JSONDecodeError, ValueError):
        return 0
    first_line = str(payload.get("error") or "").splitlines()[:1]
    if not ACCESS_ERROR.search("".join(first_line)):
        return 0
    account = os.environ.get("CLAUDE_CONFIG_DIR") or str(pathlib.Path.home() / ".claude")
    server = str(payload.get("tool_name", "")).split("__")[1:2]
    if not server:
        return 0
    note = NOTE.format(server=server[0], account=account)
    print(json.dumps({"hookSpecificOutput": {"hookEventName": "PostToolUseFailure", "additionalContext": note}}))
    return 0


if __name__ == "__main__":
    sys.exit(main())

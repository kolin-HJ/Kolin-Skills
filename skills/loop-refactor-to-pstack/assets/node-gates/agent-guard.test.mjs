import assert from "node:assert/strict";
import { test } from "node:test";

import { decide, decideHookInput } from "./agent-guard.mjs";

const blocked = [
  ["git commit --no-verify -m x", "--no-verify"],
  ["git push --no-verify origin feature/x", "--no-verify"],
  ["git commit -n -m x", "git commit -n"],
  ["git commit -anm x", "git commit -n"],
  ["git config core.hooksPath /dev/null", "core.hooksPath"],
  ["git -c core.hooksPath=/dev/null commit -m x", "core.hooksPath"],
  ["git push origin staging", "push to staging"],
  ["git push origin HEAD:main", "push to main"],
  ["git push -f origin x:staging", "push to staging"],
  ["git push --force-with-lease origin +x:refs/heads/production", "push to production"],
  ["git push origin :old_main", "push to old_main"],
  ["git status && git push origin main", "push to main"],
  ["FOO=1 git push origin staging", "push to staging"],
  ['sh -c "git push origin staging"', "push to staging"],
  ["(git push origin main)", "push to main"],
  ["time git push origin main", "push to main"],
  ["nohup git push origin staging", "push to staging"],
];

for (const [command, expected] of blocked) {
  test(`blocks: ${command}`, () => {
    const reason = decide(command);
    assert.ok(reason?.includes(expected), `got ${reason}`);
  });
}

const allowed = [
  "git status",
  "git push origin feature/staging-fix",
  "git push staging feature/x",
  "git push origin HEAD:feature/main",
  "git push -u origin claude/adopt-pstack",
  'git commit -m "no-verify in message"',
  "git commit -m x -- file-n",
  "git config user.name x",
  'git commit -m "core.hooksPath"',
  "echo git push origin staging",
  "pnpm check",
  "git commit -m x -uno",
];

for (const command of allowed) {
  test(`allows: ${command}`, () => {
    assert.equal(decide(command), null);
  });
}

test("a non-Bash tool is not inspected", () => {
  const raw = JSON.stringify({
    tool_name: "Write",
    tool_input: { command: "git push origin staging" },
  });
  assert.equal(decideHookInput(raw), null);
});

test("hook input for a Bash push to staging yields the reason", () => {
  const raw = JSON.stringify({
    tool_name: "Bash",
    tool_input: { command: "git push origin staging" },
  });
  assert.equal(
    decideHookInput(raw),
    "agent-guard: git push to staging is blocked (also with --force). Push a feature branch and open a pull request into staging."
  );
});

test("malformed input is allowed so a parser bug cannot lock the agent out", () => {
  assert.equal(decideHookInput("not json"), null);
  assert.equal(decideHookInput('{"tool_name":"Bash"}'), null);
  assert.equal(decideHookInput('{"tool_name":"Bash","tool_input":{"command":5}}'), null);
});

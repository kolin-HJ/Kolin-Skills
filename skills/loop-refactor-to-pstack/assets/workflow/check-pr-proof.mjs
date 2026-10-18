import { execFileSync } from "node:child_process";
import { readFileSync } from "node:fs";
import { fileURLToPath } from "node:url";

const RUNNABLE_SOURCE = /^(apps\/web\/src|packages\/[^/]+\/src)\/(?!.*\.test\.ts$)/;
const RAN_LINE = /^\s*[-*]\s*Ran:\s*`[^`]+`.*\S/;
const NOT_RUN_LINE = /^\s*[-*]\s*Not run:\s*(.*)$/;
const NOT_RUN_REASON = /\S.*\b(because|since)\b.*\S/i;
const APP_PROOF_COMMAND = /^\s*[-*]\s*Ran:\s*`(pnpm -s verify |node \S*parity-pair\.mjs)[^`]*`/;
const APP_PROOF_SKIP = /^verify\b.*\b(because|since)\b.*\S/i;
const HEADING = /^##\s+(.+?)\s*$/;

function section(body, title) {
  const lines = body.split(/\r?\n/);
  const start = lines.findIndex((line) => HEADING.exec(line)?.[1] === title);
  if (start === -1) return null;
  const rest = lines.slice(start + 1);
  const end = rest.findIndex((line) => HEADING.test(line));
  return end === -1 ? rest : rest.slice(0, end);
}

export function proofProblems({ body, changedFiles }) {
  const lines = section(body, "Verification");
  if (lines === null) return ["the PR body has no ## Verification section"];
  const ran = lines.filter((line) => RAN_LINE.test(line));
  const notRun = lines.flatMap((line) => {
    const match = NOT_RUN_LINE.exec(line);
    return match ? [match[1] ?? ""] : [];
  });
  const problems = [];
  if (ran.length === 0) {
    problems.push("## Verification lists no `- Ran: \\`<command>\\` <result>` line");
  }
  for (const reason of notRun) {
    if (!NOT_RUN_REASON.test(reason)) {
      problems.push(
        `"Not run: ${reason}" names no reason; write "Not run: <check>, because <why>"`
      );
    }
  }
  const touchesApp = changedFiles.some((file) => RUNNABLE_SOURCE.test(file));
  const provedOnApp =
    ran.some((line) => APP_PROOF_COMMAND.test(line)) ||
    notRun.some((reason) => APP_PROOF_SKIP.test(reason));
  if (touchesApp && !provedOnApp) {
    problems.push(
      "the change touches app source but ## Verification has no `pnpm -s verify` or parity-pair run, and no `Not run: verify ..., because ...` line saying why"
    );
  }
  return problems;
}

export function isReleasePr(pullRequest) {
  const head = pullRequest?.head;
  const base = pullRequest?.base;
  return (
    base?.ref === "main" &&
    head?.ref === "staging" &&
    head?.repo?.full_name !== undefined &&
    head.repo.full_name === base?.repo?.full_name
  );
}

function main() {
  if (process.env.GITHUB_EVENT_NAME !== "pull_request") {
    console.log("check-pr-proof: not a pull_request event, nothing to check");
    return;
  }
  const event = JSON.parse(readFileSync(process.env.GITHUB_EVENT_PATH ?? "", "utf8"));
  if (isReleasePr(event.pull_request)) {
    console.log("check-pr-proof: a staging to main release carries the proof of its merged PRs");
    return;
  }
  const base = process.env.BASE_REF ?? "";
  execFileSync("git", [
    "fetch",
    "--no-tags",
    "--depth=1",
    "origin",
    `+refs/heads/${base}:refs/remotes/origin/${base}`,
  ]);
  const changedFiles = execFileSync("git", ["diff", "--name-only", `origin/${base}`, "HEAD"], {
    encoding: "utf8",
  })
    .split("\n")
    .filter(Boolean);
  const problems = proofProblems({ body: event.pull_request?.body ?? "", changedFiles });
  if (problems.length === 0) {
    console.log("check-pr-proof: the PR body states its verification");
    return;
  }
  for (const problem of problems) console.error(`check-pr-proof: ${problem}`);
  console.error(
    "\nState what ran and what did not in ## Verification (see .github/PULL_REQUEST_TEMPLATE.md). An unverified change may merge, but it says so."
  );
  process.exit(1);
}

if (process.argv[1] === fileURLToPath(import.meta.url)) main();

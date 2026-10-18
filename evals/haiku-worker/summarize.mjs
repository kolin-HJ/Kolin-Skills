import { readFileSync } from "node:fs";
import os from "node:os";
import path from "node:path";
import { fileURLToPath } from "node:url";
import { usageOf } from "./usage.mjs";

const HERE = path.dirname(fileURLToPath(import.meta.url));
const [subagentsDir] = process.argv.slice(2);
if (!subagentsDir) {
  console.error("usage: node summarize.mjs <~/.claude/projects/<project>/<session>/subagents>");
  process.exit(2);
}
const dir = subagentsDir.replace(/^~/, os.homedir());
const rows = readFileSync(path.join(HERE, "runs/agents.tsv"), "utf8").trim().split("\n").slice(1).map((l) => l.split("\t"));
const k = (n) => `${Math.round(n / 1000)}K`;
console.log("| Case | Worker | Rounds | Worker tokens | Worker max prompt | Worker $ | Advisor tokens | Advisor $ | Total tokens | Total $ |");
console.log("|---|---|---|---|---|---|---|---|---|---|");
for (const [c, w, rounds, workerId, advisorId] of rows) {
  const wu = usageOf(path.join(dir, `agent-${workerId}.jsonl`));
  const au = usageOf(path.join(dir, `agent-${advisorId}.jsonl`));
  console.log(
    `| ${c} | ${w} | ${rounds} | ${k(wu.total)} | ${k(wu.maxPrompt)} | ${wu.usd.toFixed(3)} | ${k(au.total)} | ${au.usd.toFixed(3)} | ${k(wu.total + au.total)} | ${(wu.usd + au.usd).toFixed(3)} |`
  );
}

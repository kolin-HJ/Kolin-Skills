import { execFileSync } from "node:child_process";
import { fileURLToPath } from "node:url";

const DAY_MS = 24 * 60 * 60 * 1000;
const FOLLOW_UP_TITLE = /^(fix|revert)(\([^)]*\))?!?:|^Revert "/i;
const MIN_SHARED_SHARE = 0.5;
const SHARED_FILES =
  /(^|\/)(AGENTS\.md|pnpm-lock\.yaml|package\.json)$|^docs\/|^\.agents\/|^\.pstack\//;

function ownFiles(pr) {
  return pr.files.filter((file) => !SHARED_FILES.test(file));
}

const REVERTED_TITLE = /^Revert "(.+)"$/;

function shareOfFix(fixFiles, original) {
  if (fixFiles.length === 0) return 0;
  return fixFiles.filter((file) => original.has(file)).length / fixFiles.length;
}

function culprit(fix, earlier, windowDays) {
  const at = Date.parse(fix.mergedAt);
  const inWindow = earlier.filter((pr) => at - Date.parse(pr.mergedAt) <= windowDays * DAY_MS);
  const reverted = REVERTED_TITLE.exec(fix.title)?.[1];
  if (reverted !== undefined) return inWindow.find((pr) => pr.title === reverted) ?? null;
  const fixFiles = ownFiles(fix);
  const ranked = inWindow
    .map((pr) => ({ pr, share: shareOfFix(fixFiles, new Set(ownFiles(pr))) }))
    .filter(({ share }) => share >= MIN_SHARED_SHARE)
    .sort((a, b) => b.share - a.share || b.pr.mergedAt.localeCompare(a.pr.mergedAt));
  return ranked[0]?.pr ?? null;
}

export function followUps(prs, windowDays) {
  const byMerge = [...prs].sort((a, b) => a.mergedAt.localeCompare(b.mergedAt));
  const fixesOf = new Map(byMerge.map((pr) => [pr.number, []]));
  byMerge.forEach((pr, i) => {
    if (!FOLLOW_UP_TITLE.test(pr.title)) return;
    const blamed = culprit(pr, byMerge.slice(0, i), windowDays);
    if (blamed !== null) fixesOf.get(blamed.number)?.push(pr);
  });
  return byMerge.map((pr) => ({
    number: pr.number,
    title: pr.title,
    mergedAt: pr.mergedAt,
    fixes: fixesOf.get(pr.number) ?? [],
  }));
}

function positiveInteger(flag, value) {
  const n = Number(value);
  if (!Number.isInteger(n) || n <= 0) {
    console.error(`trust-curve: ${flag} must be a positive whole number of days, got ${value}`);
    process.exit(2);
  }
  return n;
}

function percent(part, whole) {
  return whole === 0 ? "n/a" : `${Math.round((part / whole) * 100)}%`;
}

function main() {
  const args = new Map(
    process.argv
      .slice(2)
      .flatMap((arg, i, all) => (arg.startsWith("--") ? [[arg, all[i + 1]]] : []))
  );
  const days = positiveInteger("--days", args.get("--days") ?? "30");
  const windowDays = positiveInteger("--window", args.get("--window") ?? "7");
  const base = args.get("--base") ?? "staging";
  const since = new Date(Date.now() - (days + windowDays) * DAY_MS).toISOString().slice(0, 10);
  const raw = execFileSync(
    "gh",
    [
      "pr",
      "list",
      "--base",
      base,
      "--state",
      "merged",
      "--limit",
      "500",
      "--search",
      `merged:>=${since}`,
      "--json",
      "number,title,mergedAt,files",
    ],
    { encoding: "utf8", maxBuffer: 64 * 1024 * 1024 }
  );
  const prs = JSON.parse(raw).map((pr) => ({ ...pr, files: pr.files.map((f) => f.path) }));
  const cutoff = Date.now() - days * DAY_MS;
  const report = followUps(prs, windowDays).filter((row) => Date.parse(row.mergedAt) >= cutoff);
  const settled = report.filter(
    (row) => Date.parse(row.mergedAt) <= Date.now() - windowDays * DAY_MS
  );
  const needed = report.filter((row) => row.fixes.length > 0);
  console.log(`PRs merged into ${base} in the last ${days} days: ${report.length}`);
  console.log(
    `Needed a fix or revert on the same files within ${windowDays} days: ${needed.length} (${percent(needed.length, report.length)})`
  );
  console.log(
    `Of the ${settled.length} whose ${windowDays}-day window has closed: ${settled.filter((r) => r.fixes.length === 0).length} held (${percent(settled.filter((r) => r.fixes.length === 0).length, settled.length)})`
  );
  for (const row of needed) {
    console.log(`\n#${row.number} ${row.title}`);
    for (const fix of row.fixes) console.log(`  followed by #${fix.number} ${fix.title}`);
  }
}

if (process.argv[1] === fileURLToPath(import.meta.url)) main();

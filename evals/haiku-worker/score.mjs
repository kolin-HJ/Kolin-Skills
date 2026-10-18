import { execSync } from "node:child_process";
import { readFileSync, writeFileSync } from "node:fs";
import path from "node:path";
import { fileURLToPath } from "node:url";

const HERE = path.dirname(fileURLToPath(import.meta.url));
const CODE = /\.(ts|tsx|js|mjs|json)$/;

const [runsDir, caseId, worker] = process.argv.slice(2);
if (!runsDir || !caseId || !worker) {
  console.error("usage: node score.mjs <runs dir from prepare.mjs> <case id> <haiku|sonnet>");
  process.exit(2);
}
const c = JSON.parse(readFileSync(path.join(HERE, "cases.json"), "utf8")).find((x) => x.id === caseId);
const dir = path.join(path.resolve(runsDir), `${caseId}-${worker}`);
const sh = (cmd) => {
  try {
    return { ok: true, out: execSync(cmd, { cwd: dir, encoding: "utf8", stdio: "pipe", maxBuffer: 1 << 26 }) };
  } catch (e) {
    return { ok: false, out: `${e.stdout ?? ""}${e.stderr ?? ""}` };
  }
};

function hunks(patch) {
  const out = [];
  let file = null;
  let cur = null;
  for (const line of patch.split("\n")) {
    if (line.startsWith("diff --git ")) {
      file = line.split(" b/").pop();
      cur = null;
    } else if (line.startsWith("@@")) {
      cur = { file, lines: [] };
      out.push(cur);
    } else if (cur && (line.startsWith("+") || line.startsWith("-")) && !line.startsWith("+++") && !line.startsWith("---")) {
      cur.lines.push(`${file}\t${line[0]}${line.slice(1).trim()}`);
    }
  }
  return out;
}
const bag = (hs) => {
  const m = new Map();
  for (const h of hs) for (const l of h.lines) m.set(l, (m.get(l) ?? 0) + 1);
  return m;
};
const lineDiff = (hs, other) => {
  const left = new Map(other);
  return hs.flatMap((h) =>
    h.lines.filter((l) => {
      const n = left.get(l) ?? 0;
      if (n > 0) left.set(l, n - 1);
      return n === 0;
    })
  );
};
const offBy = (hs, other) => {
  const left = new Map(other);
  return hs.filter((h) => {
    let off = false;
    for (const l of h.lines) {
      const n = left.get(l) ?? 0;
      if (n > 0) left.set(l, n - 1);
      else off = true;
    }
    return off;
  });
};

sh("git add -A -N");
const actual = hunks(sh("git diff -M HEAD").out);
const expected = hunks(readFileSync(path.join(HERE, c.expected), "utf8"));
const extra = offBy(actual, bag(expected));
const missing = offBy(expected, bag(actual));
const changed = sh("git diff -M --name-only HEAD").out.split("\n").filter(Boolean);

const gates = c.gates.map((cmd) => ({ cmd, ...sh(cmd) }));
const fmtFiles = changed.filter((f) => CODE.test(f));
if (fmtFiles.length) gates.push({ cmd: "oxfmt --check <changed code files>", ...sh(`node_modules/.bin/oxfmt --check ${fmtFiles.map((f) => JSON.stringify(f)).join(" ")}`) });

const result = {
  case: caseId,
  worker,
  changed,
  hunks: { actual: actual.length, expected: expected.length, extra: extra.length, missing: missing.length },
  extraLines: lineDiff(actual, bag(expected)),
  missingLines: lineDiff(expected, bag(actual)),
  gates: gates.map((g) => ({ cmd: g.cmd, ok: g.ok, tail: g.ok ? "" : g.out.split("\n").slice(-15).join("\n") })),
};
writeFileSync(path.join(path.resolve(runsDir), `${caseId}-${worker}.score.json`), JSON.stringify(result, null, 2));
console.log(JSON.stringify({ ...result.hunks, extraLines: result.extraLines.length, missingLines: result.missingLines.length, gates: result.gates.map((g) => `${g.ok ? "PASS" : "FAIL"} ${g.cmd}`) }));

#!/usr/bin/env node
import { spawn } from "node:child_process";
import { existsSync, mkdirSync, readFileSync, rmSync, writeFileSync } from "node:fs";
import net from "node:net";
import path from "node:path";

import { candidates, featuresToRecheck, headOnlyErrors, merge, verdict } from "./pair-verdict.mjs";

const VERIFY = path.join(import.meta.dirname, "verify.mjs");
const PARITY = path.join(import.meta.dirname, "parity.mjs");
const FEATURE_TIMEOUT_MS = 10 * 60_000;

function usage(message) {
  console.error(`${message}

usage: node parity-pair.mjs --base <checkout> --head <checkout> --out <dir> [--base-legacy] [--only a,b]

Runs this script's own parity recipes against the base and head checkouts'
apps at the same time, one feature at a time on both, so both read the same
upstream data within seconds. Features that differ run again on two freshly
launched apps, and a change counts only when it shows in both passes.`);
  process.exit(2);
}

const args = process.argv.slice(2);
const flag = (name) => {
  const index = args.indexOf(`--${name}`);
  return index === -1 ? undefined : args[index + 1];
};
const base = flag("base") && path.resolve(flag("base"));
const head = flag("head") && path.resolve(flag("head"));
const out = flag("out") && path.resolve(flag("out"));
const baseLegacy = args.includes("--base-legacy");
const only = flag("only")?.split(",");
if (!base || !head || !out) usage("--base, --head and --out are required");
if (base === head) usage("--base and --head are the same checkout");
for (const checkout of [base, head]) {
  if (!existsSync(path.join(checkout, "apps/web/node_modules/.bin/next"))) {
    usage(`${checkout} has no installed apps/web; it is not a checkout this script can launch`);
  }
}
mkdirSync(out, { recursive: true });

function run(script, scriptArgs, root, timeoutMs = FEATURE_TIMEOUT_MS) {
  return new Promise((resolve) => {
    const child = spawn(process.execPath, [script, ...scriptArgs], {
      env: { ...process.env, VERIFY_ROOT: root },
      stdio: ["ignore", "pipe", "pipe"],
    });
    const timer = setTimeout(() => child.kill("SIGKILL"), timeoutMs);
    let stdout = "";
    let stderr = "";
    child.stdout.on("data", (chunk) => (stdout += chunk));
    child.stderr.on("data", (chunk) => (stderr += chunk));
    child.on("close", (code) => {
      clearTimeout(timer);
      resolve({ code, stdout, stderr });
    });
  });
}

function parsed(result, what) {
  try {
    return JSON.parse(result.stdout);
  } catch {
    throw new Error(
      `${what} printed no JSON (exit ${result.code}):\n${result.stderr.slice(-2000)}`
    );
  }
}

function portIsFree(port) {
  return new Promise((resolve) => {
    const server = net.createServer();
    server.once("error", () => resolve(false));
    server.listen(port, () => server.close(() => resolve(true)));
  });
}

async function freePorts(count) {
  const candidates = Array.from({ length: 100 }, (_, offset) => 3100 + offset);
  const free = await Promise.all(candidates.map(portIsFree));
  const ports = candidates.filter((_, index) => free[index]).slice(0, count);
  if (ports.length < count) throw new Error("fewer than two free ports between 3100 and 3199");
  return ports;
}

async function cleanupBoth() {
  await Promise.all([run(VERIFY, ["cleanup"], base), run(VERIFY, ["cleanup"], head)]);
}

async function launchBoth() {
  await cleanupBoth();
  const [basePort, headPort] = await freePorts(2);
  const results = await Promise.all([
    run(VERIFY, ["launch", "--fresh", "--port", String(basePort)], base),
    run(VERIFY, ["launch", "--fresh", "--port", String(headPort)], head),
  ]);
  const doctors = await Promise.all([run(VERIFY, ["doctor"], base), run(VERIFY, ["doctor"], head)]);
  for (const [index, name] of ["base", "head"].entries()) {
    const launched = parsed(results[index], `${name} launch`);
    if (!launched.ok) throw new Error(`${name} launch failed: ${JSON.stringify(launched)}`);
    const doctor = parsed(doctors[index], `${name} doctor`);
    if (!doctor.ok) throw new Error(`${name} doctor failed: ${JSON.stringify(doctor)}`);
  }
}

async function observeInLockstep(label, features) {
  const dir = path.join(out, label);
  mkdirSync(dir, { recursive: true });
  const parts = { base: [], head: [] };
  const logs = { base: [], head: [] };
  const started = Date.now();
  const step = async (feature) => {
    const file = (side) => path.join(dir, `${side}-${feature}.json`);
    const common = ["--only", feature, "--no-doctor"];
    rmSync(file("base"), { force: true });
    rmSync(file("head"), { force: true });
    const [baseRun, headRun] = await Promise.all([
      run(PARITY, [...(baseLegacy ? ["--legacy"] : []), ...common, "--out", file("base")], base),
      run(PARITY, [...common, "--out", file("head")], head),
    ]);
    for (const [side, result] of [
      ["base", baseRun],
      ["head", headRun],
    ]) {
      logs[side].push(`== ${feature}\n${result.stdout}\n${result.stderr}`);
      if (!existsSync(file(side))) {
        throw new Error(
          `${side} parity wrote no observation for ${feature}:\n${result.stderr.slice(-2000)}`
        );
      }
      parts[side].push(JSON.parse(readFileSync(file(side), "utf8")));
    }
  };
  await features.reduce(
    (previous, feature) => previous.then(() => step(feature)),
    Promise.resolve()
  );
  const files = {};
  for (const side of ["base", "head"]) {
    files[side] = path.join(out, `${label}-${side}.json`);
    writeFileSync(files[side], `${JSON.stringify(merge(parts[side]), null, 2)}\n`);
    writeFileSync(path.join(out, `${label}-${side}.log`), logs[side].join("\n"));
  }
  return { files, ms: Date.now() - started };
}

async function compare(label, files) {
  const result = await run(PARITY, ["--observed", files.head, "--against", files.base], head);
  const report = parsed(result, `${label} comparison`);
  writeFileSync(path.join(out, `${label}-cmp.json`), `${JSON.stringify(report, null, 2)}\n`);
  return report;
}

const listed = await run(PARITY, ["--list"], head);
const names = parsed(listed, "parity --list");
const features = only ? names.filter((name) => only.includes(name)) : names;
const unknown = (only ?? []).filter((name) => !names.includes(name));
if (unknown.length || !features.length)
  usage(`no such feature: ${unknown.join(", ") || "(none given)"}`);
const timings = {};
const summary = { base, head, baseLegacy, features: features.length };
const interrupted = (signal) => {
  void cleanupBoth().finally(() => process.exit(130));
  console.error(`${signal}: stopping both apps`);
};
process.once("SIGINT", interrupted);
process.once("SIGTERM", interrupted);
try {
  let started = Date.now();
  await launchBoth();
  timings.launch1 = Date.now() - started;
  const first = await observeInLockstep("pass1", features);
  timings.observe1 = first.ms;
  const firstReport = await compare("pass1", first.files);
  const firstAts = candidates(firstReport);
  summary.commits = {
    base: JSON.parse(readFileSync(first.files.base, "utf8")).head,
    head: JSON.parse(readFileSync(first.files.head, "utf8")).head,
  };
  summary.pass1 = { ok: firstReport.ok, changes: firstAts, errors: firstReport.errors };
  const branchErrors = headOnlyErrors(firstReport, names);

  const worldMoved = [first.files.base, first.files.head].some(
    (file) => JSON.parse(readFileSync(file, "utf8")).worldChanged
  );
  if (firstReport.ok) {
    summary.ok = true;
    summary.changes = [];
  } else if (worldMoved) {
    summary.ok = false;
    summary.verdict = "another process wrote the shared database during the run; rerun";
  } else {
    const recheck = featuresToRecheck(firstReport, names);
    summary.recheck = recheck;
    if (recheck === null) {
      summary.ok = false;
      summary.verdict = "pass 1 failed on something no feature owns; read pass1-cmp.json";
    } else {
      started = Date.now();
      await launchBoth();
      timings.launch2 = Date.now() - started;
      const second = await observeInLockstep("pass2", recheck);
      timings.observe2 = second.ms;
      const secondReport = await compare("pass2", second.files);
      const secondAts = candidates(secondReport);
      const errors = [
        ...secondReport.errors,
        ...(secondReport.against ?? []).flatMap((baseline) => baseline.errors),
      ];
      summary.pass2 = { ok: secondReport.ok, changes: secondAts, errors };
      Object.assign(summary, verdict(firstAts, secondAts));
      summary.errors = [...branchErrors, ...errors];
      summary.ok = summary.changes.length === 0 && summary.errors.length === 0;
    }
  }
} finally {
  await cleanupBoth();
}
summary.timings = timings;
writeFileSync(path.join(out, "summary.json"), `${JSON.stringify(summary, null, 2)}\n`);
console.log(JSON.stringify(summary, null, 2));
process.exit(summary.ok ? 0 : 1);

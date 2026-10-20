import { execFileSync, spawnSync } from "node:child_process";
import { existsSync, readFileSync, writeFileSync } from "node:fs";
import path from "node:path";
import { fileURLToPath } from "node:url";

import { writeJson } from "./lib/write-json.mjs";

const ROOT = path.resolve(path.dirname(fileURLToPath(import.meta.url)), "..");
const AGENTS_FILE = "AGENTS.md";
const BASELINE_PATH = path.join(ROOT, "scripts", "agents-refs-baseline.json");
const SYMBOL_SCOPES = [
  "apps",
  "packages",
  "scripts",
  ".agents/skills/verify-app",
  ":(glob)*.json",
];
const ENV_EXAMPLE_FILES = [".env.local.example"];
const NOT_SOURCE = [
  ":(exclude)scripts/*-baseline.json",
  ":(exclude)package-lock.json",
  ":(exclude,glob)**/*.md",
];
const WHOLE_LINE_COMMENT = /^\s*(?:\/\/|\/\*|\*|#|--)/;
const TRAILING_COMMENT = /(?:^|\s)(?:\/\/|\/\*).*$/;
const SQL_TRAILING_COMMENT = /\s--\s.*$/;
const PATH_EXTENSION =
  /\.(ts|tsx|js|mjs|cjs|json|md|mdc|sql|yml|yaml|sh|toml|py|css|html|txt|tsv|example)$/;
const CAMEL = /^[a-z][a-z0-9]*(?:[A-Z][a-z0-9]*)+$/;
const PASCAL = /^[A-Z][a-z0-9]+(?:[A-Z][a-z0-9]*)+$/;
const SNAKE = /^[a-z][a-z0-9]*(?:_[a-z0-9]+)+$/;
const SCREAMING = /^[A-Z][A-Z0-9]*(?:_[A-Z0-9]+)+$/;
const CALL_OR_ARRAY_SUFFIX = /(?:\(\)|\[\])$/;
const WORD = /^\w+$/;
const BARE_EXTENSION = /^\.[a-z]+$/;
const NOT_A_REFERENCE = /\s|:\/\/|^[/~-]/;
const ENV_ASSIGNMENT = /^([A-Z][A-Z0-9]*(?:_[A-Z0-9]+)+)=\S*$/;
const WORKSPACE_ALIAS = "@/";
const WORKSPACE_ALIAS_TARGET = "apps/web/src/";
const SCOPE_LABEL =
  "the code under apps/, packages/, scripts/, .agents/skills/verify-app/ or the root *.json configs";
const FIX_HINT =
  "rename the reference to the code that owns it now, strike it through as ~~`name`~~ if the sentence says it is gone, or delete the sentence";
const REVIVED_HINT =
  "a struck-through name says the thing is gone, so either remove the thing again or drop the strike";
export const EXTERNAL_NAMES = new Map([
  ["AskQuestion", "a Cursor tool name"],
  ["old_main", "a git branch on the remote"],
  ["outputFileTracingIncludes", "a Next.js config key"],
  [".pstack/lessons.md", "the lessons file pstack creates on its first lesson"],
]);

function listRepoPaths() {
  return execFileSync("git", ["ls-files", "-z", "--cached", "--others", "--exclude-standard"], {
    cwd: ROOT,
    encoding: "utf8",
    maxBuffer: 64 * 1024 * 1024,
  })
    .split("\0")
    .filter((f) => f !== "" && existsSync(path.join(ROOT, f)));
}

function directoryNames(repoPaths) {
  return new Set(repoPaths.flatMap((repoPath) => repoPath.split("/").slice(0, -1)));
}

function declaredPackageNames(repoPaths) {
  const names = new Set();
  for (const file of repoPaths.filter((f) => f === "package.json" || f.endsWith("/package.json"))) {
    const manifest = JSON.parse(readFileSync(path.join(ROOT, file), "utf8"));
    if (typeof manifest.name === "string") names.add(manifest.name);
    for (const field of ["dependencies", "devDependencies", "peerDependencies"]) {
      for (const dep of Object.keys(manifest[field] ?? {})) names.add(dep);
    }
  }
  return names;
}

function struckRanges(line) {
  return [...line.matchAll(/~~(.+?)~~/g)].map((m) => [m.index, m.index + m[0].length]);
}

export function spansWithLines(markdown) {
  const spans = [];
  let fenced = false;
  markdown.split("\n").forEach((line, index) => {
    if (line.trimStart().startsWith("```")) {
      fenced = !fenced;
      return;
    }
    if (fenced) return;
    const struck = struckRanges(line);
    for (const match of line.matchAll(/`([^`]+)`/g)) {
      const removed = struck.some(([from, to]) => match.index > from && match.index < to);
      spans.push({ text: match[1].trim(), line: index + 1, removed });
    }
  });
  return spans;
}

function identifierKind(token) {
  if (SCREAMING.test(token)) return "env-or-constant";
  if (CAMEL.test(token) || PASCAL.test(token) || SNAKE.test(token)) return "identifier";
  return null;
}

function identifierRefs(text) {
  const bare = text.replace(CALL_OR_ARRAY_SUFFIX, "");
  const segments = bare.split(".");
  if (!segments.every((segment) => WORD.test(segment))) return [];
  return segments.flatMap((segment) => {
    const kind = identifierKind(segment);
    return kind === null ? [] : [{ kind, target: segment }];
  });
}

function isPathLike(text) {
  return text.includes("/") || PATH_EXTENSION.test(text);
}

function isAnchored(target, directoryNames) {
  return PATH_EXTENSION.test(target) || directoryNames.has(target.split("/")[0]);
}

function packageSpecifier(text) {
  const parts = text.split("/");
  return text.startsWith("@") ? parts.slice(0, 2).join("/") : parts[0];
}

function classify(text, tree) {
  const assignment = text.match(ENV_ASSIGNMENT);
  if (assignment) return [{ kind: "env-or-constant", target: assignment[1] }];
  if (NOT_A_REFERENCE.test(text)) return [];
  if (!isPathLike(text)) return identifierRefs(text);
  if (BARE_EXTENSION.test(text)) return [];
  if (text.startsWith(WORKSPACE_ALIAS)) {
    return [{ kind: "path", target: WORKSPACE_ALIAS_TARGET + text.slice(WORKSPACE_ALIAS.length) }];
  }
  if (tree.packageNames.has(packageSpecifier(text))) return [];
  const target = text.replace(/^\.\//, "");
  return isAnchored(target, tree.directoryNames) ? [{ kind: "path", target }] : [];
}

function expandBraces(pattern) {
  const match = pattern.match(/\{([^{}]*)\}/);
  if (!match || match.index === undefined) return [pattern];
  const head = pattern.slice(0, match.index);
  const tail = pattern.slice(match.index + match[0].length);
  return match[1].split(",").flatMap((choice) => expandBraces(head + choice + tail));
}

function globSource(pattern) {
  let out = "";
  for (let i = 0; i < pattern.length; i++) {
    const char = pattern[i];
    if (char === "*" && pattern[i + 1] === "*") {
      out += ".*";
      i++;
    } else if (char === "*") {
      out += "[^/]*";
    } else if (char === "<") {
      const close = pattern.indexOf(">", i);
      out += "[^/]+";
      i = close === -1 ? pattern.length : close;
    } else {
      out += char.replace(/[.+?^${}()|[\]\\]/g, "\\$&");
    }
  }
  return out;
}

function pathMatcher(target) {
  const directory = target.endsWith("/");
  const trimmed = target.replace(/\/+$/, "");
  const lastSegment = trimmed.slice(trimmed.lastIndexOf("/") + 1);
  const inferredExtension = lastSegment.includes(".") ? "" : "(?:\\.[A-Za-z0-9]+)?";
  const tail = directory ? "/.*" : `${inferredExtension}(?:/.*)?`;
  return new RegExp(`(?:^|/)${globSource(trimmed)}${tail}$`);
}

function pathExists(target, repoPaths) {
  return expandBraces(target).every((choice) => {
    const matcher = pathMatcher(choice);
    return repoPaths.some((repoPath) => matcher.test(repoPath));
  });
}

function runGit(args, options) {
  const result = spawnSync("git", args, {
    cwd: ROOT,
    encoding: "utf8",
    maxBuffer: 256 * 1024 * 1024,
    ...options,
  });
  if (result.status !== 0 && result.status !== 1) {
    console.error(`git ${args[0]} failed: ${result.stderr}`);
    process.exit(2);
  }
  return result;
}

function ignoredByGit(targets) {
  if (targets.length === 0) return new Set();
  const result = runGit(["check-ignore", "--no-index", "--stdin"], { input: targets.join("\n") });
  return new Set(result.stdout.split("\n").filter((line) => line !== ""));
}

function codePart(file, text) {
  if (ENV_EXAMPLE_FILES.includes(file)) return text;
  if (WHOLE_LINE_COMMENT.test(text)) return "";
  const withoutTrailing = text.replace(TRAILING_COMMENT, "");
  return file.endsWith(".sql")
    ? withoutTrailing.replace(SQL_TRAILING_COMMENT, "")
    : withoutTrailing;
}

function wordsPresent(words, pathspecs) {
  if (words.length === 0) return new Set();
  const wanted = new Set(words);
  const patterns = words.flatMap((word) => ["-e", word]);
  const result = runGit([
    "grep",
    "--untracked",
    "--null",
    "-w",
    "-F",
    ...patterns,
    "--",
    ...pathspecs,
    ...NOT_SOURCE,
  ]);
  const present = new Set();
  for (const line of result.stdout.split("\n")) {
    const separator = line.indexOf("\0");
    if (separator === -1) continue;
    const code = codePart(line.slice(0, separator), line.slice(separator + 1));
    for (const token of code.match(/\w+/g) ?? []) {
      if (wanted.has(token)) present.add(token);
    }
  }
  return present;
}

function scan() {
  const repoPaths = listRepoPaths();
  const tree = {
    packageNames: declaredPackageNames(repoPaths),
    directoryNames: directoryNames(repoPaths),
  };
  const markdown = readFileSync(path.join(ROOT, AGENTS_FILE), "utf8");
  const refs = new Map();
  for (const { text, line, removed } of spansWithLines(markdown)) {
    for (const { kind, target } of classify(text, tree)) {
      const key = `${removed ? "struck " : ""}${kind} ${target}`;
      const ref = refs.get(key) ?? { kind, target, removed, lines: new Set() };
      ref.lines.add(line);
      refs.set(key, ref);
    }
  }
  const all = [...refs.entries()];
  const words = (kind) => all.filter(([, ref]) => ref.kind === kind).map(([, ref]) => ref.target);
  const inSource = wordsPresent(
    [...words("identifier"), ...words("env-or-constant")],
    SYMBOL_SCOPES
  );
  const inEnvExamples = wordsPresent(words("env-or-constant"), ENV_EXAMPLE_FILES);
  const unmatchedPaths = all
    .filter(([, ref]) => ref.kind === "path")
    .filter(([, ref]) => !pathExists(ref.target, repoPaths));
  const ignored = ignoredByGit(unmatchedPaths.map(([, ref]) => ref.target));
  const deadPaths = new Set(
    unmatchedPaths.filter(([, ref]) => !ignored.has(ref.target)).map(([key]) => key)
  );
  const dead = new Map();
  for (const [key, ref] of all) {
    const resolves =
      ref.kind === "path"
        ? !deadPaths.has(key)
        : inSource.has(ref.target) ||
          (ref.kind === "env-or-constant" && inEnvExamples.has(ref.target));
    if (isFinding(ref, resolves)) dead.set(key, ref);
  }
  return dead;
}

export function isFinding(ref, resolves) {
  if (ref.removed) return resolves;
  return !resolves && !EXTERNAL_NAMES.has(ref.target);
}

function readBaseline() {
  if (!existsSync(BASELINE_PATH)) return [];
  return JSON.parse(readFileSync(BASELINE_PATH, "utf8"));
}

function writeBaseline(keys) {
  writeFileSync(BASELINE_PATH, `${JSON.stringify([...keys].sort(), null, 2)}\n`);
}

function describe(ref) {
  const lines = [...ref.lines].sort((a, b) => a - b).join(",");
  if (ref.removed) {
    return `${AGENTS_FILE}:${lines}: struck-through ${ref.kind} \`${ref.target}\` exists in the tree again: ${REVIVED_HINT}`;
  }
  const where =
    ref.kind === "path"
      ? "which matches no path in the working tree outside .gitignore"
      : ref.kind === "env-or-constant"
        ? `which appears nowhere in ${SCOPE_LABEL} or in ${ENV_EXAMPLE_FILES.join(", ")}`
        : `which appears nowhere in ${SCOPE_LABEL}`;
  return `${AGENTS_FILE}:${lines}: ${ref.kind} \`${ref.target}\`, ${where}`;
}

function printNew(fresh, dead) {
  for (const key of fresh) console.error(describe(dead.get(key)));
  console.error(`\n${fresh.length} new dead reference(s) in ${AGENTS_FILE}: ${FIX_HINT}.`);
}

async function main() {
  const mode = process.argv[2] ?? "--check";
  const dead = scan();

  if (mode === "--init") {
    writeBaseline(dead.keys());
    console.log(`agents-refs baseline written from scratch: ${dead.size} dead references`);
    process.exit(0);
  }

  const baseline = readBaseline();
  const allowed = new Set(baseline);
  const fresh = [...dead.keys()].filter((key) => !allowed.has(key)).sort();
  const stale = baseline.filter((key) => !dead.has(key));

  if (mode === "--json") {
    const rows = [...new Set([...dead.keys(), ...baseline])].sort().map((key) => ({
      file: AGENTS_FILE,
      key,
      current: dead.has(key) ? 1 : 0,
      allowed: allowed.has(key) ? 1 : 0,
    }));
    await writeJson({ rows });
    process.exit(0);
  }

  if (mode === "--update") {
    if (fresh.length > 0) {
      printNew(fresh, dead);
      console.error(
        "\nrefusing to update: --update only drops entries, it never adds one. Nothing was written."
      );
      process.exit(1);
    }
    writeBaseline(baseline.filter((key) => dead.has(key)));
    console.log(
      `agents-refs baseline updated: ${stale.length} dropped, ${dead.size} dead references remain`
    );
    process.exit(0);
  }

  if (mode !== "--check") {
    console.error(`unknown mode ${mode}; use --check (default), --json, --update or --init`);
    process.exit(2);
  }

  if (fresh.length > 0) printNew(fresh, dead);
  if (stale.length > 0) {
    for (const key of stale) {
      console.error(`${key}: now resolves or is gone from ${AGENTS_FILE}, baseline still lists it`);
    }
    console.error(
      `\nstale baseline entries: ${stale.length}. Lock in the fix: node scripts/check-agents-refs.mjs --update`
    );
  }
  if (fresh.length > 0 || stale.length > 0) process.exit(1);
  console.log(`every reference in ${AGENTS_FILE} resolves: ${dead.size} baselined`);
}

if (process.argv[1] === fileURLToPath(import.meta.url)) main();

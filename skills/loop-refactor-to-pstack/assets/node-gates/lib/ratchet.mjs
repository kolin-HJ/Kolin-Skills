const LOWERED_SEVERITY = new Set(["off", "warn", "info"]);
const FALLOW_EXEMPTION_KEYS = [
  "entry",
  "dynamicallyLoaded",
  "ignorePatterns",
  "ignoreFindings",
  "ignoreDependencies",
  "ignoreExports",
  "ignoreUnresolvedImports",
];
const STRICT_FLAGS = [
  "strict",
  "noUncheckedIndexedAccess",
  "exactOptionalPropertyTypes",
  "noImplicitAny",
  "strictNullChecks",
  "strictFunctionTypes",
  "strictBindCallApply",
  "strictPropertyInitialization",
  "noImplicitThis",
  "useUnknownInCatchVariables",
  "alwaysStrict",
  "noImplicitReturns",
  "noFallthroughCasesInSwitch",
  "noImplicitOverride",
];
const WORKSPACE_GATE_SCRIPTS = ["lint", "typecheck", "test"];
const PINNED_PACKAGE = /^(effect|@effect\/.+)$/;
const DEPENDENCY_FIELDS = ["dependencies", "devDependencies"];
const GATE_POLICY_GROWTH_LISTS = [
  "effectHookOwners",
  "deliberateCatchOwners",
  "hexColorOwners",
  "throwingGuards",
  "checkedGuards",
];
const OXLINT_LOWERED = new Set(["off", "allow", "warn", 0, 1]);
const BYPASS_LINE =
  /\bif:|continue-on-error|\|\||;\s*(true|:|exit)\b|\bexit 0\b|\bset \+[eo]\b|--no-verify/;
const GATE_COMMAND_LINE = /\b(pnpm|npx|node|turbo)\b/;
const YAML_KEY_LINE = /^(- )?[\w.-]+:(\s|$)/;
const RUN_LINE = /^(- )?run:\s*[^|>\s]/;
const isWorkflowCommand = (line) =>
  RUN_LINE.test(line) || (!YAML_KEY_LINE.test(line) && GATE_COMMAND_LINE.test(line));
const PNPM_SCRIPT_CALL = /^pnpm (?:-s |run |-s run )?([\w:-]+)$/;

function ones(keys) {
  return new Map(keys.map((key) => [key, 1]));
}

export function fallowExemptions(json) {
  const listed = FALLOW_EXEMPTION_KEYS.flatMap((key) =>
    (json[key] ?? []).map((value) => `${key} ${JSON.stringify(value)}`)
  );
  const rules = Object.entries(json.rules ?? {})
    .filter(([, level]) => LOWERED_SEVERITY.has(level))
    .map(([rule, level]) => `rules ${rule}=${level}`);
  const boundaryAllows = (json.boundaries?.rules ?? []).flatMap((rule) =>
    [...(rule.allow ?? []), ...(rule.allowTypeOnly ?? [])].map(
      (zone) => `boundaries.allow ${rule.from}->${zone}`
    )
  );
  return ones([...listed, ...rules, ...boundaryAllows]);
}

function isOxlintLowered(level) {
  return OXLINT_LOWERED.has(Array.isArray(level) ? level[0] : level);
}

function oxlintLowered(scope, levels) {
  return Object.entries(levels ?? {})
    .filter(([, level]) => isOxlintLowered(level))
    .map(([name]) => `${scope} ${name}`);
}

function oxlintEnforcedRules(scope, levels) {
  return Object.entries(levels ?? {})
    .filter(([, level]) => !isOxlintLowered(level))
    .map(([name]) => `${scope} ${name}`);
}

export function oxlintEnforced(json) {
  const overrides = (json.overrides ?? []).flatMap((override) => {
    const scope = `overrides[${override.files.join(",")}]`;
    return [
      ...(override.plugins ?? []).map((plugin) => `${scope}.plugins ${plugin}`),
      ...oxlintEnforcedRules(`${scope}.rules`, override.rules),
    ];
  });
  return new Set([
    ...(json.options?.typeAware === true ? ["options.typeAware"] : []),
    ...(json.plugins ?? []).map((plugin) => `plugins ${plugin}`),
    ...oxlintEnforcedRules("rules", json.rules),
    ...overrides,
  ]);
}

export function oxlintExemptions(json) {
  const overrides = (json.overrides ?? []).flatMap((override) => {
    const scope = `overrides[${override.files.join(",")}]`;
    return [
      ...oxlintLowered(`${scope}.rules`, override.rules),
      ...(override.excludeFiles ?? []).map((glob) => `${scope}.excludeFiles ${glob}`),
    ];
  });
  return ones([
    ...oxlintLowered("categories", json.categories),
    ...oxlintLowered("rules", json.rules),
    ...(json.ignorePatterns ?? []).map((glob) => `ignorePatterns ${glob}`),
    ...overrides,
  ]);
}

function pluginSeverities(options) {
  return (options.plugins ?? []).flatMap((plugin) =>
    Object.entries(plugin.diagnosticSeverity ?? {}).map(([rule, level]) => ({
      key: `plugin ${plugin.name} ${rule}=${level}`,
      level,
    }))
  );
}

function pinnedDependencies(json) {
  return DEPENDENCY_FIELDS.flatMap((field) =>
    Object.entries(json[field] ?? {})
      .filter(([name]) => PINNED_PACKAGE.test(name))
      .map(([name, version]) => `dependency ${name}@${version}`)
  );
}

export function tsconfigEnforced(json) {
  const options = json.compilerOptions ?? {};
  return new Set([
    ...(options.plugins ?? []).map((plugin) => `plugin ${plugin.name}`),
    ...pluginSeverities(options)
      .filter(({ level }) => level === "error")
      .map(({ key }) => key),
    ...(json.extends === undefined ? [] : [`extends ${json.extends}`]),
    ...STRICT_FLAGS.filter((flag) => options[flag] === true).map(
      (flag) => `compilerOptions.${flag}`
    ),
    ...(json.include ?? []).map((glob) => `include ${glob}`),
  ]);
}

export function tsconfigExemptions(json) {
  const options = json.compilerOptions ?? {};
  return ones([
    ...STRICT_FLAGS.filter((flag) => options[flag] === false).map(
      (flag) => `compilerOptions.${flag}=false`
    ),
    ...pluginSeverities(options)
      .filter(({ level }) => level !== "error")
      .map(({ key }) => key),
    ...(json.exclude ?? []).map((glob) => `exclude ${glob}`),
    ...(json.files ?? []).map((file) => `files ${file}`),
  ]);
}

function checkSteps(scripts) {
  return (scripts.check ?? "")
    .split("&&")
    .map((step) => step.trim().match(/^pnpm (\S+)$/)?.[1])
    .filter((name) => name !== undefined);
}

function scriptChain(scripts, name, seen) {
  const command = scripts[name];
  if (command === undefined || seen.has(name)) return [];
  seen.add(name);
  const called = command
    .split("&&")
    .map((part) => part.trim().match(PNPM_SCRIPT_CALL)?.[1])
    .filter((next) => next !== undefined);
  return [
    `script ${name} = ${command}`,
    ...called.flatMap((next) => scriptChain(scripts, next, seen)),
  ];
}

export function rootPackageEnforced(json) {
  const scripts = json.scripts ?? {};
  const seen = new Set();
  return new Set([
    ...checkSteps(scripts).flatMap((name) => [
      `check step ${name}`,
      ...scriptChain(scripts, name, seen),
    ]),
    ...pinnedDependencies(json),
  ]);
}

export function workspacePackageEnforced(json) {
  const scripts = json.scripts ?? {};
  return new Set([
    ...WORKSPACE_GATE_SCRIPTS.filter((name) => scripts[name] !== undefined).map(
      (name) => `script ${name} = ${scripts[name]}`
    ),
    ...pinnedDependencies(json),
  ]);
}

export function oxfmtIgnores(json) {
  return ones((json.ignorePatterns ?? []).map((pattern) => `ignorePatterns ${pattern}`));
}

export function codeLines(text) {
  return text
    .split("\n")
    .map((line) => line.trim())
    .filter((line) => line !== "" && !/^(#|\/\/)/.test(line));
}

export function counted(lines) {
  const out = new Map();
  for (const line of lines) out.set(line, (out.get(line) ?? 0) + 1);
  return out;
}

export function numbered(lines) {
  return new Set(
    [...counted(lines)].flatMap(([line, count]) =>
      Array.from({ length: count }, (_, i) => (i === 0 ? line : `${line} #${i + 1}`))
    )
  );
}

const bypassLines = (lines) => counted(lines.filter((line) => BYPASS_LINE.test(line)));

export function gatePolicyEntries(json) {
  const lists = GATE_POLICY_GROWTH_LISTS.flatMap((list) =>
    (json[list] ?? []).map((value) => `${list} ${value}`)
  );
  const maxFileLines =
    typeof json.maxFileLines === "number" ? [["maxFileLines", json.maxFileLines]] : [];
  return new Map([...ones(lists), ...maxFileLines]);
}

export function gatePolicyEnforced(json) {
  const scopes = Object.entries(json.scopes ?? {}).flatMap(([gate, paths]) =>
    paths.map((entry) => `scopes.${gate} ${entry}`)
  );
  return new Set([
    ...(json.bannedFileNames ?? []).map((name) => `bannedFileNames ${name}`),
    ...scopes,
    ...(typeof json.maxFileLines === "number" ? ["maxFileLines"] : []),
  ]);
}

export function renamed(entries, renames) {
  const out = new Map();
  for (const [key, count] of entries) {
    const next = key.replace(/[^ |:]+/g, (token) => renames.get(token) ?? token);
    out.set(next, (out.get(next) ?? 0) + count);
  }
  return out;
}

export function compareConfig({ file, config, baseText, headText, renames }) {
  const parse = config.parse ?? JSON.parse;
  const headParsed = headText === null ? null : parse(headText);
  const baseParsed = baseText === null ? null : parse(baseText);
  const head =
    headParsed === null || !config.entries ? new Map() : config.entries(headParsed, file);
  const stillEnforced =
    config.enforced && headParsed !== null ? config.enforced(headParsed, file) : new Set();
  const dropped =
    config.enforced && baseParsed !== null
      ? [...config.enforced(baseParsed, file)].filter((key) => !stillEnforced.has(key))
      : [];
  const base =
    baseParsed === null || !config.entries
      ? new Map()
      : renamed(config.entries(baseParsed, file), renames);
  const raised = [...head]
    .filter(() => baseParsed !== null || !config.newFileFree)
    .filter(([key, count]) => count > (base.get(key) ?? 0))
    .map(([key, count]) => ({ key, from: base.get(key) ?? 0, to: count }));
  const sizes = config.entries
    ? { base: base.size, head: head.size }
    : {
        base: baseParsed === null ? 0 : config.enforced(baseParsed, file).size,
        head: stillEnforced.size,
      };
  return { dropped, raised, baseMissing: baseParsed === null, sizes };
}

const outsideAgents = (file) => !file.startsWith(".agents/") && !file.includes("node_modules/");

const exact = (name) => (file) => file === name;

export const CONFIGS = [
  {
    match: exact(".oxlintrc.json"),
    unit: "oxlint exemptions",
    entries: oxlintExemptions,
    enforced: oxlintEnforced,
  },
  { match: exact(".fallowrc.json"), unit: "dead-code exemptions", entries: fallowExemptions },
  {
    match: exact("scripts/library-limits.json"),
    unit: "library-forced lint findings",
    entries: (json) => new Map(json.map((limit) => [`${limit.file} ${limit.rule}`, limit.count])),
  },
  {
    match: exact("scripts/public-entry-points.json"),
    unit: "public entry points",
    entries: (json) => ones(Object.keys(json)),
  },
  {
    match: (file) => /(^|\/)tsconfig[^/]*\.json$/.test(file) && outsideAgents(file),
    unit: "TypeScript strictness settings",
    entries: tsconfigExemptions,
    enforced: tsconfigEnforced,
  },
  { match: exact("package.json"), unit: "root check steps", enforced: rootPackageEnforced },
  {
    match: (file) => /^(apps|packages)\/[^/]+\/package\.json$/.test(file),
    unit: "workspace gate scripts",
    enforced: workspacePackageEnforced,
  },
  { match: exact(".oxfmtrc.json"), unit: "formatter ignore patterns", entries: oxfmtIgnores },
  {
    match: (file) =>
      /^\.github\/workflows\/[^/]+\.ya?ml$/.test(file) ||
      /^\.github\/actions\/.+\/action\.ya?ml$/.test(file),
    unit: "workflow gate commands and bypass lines (if:, continue-on-error, ||, ; true, exit 0, set +e, --no-verify)",
    parse: codeLines,
    enforced: (lines) => numbered(lines.filter(isWorkflowCommand)),
    entries: bypassLines,
  },
  {
    match: exact(".claude/settings.json"),
    unit: "agent hook settings lines",
    parse: codeLines,
    enforced: numbered,
    entries: bypassLines,
    newFileFree: true,
  },
  {
    match: (file) =>
      /(^|\/)vitest\.(config|workspace)\.[cm]?[jt]s$/.test(file) && outsideAgents(file),
    unit: "test runner config lines (any change needs review)",
    parse: codeLines,
    enforced: numbered,
    entries: counted,
  },
  {
    match: (file) =>
      (/^scripts\/(check-[^/]+|lower-baselines|agent-guard)\.mjs$/.test(file) &&
        !file.endsWith(".test.mjs")) ||
      /^scripts\/lib\/[^/]+\.mjs$/.test(file) ||
      file === "scripts/sync-agent-skills.sh" ||
      file === "apps/web/scripts/check-navigation.mjs" ||
      file === ".agents/skills/verify-supply-chain/scripts/check-feature-map.mjs",
    unit: "gate code lines (a changed or removed line needs review)",
    parse: codeLines,
    enforced: numbered,
  },
  {
    match: exact("scripts/gate-policy.json"),
    unit: "gate policy settings",
    entries: gatePolicyEntries,
    enforced: gatePolicyEnforced,
  },
];

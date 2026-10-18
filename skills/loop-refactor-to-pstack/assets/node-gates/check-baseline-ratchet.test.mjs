import assert from "node:assert/strict";
import { test } from "node:test";

import { CONFIGS, compareConfig, renamed } from "./lib/ratchet.mjs";

const NO_RENAMES = new Map();

function configFor(file) {
  const config = CONFIGS.find((candidate) => candidate.match(file));
  assert.ok(config, `no ratchet config matches ${file}`);
  return config;
}

function ratchet(file, baseJson, headJson, renames = NO_RENAMES) {
  const text = (value) => (value === null ? null : JSON.stringify(value));
  const { dropped, raised } = compareConfig({
    file,
    config: configFor(file),
    baseText: text(baseJson),
    headText: text(headJson),
    renames,
  });
  return { dropped, raised };
}

function ratchetLines(file, baseText, headText) {
  const { dropped, raised } = compareConfig({
    file,
    config: configFor(file),
    baseText,
    headText,
    renames: NO_RENAMES,
  });
  return { dropped, raised };
}

const BASE_TSCONFIG = {
  extends: "../../tsconfig.base.json",
  compilerOptions: { strict: true, noUncheckedIndexedAccess: true },
};

test("tsconfig strict turned false is reported as dropped and as a raised exemption", () => {
  const head = {
    ...BASE_TSCONFIG,
    compilerOptions: { strict: false, noUncheckedIndexedAccess: true },
  };
  assert.deepEqual(ratchet("apps/web/tsconfig.json", BASE_TSCONFIG, head), {
    dropped: ["compilerOptions.strict"],
    raised: [{ key: "compilerOptions.strict=false", from: 0, to: 1 }],
  });
});

test("tsconfig strict removed outright is reported as dropped", () => {
  const head = { ...BASE_TSCONFIG, compilerOptions: { noUncheckedIndexedAccess: true } };
  assert.deepEqual(ratchet("packages/calc/tsconfig.json", BASE_TSCONFIG, head), {
    dropped: ["compilerOptions.strict"],
    raised: [],
  });
});

test("tsconfig that stops extending the base config is reported as dropped", () => {
  const head = { compilerOptions: { strict: true, noUncheckedIndexedAccess: true } };
  assert.deepEqual(ratchet("packages/db/tsconfig.json", BASE_TSCONFIG, head), {
    dropped: ["extends ../../tsconfig.base.json"],
    raised: [],
  });
});

test("tsconfig gaining a stricter flag passes", () => {
  const head = {
    ...BASE_TSCONFIG,
    compilerOptions: { strict: true, noUncheckedIndexedAccess: true, noImplicitReturns: true },
  };
  assert.deepEqual(ratchet("apps/web/tsconfig.json", BASE_TSCONFIG, head), {
    dropped: [],
    raised: [],
  });
});

test("tsconfig excluding the source tree is reported as a raised exemption", () => {
  const head = { ...BASE_TSCONFIG, exclude: ["src"] };
  assert.deepEqual(ratchet("packages/db/tsconfig.json", BASE_TSCONFIG, head), {
    dropped: [],
    raised: [{ key: "exclude src", from: 0, to: 1 }],
  });
});

test("tsconfig narrowing its include is reported as dropped", () => {
  const base = { ...BASE_TSCONFIG, include: ["src", "test"] };
  const head = { ...BASE_TSCONFIG, include: ["src"] };
  assert.deepEqual(ratchet("packages/db/tsconfig.json", base, head), {
    dropped: ["include test"],
    raised: [],
  });
});

const EFFECT_PLUGIN = {
  name: "@effect/language-service",
  diagnosticSeverity: { floatingEffect: "error", asyncFunction: "error" },
};
const BASE_EFFECT_TSCONFIG = {
  ...BASE_TSCONFIG,
  compilerOptions: { ...BASE_TSCONFIG.compilerOptions, plugins: [EFFECT_PLUGIN] },
};

function withEffectPlugin(plugins) {
  return { ...BASE_TSCONFIG, compilerOptions: { ...BASE_TSCONFIG.compilerOptions, plugins } };
}

test("tsconfig dropping the Effect language-service plugin is reported as dropped", () => {
  assert.deepEqual(ratchet("apps/web/tsconfig.json", BASE_EFFECT_TSCONFIG, withEffectPlugin([])), {
    dropped: [
      "plugin @effect/language-service",
      "plugin @effect/language-service floatingEffect=error",
      "plugin @effect/language-service asyncFunction=error",
    ],
    raised: [],
  });
});

test("an Effect diagnostic lowered from error is reported as dropped and raised", () => {
  const head = withEffectPlugin([
    { ...EFFECT_PLUGIN, diagnosticSeverity: { floatingEffect: "warning", asyncFunction: "error" } },
  ]);
  assert.deepEqual(ratchet("apps/web/tsconfig.json", BASE_EFFECT_TSCONFIG, head), {
    dropped: ["plugin @effect/language-service floatingEffect=error"],
    raised: [{ key: "plugin @effect/language-service floatingEffect=warning", from: 0, to: 1 }],
  });
});

test("an Effect diagnostic raised to error passes", () => {
  const head = withEffectPlugin([
    {
      ...EFFECT_PLUGIN,
      diagnosticSeverity: { ...EFFECT_PLUGIN.diagnosticSeverity, processEnv: "error" },
    },
  ]);
  assert.deepEqual(ratchet("apps/web/tsconfig.json", BASE_EFFECT_TSCONFIG, head), {
    dropped: [],
    raised: [],
  });
});

const BASE_EFFECT_WORKSPACE = {
  scripts: { test: "vitest run" },
  dependencies: { effect: "4.0.0", zod: "^3.25.0" },
  devDependencies: { "@effect/vitest": "4.0.0" },
};

test("an Effect version bump in a workspace is reported as dropped", () => {
  const head = { ...BASE_EFFECT_WORKSPACE, dependencies: { effect: "4.0.1", zod: "^3.25.0" } };
  assert.deepEqual(ratchet("apps/web/package.json", BASE_EFFECT_WORKSPACE, head), {
    dropped: ["dependency effect@4.0.0"],
    raised: [],
  });
});

test("an Effect version loosened to a range at the root is reported as dropped", () => {
  const base = { scripts: { check: "pnpm test", test: "vitest run" }, devDependencies: { "@effect/language-service": "0.87.3" } };
  const head = { ...base, devDependencies: { "@effect/language-service": "^0.87.3" } };
  assert.deepEqual(ratchet("package.json", base, head), {
    dropped: ["dependency @effect/language-service@0.87.3"],
    raised: [],
  });
});

test("a version change of a package outside Effect passes", () => {
  const head = { ...BASE_EFFECT_WORKSPACE, dependencies: { effect: "4.0.0", zod: "^3.26.0" } };
  assert.deepEqual(ratchet("apps/web/package.json", BASE_EFFECT_WORKSPACE, head), {
    dropped: [],
    raised: [],
  });
});

const BASE_ROOT_PACKAGE = {
  scripts: {
    check: "pnpm lint && pnpm test",
    lint: "oxlint",
    test: "vitest run",
  },
};

test("a step removed from the root check script is reported as dropped with its script", () => {
  const head = { scripts: { check: "pnpm lint", lint: "oxlint", test: "vitest run" } };
  assert.deepEqual(ratchet("package.json", BASE_ROOT_PACKAGE, head), {
    dropped: ["check step test", "script test = vitest run"],
    raised: [],
  });
});

test("a root check step whose command changed is reported as dropped", () => {
  const head = {
    scripts: { check: "pnpm lint && pnpm test", lint: "oxlint --quiet", test: "vitest run" },
  };
  assert.deepEqual(ratchet("package.json", BASE_ROOT_PACKAGE, head), {
    dropped: ["script lint = oxlint"],
    raised: [],
  });
});

test("a script a check step delegates to is enforced through the chain", () => {
  const base = {
    scripts: {
      check: "pnpm lint",
      lint: "pnpm -s lint:a && pnpm run lint:b",
      "lint:a": "oxlint",
      "lint:b": "node nav.mjs",
    },
  };
  const head = {
    scripts: {
      check: "pnpm lint",
      lint: "pnpm -s lint:a && pnpm run lint:b",
      "lint:a": "true",
      "lint:b": "node nav.mjs",
    },
  };
  assert.deepEqual(ratchet("package.json", base, head), {
    dropped: ["script lint:a = oxlint"],
    raised: [],
  });
});

test("a workspace test script that changed is reported as dropped", () => {
  const base = { scripts: { test: "vitest run", typecheck: "tsc --noEmit" } };
  const head = { scripts: { test: "vitest run --passWithNoTests", typecheck: "tsc --noEmit" } };
  assert.deepEqual(ratchet("packages/calc/package.json", base, head), {
    dropped: ["script test = vitest run"],
    raised: [],
  });
});

test("a workspace script outside lint, typecheck and test may change freely", () => {
  const base = { scripts: { test: "vitest run", build: "tsc" } };
  const head = { scripts: { test: "vitest run", build: "tsc -b" } };
  assert.deepEqual(ratchet("apps/web/package.json", base, head), { dropped: [], raised: [] });
});

const CI_BASE = "jobs:\n  check:\n    steps:\n      - run: pnpm check\n";

test("a changed CI line is reported as dropped", () => {
  const head = "jobs:\n  check:\n    steps:\n      - run: pnpm lint\n";
  assert.deepEqual(ratchetLines(".github/workflows/ci.yml", CI_BASE, head), {
    dropped: ["- run: pnpm check"],
    raised: [],
  });
});

test("an added CI line passes", () => {
  const head = `${CI_BASE}      - run: pnpm audit\n`;
  assert.deepEqual(ratchetLines(".github/workflows/ci.yml", CI_BASE, head), {
    dropped: [],
    raised: [],
  });
});

test("a removed comment line in a workflow is not a loosened gate", () => {
  const base = `# why\n${CI_BASE}`;
  assert.deepEqual(ratchetLines(".github/workflows/ci.yml", base, CI_BASE), {
    dropped: [],
    raised: [],
  });
});

test("a step disabled by an added if: false is reported as raised", () => {
  const head = "jobs:\n  check:\n    steps:\n      - if: false\n        run: pnpm check\n";
  assert.deepEqual(ratchetLines(".github/workflows/ci.yml", CI_BASE, head), {
    dropped: ["- run: pnpm check"],
    raised: [{ key: "- if: false", from: 0, to: 1 }],
  });
});

test("an added continue-on-error is reported as raised", () => {
  const head = `${CI_BASE}        continue-on-error: true\n`;
  assert.deepEqual(ratchetLines(".github/workflows/ci.yml", CI_BASE, head), {
    dropped: [],
    raised: [{ key: "continue-on-error: true", from: 0, to: 1 }],
  });
});

test("an || exit 0 added to a gate step is reported as dropped and raised", () => {
  const head = "jobs:\n  check:\n    steps:\n      - run: pnpm check || exit 0\n";
  assert.deepEqual(ratchetLines(".github/workflows/ci.yml", CI_BASE, head), {
    dropped: ["- run: pnpm check"],
    raised: [{ key: "- run: pnpm check || exit 0", from: 0, to: 1 }],
  });
});

test("a gate command removed from a run block is reported as dropped", () => {
  const base =
    "      - run: |\n          git fetch origin staging\n          node scripts/check-baseline-ratchet.mjs origin/staging\n";
  const head = "      - run: |\n          git fetch origin staging\n";
  assert.deepEqual(ratchetLines(".github/workflows/ci.yml", base, head), {
    dropped: ["node scripts/check-baseline-ratchet.mjs origin/staging"],
    raised: [],
  });
});

test("a bare exit 0 added to a run block is reported as raised", () => {
  const base = "      - run: |\n          pnpm check\n";
  const head = "      - run: |\n          exit 0\n          pnpm check\n";
  assert.deepEqual(ratchetLines(".github/workflows/ci.yml", base, head), {
    dropped: [],
    raised: [{ key: "exit 0", from: 0, to: 1 }],
  });
});

test("a bypass line copied onto a second step is reported as raised", () => {
  const base = `${CI_BASE}      - if: false\n        run: pnpm deploy\n`;
  const head = `${CI_BASE.replace("- run: pnpm check", "- if: false\n        run: pnpm check")}      - if: false\n        run: pnpm deploy\n`;
  assert.deepEqual(ratchetLines(".github/workflows/ci.yml", base, head), {
    dropped: ["- run: pnpm check"],
    raised: [{ key: "- if: false", from: 1, to: 2 }],
  });
});

test("one of two identical gate steps removed is reported as dropped", () => {
  const base = `${CI_BASE}  lint:\n    steps:\n      - run: pnpm check\n`;
  const head = `${CI_BASE}  lint:\n    steps:\n      - run: echo hi\n`;
  assert.deepEqual(ratchetLines(".github/workflows/ci.yml", base, head), {
    dropped: ["- run: pnpm check #2"],
    raised: [],
  });
});

test("an ordinary workflow edit that keeps every gate command passes", () => {
  const base = `${CI_BASE}      - uses: pnpm/action-setup@v4\n        with:\n          node-version: 20\n          cache: pnpm\n      - name: pnpm check\n`;
  const head = `${CI_BASE}      - uses: pnpm/action-setup@v5\n        with:\n          node-version: 22\n          cache: npm\n      - name: every gate\n`;
  assert.deepEqual(ratchetLines(".github/workflows/ci.yml", base, head), {
    dropped: [],
    raised: [],
  });
});

test("a new .yaml workflow that skips its steps is reported as raised", () => {
  assert.deepEqual(
    ratchetLines(".github/workflows/extra.yaml", null, "- run: pnpm check || true\n"),
    {
      dropped: [],
      raised: [{ key: "- run: pnpm check || true", from: 0, to: 1 }],
    }
  );
});

test("a vitest config added to a package is reported as raised, line by line", () => {
  const head = 'export default { test: { include: ["src/none/**"] } };\n';
  assert.deepEqual(ratchetLines("packages/calc/vitest.config.ts", null, head), {
    dropped: [],
    raised: [{ key: 'export default { test: { include: ["src/none/**"] } };', from: 0, to: 1 }],
  });
});

test("an element added to a multi-line vitest exclude is reported as raised", () => {
  const base = 'exclude: [\n"a/**",\n],\n';
  const head = 'exclude: [\n"a/**",\n"src/big/**",\n],\n';
  assert.deepEqual(ratchetLines("apps/web/vitest.config.ts", base, head), {
    dropped: [],
    raised: [{ key: '"src/big/**",', from: 0, to: 1 }],
  });
});

test("agent hook settings deleted at head are reported as dropped", () => {
  assert.deepEqual(ratchetLines(".claude/settings.json", '{"hooks":1}\n', null), {
    dropped: ['{"hooks":1}'],
    raised: [],
  });
});

test("agent hook settings missing at the base pass, their bypass lines included", () => {
  assert.deepEqual(ratchetLines(".claude/settings.json", null, '{"a": "x || y"}\n'), {
    dropped: [],
    raised: [],
  });
});

test("a changed line in gate code is reported as dropped and an added line passes", () => {
  const base = "export function count() {\n  return hits;\n}\n";
  const head = "export function count() {\n  const n = 1;\n  return 0;\n}\n";
  assert.deepEqual(ratchetLines("scripts/lib/paved-rules.mjs", base, head), {
    dropped: ["return hits;"],
    raised: [],
  });
});

const BASE_POLICY = {
  effectHookOwners: ["apps/web/src/lib/use-interval.ts"],
  deliberateCatchOwners: [],
  hexColorOwners: [],
  throwingGuards: ["requireUser"],
  checkedGuards: ["getAppUser"],
  bannedFileNames: ["errors-badge.tsx"],
  maxFileLines: 1000,
  scopes: { comments: ["apps", "packages"], guards: ["apps"] },
};

test("gate policy: an owner added is reported as raised", () => {
  const head = {
    ...BASE_POLICY,
    effectHookOwners: ["apps/web/src/lib/use-interval.ts", "apps/web/src/lib/use-poll.ts"],
  };
  assert.deepEqual(ratchet("scripts/gate-policy.json", BASE_POLICY, head), {
    dropped: [],
    raised: [{ key: "effectHookOwners apps/web/src/lib/use-poll.ts", from: 0, to: 1 }],
  });
});

test("gate policy: an owner removed passes", () => {
  const head = { ...BASE_POLICY, effectHookOwners: [] };
  assert.deepEqual(ratchet("scripts/gate-policy.json", BASE_POLICY, head), {
    dropped: [],
    raised: [],
  });
});

test("gate policy: a guard added to the throwing list is reported as raised", () => {
  const head = { ...BASE_POLICY, throwingGuards: ["requireUser", "requireAdmin"] };
  assert.deepEqual(ratchet("scripts/gate-policy.json", BASE_POLICY, head), {
    dropped: [],
    raised: [{ key: "throwingGuards requireAdmin", from: 0, to: 1 }],
  });
});

test("gate policy: a scope path removed is reported as dropped", () => {
  const head = { ...BASE_POLICY, scopes: { comments: ["apps"], guards: ["apps"] } };
  assert.deepEqual(ratchet("scripts/gate-policy.json", BASE_POLICY, head), {
    dropped: ["scopes.comments packages"],
    raised: [],
  });
});

test("gate policy: a banned file name removed is reported as dropped", () => {
  const head = { ...BASE_POLICY, bannedFileNames: [] };
  assert.deepEqual(ratchet("scripts/gate-policy.json", BASE_POLICY, head), {
    dropped: ["bannedFileNames errors-badge.tsx"],
    raised: [],
  });
});

test("gate policy: maxFileLines raised is reported as raised", () => {
  const head = { ...BASE_POLICY, maxFileLines: 1200 };
  assert.deepEqual(ratchet("scripts/gate-policy.json", BASE_POLICY, head), {
    dropped: [],
    raised: [{ key: "maxFileLines", from: 1000, to: 1200 }],
  });
});

test("gate policy: maxFileLines lowered passes", () => {
  const head = { ...BASE_POLICY, maxFileLines: 800 };
  assert.deepEqual(ratchet("scripts/gate-policy.json", BASE_POLICY, head), {
    dropped: [],
    raised: [],
  });
});

test("gate policy: maxFileLines deleted is reported as dropped", () => {
  const { maxFileLines, ...head } = BASE_POLICY;
  assert.equal(maxFileLines, 1000);
  assert.deepEqual(ratchet("scripts/gate-policy.json", BASE_POLICY, head), {
    dropped: ["maxFileLines"],
    raised: [],
  });
});

test("oxlint: a rule turned off is reported as dropped and as a raised exemption", () => {
  const base = { rules: { "no-debugger": "error" } };
  const head = { rules: { "no-debugger": "off" } };
  assert.deepEqual(ratchet(".oxlintrc.json", base, head), {
    dropped: ["rules no-debugger"],
    raised: [{ key: "rules no-debugger", from: 0, to: 1 }],
  });
});

test("oxlint: a rule lowered to a numeric 0 inside an array is still lowered", () => {
  const base = { rules: { "no-debugger": ["error"] } };
  const head = { rules: { "no-debugger": [0] } };
  assert.deepEqual(ratchet(".oxlintrc.json", base, head), {
    dropped: ["rules no-debugger"],
    raised: [{ key: "rules no-debugger", from: 0, to: 1 }],
  });
});

test("oxfmt: an ignore pattern added is reported as raised", () => {
  const base = { ignorePatterns: ["**/.next/**"] };
  const head = { ignorePatterns: ["**/.next/**", "apps/**"] };
  assert.deepEqual(ratchet(".oxfmtrc.json", base, head), {
    dropped: [],
    raised: [{ key: "ignorePatterns apps/**", from: 0, to: 1 }],
  });
});

test("an existing exemption carried through a file rename is not new", () => {
  const renames = new Map([["old/limits.ts", "new/limits.ts"]]);
  const base = [{ file: "old/limits.ts", rule: "no-any", count: 2 }];
  const head = [{ file: "new/limits.ts", rule: "no-any", count: 2 }];
  assert.deepEqual(ratchet("scripts/library-limits.json", base, head, renames), {
    dropped: [],
    raised: [],
  });
});

test("an exemption count that rises after a rename is reported against the renamed key", () => {
  const renames = new Map([["old/limits.ts", "new/limits.ts"]]);
  const base = [{ file: "old/limits.ts", rule: "no-any", count: 2 }];
  const head = [{ file: "new/limits.ts", rule: "no-any", count: 3 }];
  assert.deepEqual(ratchet("scripts/library-limits.json", base, head, renames), {
    dropped: [],
    raised: [{ key: "new/limits.ts no-any", from: 2, to: 3 }],
  });
});

test("renamed rewrites each path token and sums entries that collide", () => {
  const renames = new Map([
    ["a.ts", "c.ts"],
    ["b.ts", "c.ts"],
  ]);
  const out = renamed(
    new Map([
      ["a.ts rule", 1],
      ["b.ts rule", 2],
    ]),
    renames
  );
  assert.deepEqual([...out], [["c.ts rule", 3]]);
});

test("fallow: an added entry exemption is reported as raised", () => {
  const base = { entry: ["src/a.ts"] };
  const head = { entry: ["src/a.ts", "src/b.ts"] };
  assert.deepEqual(ratchet(".fallowrc.json", base, head), {
    dropped: [],
    raised: [{ key: 'entry "src/b.ts"', from: 0, to: 1 }],
  });
});

test("fallow: a rule turned off is reported as a raised exemption", () => {
  const base = { rules: { "unused-files": "error" } };
  const head = { rules: { "unused-files": "off" } };
  assert.deepEqual(ratchet(".fallowrc.json", base, head), {
    dropped: [],
    raised: [{ key: "rules unused-files=off", from: 0, to: 1 }],
  });
});

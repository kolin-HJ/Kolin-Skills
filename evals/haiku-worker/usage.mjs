import { readFileSync } from "node:fs";

const PRICE = {
  "claude-opus-5-5": { input: 4, output: 20, cacheRead: 0.2 },
  "claude-sonnet-5-5": { input: 2, output: 10, cacheRead: 0.2 },
  "claude-haiku-5-5": { input: 0.1, output: 0.5, cacheRead: 0.01 },
  "claude-haiku-5-5>100k": { input: 0.5, output: 2.5, cacheRead: 0.05 },
};
const HAIKU_TIER_LIMIT = 100_000;

function priceFor(model, prompt) {
  if (model === "claude-haiku-5-5" && prompt > HAIKU_TIER_LIMIT) return PRICE["claude-haiku-5-5>100k"];
  const p = PRICE[model];
  if (!p) throw new Error(`no price for model ${model}`);
  return p;
}

export function usageOf(file) {
  const byId = new Map();
  for (const line of readFileSync(file, "utf8").split("\n")) {
    if (!line) continue;
    const m = JSON.parse(line).message;
    if (m?.usage && m.id && m.model !== "<synthetic>") byId.set(m.id, m);
  }
  const t = { model: null, requests: 0, input: 0, cacheWrite5m: 0, cacheWrite1h: 0, cacheRead: 0, output: 0, maxPrompt: 0, usd: 0 };
  for (const m of byId.values()) {
    const u = m.usage;
    const w1h = u.cache_creation?.ephemeral_1h_input_tokens ?? 0;
    const w5m = (u.cache_creation_input_tokens ?? 0) - w1h;
    const prompt = u.input_tokens + (u.cache_read_input_tokens ?? 0) + (u.cache_creation_input_tokens ?? 0);
    const p = priceFor(m.model, prompt);
    t.model = m.model;
    t.requests += 1;
    t.input += u.input_tokens;
    t.cacheWrite5m += w5m;
    t.cacheWrite1h += w1h;
    t.cacheRead += u.cache_read_input_tokens ?? 0;
    t.output += u.output_tokens;
    t.maxPrompt = Math.max(t.maxPrompt, prompt);
    t.usd +=
      (u.input_tokens * p.input + w5m * p.input * 1.25 + w1h * p.input * 2 + (u.cache_read_input_tokens ?? 0) * p.cacheRead + u.output_tokens * p.output) /
      1e6;
  }
  t.total = t.input + t.cacheWrite5m + t.cacheWrite1h + t.cacheRead + t.output;
  return t;
}

if (import.meta.url === `file://${process.argv[1]}`) {
  for (const f of process.argv.slice(2)) console.log(JSON.stringify({ file: f.split("/").pop(), ...usageOf(f) }));
}

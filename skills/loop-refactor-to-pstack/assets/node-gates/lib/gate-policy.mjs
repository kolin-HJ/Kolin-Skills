import { readFileSync } from "node:fs";

export const GATE_POLICY = JSON.parse(
  readFileSync(new URL("../gate-policy.json", import.meta.url), "utf8")
);

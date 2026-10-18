import { readFileSync } from "node:fs";

const [file] = process.argv.slice(2);
let last = null;
for (const line of readFileSync(file, "utf8").split("\n")) {
  if (!line) continue;
  const content = JSON.parse(line).message?.content;
  if (!Array.isArray(content)) continue;
  for (const b of content) {
    if (b.type === "tool_use" && typeof b.input?.message === "string") last = b.input.message;
    if (b.type === "text" && b.text.trim()) last = b.text;
  }
}
console.log(last ?? "(no report found)");

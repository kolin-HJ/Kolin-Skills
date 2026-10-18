import { fileURLToPath } from "node:url";

export const PROTECTED_BRANCHES = ["staging", "main", "production", "old_main"];
const SEPARATORS = new Set([";", "&", "|", "\n", "(", ")"]);
const SHELLS = new Set(["sh", "bash", "zsh"]);
const ENV_ASSIGNMENT = /^[A-Za-z_][A-Za-z0-9_]*=/;
const PREFIX_COMMANDS = new Set(["env", "time", "nohup", "command", "sudo"]);
const SKIP_VERIFY_CLUSTER = /^-[asqve]*n[asqve]*m?$/;

export function splitCommands(command) {
  const commands = [];
  let tokens = [];
  let word = "";
  let inWord = false;
  let quote = "";
  const endWord = () => {
    if (inWord) tokens.push(word);
    word = "";
    inWord = false;
  };
  const endCommand = () => {
    endWord();
    if (tokens.length > 0) commands.push(tokens);
    tokens = [];
  };
  for (let i = 0; i < command.length; i++) {
    const char = command[i];
    if (quote === "'") {
      if (char === "'") quote = "";
      else word += char;
    } else if (quote === '"') {
      if (char === '"') quote = "";
      else if (char === "\\" && i + 1 < command.length) word += command[++i];
      else word += char;
    } else if (char === "'" || char === '"') {
      quote = char;
      inWord = true;
    } else if (char === "\\" && i + 1 < command.length) {
      word += command[++i];
      inWord = true;
    } else if (SEPARATORS.has(char)) endCommand();
    else if (/\s/.test(char)) endWord();
    else {
      word += char;
      inWord = true;
    }
  }
  endCommand();
  return commands;
}

function pushTarget(refspec) {
  const destination = refspec.slice(refspec.lastIndexOf(":") + 1).replace(/^\+/, "");
  return destination.replace(/^refs\/heads\//, "");
}

function checkPush(args) {
  const positional = args.filter((arg) => !arg.startsWith("-"));
  const protectedTarget = positional
    .slice(1)
    .map(pushTarget)
    .find((target) => PROTECTED_BRANCHES.includes(target));
  if (protectedTarget === undefined) return null;
  return `agent-guard: git push to ${protectedTarget} is blocked (also with --force). Push a feature branch and open a pull request into staging.`;
}

function checkGit(tokens) {
  let i = 1;
  while (i < tokens.length && tokens[i].startsWith("-")) {
    const option = tokens[i];
    if ((option === "-c" || option === "-C") && i + 1 < tokens.length) {
      if (option === "-c" && tokens[i + 1].toLowerCase().startsWith("core.hookspath")) {
        return "agent-guard: setting core.hooksPath is blocked. The repo's configured hooks stay in place.";
      }
      i += 2;
    } else i += 1;
  }
  const subcommand = tokens[i];
  const args = tokens.slice(i + 1);
  if (tokens.includes("--no-verify")) {
    return "agent-guard: --no-verify is blocked. Fix what the checks report, then run the command without it.";
  }
  if (subcommand === "commit") {
    const dashDash = args.indexOf("--");
    const flags = dashDash === -1 ? args : args.slice(0, dashDash);
    if (flags.some((arg) => SKIP_VERIFY_CLUSTER.test(arg))) {
      return "agent-guard: git commit -n skips verification and is blocked. Fix what the checks report, then commit without it.";
    }
  }
  if (subcommand === "config" && args.some((arg) => arg.toLowerCase() === "core.hookspath")) {
    return "agent-guard: setting core.hooksPath is blocked. The repo's configured hooks stay in place.";
  }
  if (subcommand === "push") return checkPush(args);
  return null;
}

function checkTokens(tokens) {
  let rest = tokens;
  while (rest.length > 0 && (ENV_ASSIGNMENT.test(rest[0]) || PREFIX_COMMANDS.has(rest[0]))) {
    rest = rest.slice(1);
  }
  if (rest[0] === "git") return checkGit(rest);
  if (SHELLS.has(rest[0])) {
    const flag = rest.indexOf("-c");
    if (flag !== -1 && flag + 1 < rest.length) return decide(rest[flag + 1]);
  }
  return null;
}

export function decide(command) {
  for (const tokens of splitCommands(command)) {
    const reason = checkTokens(tokens);
    if (reason !== null) return reason;
  }
  return null;
}

export function decideHookInput(raw) {
  let input;
  try {
    input = JSON.parse(raw);
  } catch {
    return null;
  }
  if (input?.tool_name !== "Bash") return null;
  const command = input.tool_input?.command;
  return typeof command === "string" ? decide(command) : null;
}

async function main() {
  const chunks = [];
  for await (const chunk of process.stdin) chunks.push(chunk);
  const reason = decideHookInput(Buffer.concat(chunks).toString("utf8"));
  if (reason === null) process.exit(0);
  console.error(reason);
  process.exit(2);
}

if (process.argv[1] === fileURLToPath(import.meta.url)) await main();

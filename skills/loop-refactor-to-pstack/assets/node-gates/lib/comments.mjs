import { createRequire } from "node:module";

const require = createRequire(import.meta.url);
const ts = require("typescript");

function isJsDocNode(node) {
  return node.kind >= ts.SyntaxKind.FirstJSDocNode && node.kind <= ts.SyntaxKind.LastJSDocNode;
}

export function commentRanges(sourceFile) {
  const text = sourceFile.text;
  const byPos = new Map();
  const visit = (node) => {
    if (node.kind === ts.SyntaxKind.JsxText || isJsDocNode(node)) return;
    if (node.kind > ts.SyntaxKind.LastToken) {
      for (const child of node.getChildren(sourceFile)) visit(child);
      return;
    }
    const trivia = [
      ...(ts.getTrailingCommentRanges(text, node.pos) ?? []),
      ...(ts.getLeadingCommentRanges(text, node.pos) ?? []),
    ];
    for (const range of trivia) byPos.set(range.pos, range);
  };
  visit(sourceFile);
  return [...byPos.values()].sort((a, b) => a.pos - b.pos);
}

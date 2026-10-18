import { createRequire } from "node:module";

const require = createRequire(import.meta.url);
export const ts = require("typescript");

export function calleeName(call) {
  const callee = call.expression;
  if (ts.isIdentifier(callee)) return callee.text;
  if (ts.isPropertyAccessExpression(callee)) return callee.name.text;
  return null;
}

export function calleeIdentifier(call) {
  return ts.isIdentifier(call.expression) ? call.expression.text : null;
}

export function propertyName(property) {
  const name = property.name;
  if (name === undefined) return null;
  if (ts.isIdentifier(name) || ts.isStringLiteralLike(name)) return name.text;
  return null;
}

export function handlerValue(node) {
  if (ts.isPropertyAssignment(node)) return node.initializer;
  if (ts.isShorthandPropertyAssignment(node)) return node.name;
  if (ts.isMethodDeclaration(node)) return node;
  if (ts.isJsxAttribute(node) && node.initializer && ts.isJsxExpression(node.initializer)) {
    return node.initializer.expression ?? null;
  }
  return null;
}

export function containsCall(root, matches) {
  let count = 0;
  const visit = (node) => {
    if (ts.isCallExpression(node) && matches(node)) count += 1;
    ts.forEachChild(node, visit);
  };
  visit(root);
  return count;
}

export function unwrap(node) {
  const isWrapper =
    ts.isParenthesizedExpression(node) ||
    ts.isAsExpression(node) ||
    ts.isSatisfiesExpression(node) ||
    ts.isNonNullExpression(node);
  return isWrapper ? unwrap(node.expression) : node;
}

export function localInitializers(sourceFile) {
  const byName = new Map();
  const visit = (node) => {
    if (ts.isVariableDeclaration(node) && ts.isIdentifier(node.name) && node.initializer) {
      byName.set(node.name.text, node.initializer);
    }
    if (ts.isFunctionDeclaration(node) && node.name && node.body) byName.set(node.name.text, node);
    ts.forEachChild(node, visit);
  };
  visit(sourceFile);
  return byName;
}

function returnedExpression(fn) {
  if (fn.body === undefined) return undefined;
  if (!ts.isBlock(fn.body)) return fn.body;
  const last = fn.body.statements.at(-1);
  return last && ts.isReturnStatement(last) ? last.expression : undefined;
}

export function objectFields(expression, locals, seen = new Set()) {
  const node = unwrap(expression);
  if (ts.isIdentifier(node)) {
    const initializer = locals.get(node.text);
    if (initializer === undefined || seen.has(node.text)) return null;
    return objectFields(initializer, locals, new Set([...seen, node.text]));
  }
  if (ts.isCallExpression(node) && calleeIdentifier(node) === "useMemo") {
    const factory = node.arguments[0];
    const value = factory && ts.isArrowFunction(factory) ? returnedExpression(factory) : undefined;
    return value === undefined ? null : objectFields(value, locals, seen);
  }
  const callee = ts.isCallExpression(node) ? calleeIdentifier(node) : null;
  if (callee !== null) {
    const fn = locals.get(callee);
    if (fn === undefined || !ts.isFunctionLike(fn) || seen.has(callee)) return null;
    const value = returnedExpression(fn);
    return value === undefined ? null : objectFields(value, locals, new Set([...seen, callee]));
  }
  if (!ts.isObjectLiteralExpression(node)) return null;
  const fields = new Map();
  for (const property of node.properties) {
    if (ts.isSpreadAssignment(property)) {
      const spread = objectFields(property.expression, locals, seen);
      if (spread === null) return null;
      for (const [name, value] of spread) fields.set(name, value);
      continue;
    }
    const name = propertyName(property);
    if (name !== null) fields.set(name, handlerValue(property));
  }
  return fields;
}

export function enclosingFunction(node) {
  for (let current = node.parent; current; current = current.parent) {
    if (ts.isFunctionLike(current)) return current;
  }
  return null;
}

export function importBindings(sourceFile, fromModule) {
  const named = new Map();
  const namespaces = new Set();
  for (const statement of sourceFile.statements) {
    const clause = ts.isImportDeclaration(statement) ? statement.importClause : undefined;
    const specifier = clause && statement.moduleSpecifier;
    if (!specifier || !ts.isStringLiteral(specifier) || !fromModule.test(specifier.text)) continue;
    if (clause.name) named.set(clause.name.text, "default");
    const bindings = clause.namedBindings;
    if (bindings && ts.isNamespaceImport(bindings)) namespaces.add(bindings.name.text);
    if (bindings && ts.isNamedImports(bindings)) {
      for (const element of bindings.elements) {
        named.set(element.name.text, (element.propertyName ?? element.name).text);
      }
    }
  }
  return { named, namespaces };
}

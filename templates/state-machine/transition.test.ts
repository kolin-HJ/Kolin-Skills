import assert from "node:assert/strict";
import test from "node:test";
import { transition, type State } from "./state.ts";

const idle: State = { kind: "idle" };

test("idle plus submit becomes pending", () => {
  assert.deepEqual(transition(idle, { type: "submit", id: "a" }), { kind: "pending", id: "a" });
});

test("pending plus succeed becomes done", () => {
  assert.deepEqual(transition({ kind: "pending", id: "a" }, { type: "succeed", result: "ok" }), {
    kind: "done",
    id: "a",
    result: "ok",
  });
});

test("pending plus fail becomes failed", () => {
  assert.deepEqual(transition({ kind: "pending", id: "a" }, { type: "fail", reason: "no" }), {
    kind: "failed",
    id: "a",
    reason: "no",
  });
});

test("done plus reset becomes idle", () => {
  assert.deepEqual(transition({ kind: "done", id: "a", result: "ok" }, { type: "reset" }), idle);
});

test("failed plus reset becomes idle", () => {
  assert.deepEqual(transition({ kind: "failed", id: "a", reason: "no" }, { type: "reset" }), idle);
});

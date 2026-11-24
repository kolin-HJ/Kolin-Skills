import { type Event, type State } from "./state.ts";

export type Effect =
  | { kind: "none" }
  | { kind: "start"; id: string }
  | { kind: "announce"; result: string }
  | { kind: "report"; reason: string };

export function effect(state: State, event: Event): Effect {
  if (state.kind === "idle" && event.type === "submit") {
    return { kind: "start", id: event.id };
  }
  if (state.kind === "pending" && event.type === "succeed") {
    return { kind: "announce", result: event.result };
  }
  if (state.kind === "pending" && event.type === "fail") {
    return { kind: "report", reason: event.reason };
  }
  return { kind: "none" };
}

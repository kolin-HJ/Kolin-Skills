export type State =
  | { kind: "idle" }
  | { kind: "pending"; id: string }
  | { kind: "done"; id: string; result: string }
  | { kind: "failed"; id: string; reason: string };

export type Event =
  | { type: "submit"; id: string }
  | { type: "succeed"; result: string }
  | { type: "fail"; reason: string }
  | { type: "reset" };

export function transition(state: State, event: Event): State {
  switch (state.kind) {
    case "idle":
      return event.type === "submit" ? { kind: "pending", id: event.id } : state;
    case "pending":
      if (event.type === "succeed") {
        return { kind: "done", id: state.id, result: event.result };
      }
      if (event.type === "fail") {
        return { kind: "failed", id: state.id, reason: event.reason };
      }
      return state;
    case "done":
    case "failed":
      return event.type === "reset" ? { kind: "idle" } : state;
    default: {
      const exhausted: never = state;
      return exhausted;
    }
  }
}

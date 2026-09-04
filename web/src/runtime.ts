import type {
  ExecutionError,
  JsonValue,
  RunResult,
  RunState,
  RuntimeEvent,
} from "./domain";

export type ConnectionState =
  "idle" | "connecting" | "connected" | "reconnecting" | "offline";

export interface RuntimeView {
  connection: ConnectionState;
  runId: string | null;
  runState: RunState | null;
  latestSeq: number;
  activeNodeId: string | null;
  progress: Record<string, JsonValue> | null;
  logs: RuntimeEvent[];
  errors: ExecutionError[];
  startedAt: string | null;
  finishedAt: string | null;
  result: RunResult | null;
}

export const initialRuntimeView: RuntimeView = {
  connection: "idle",
  runId: null,
  runState: null,
  latestSeq: 0,
  activeNodeId: null,
  progress: null,
  logs: [],
  errors: [],
  startedAt: null,
  finishedAt: null,
  result: null,
};

function eventError(data: Record<string, JsonValue>): ExecutionError | null {
  const candidate = data.error ?? data;
  if (!candidate || typeof candidate !== "object" || Array.isArray(candidate))
    return null;
  if (
    typeof candidate.code !== "string" ||
    typeof candidate.message !== "string"
  )
    return null;
  return candidate as unknown as ExecutionError;
}

function appendUniqueError(
  errors: ExecutionError[],
  error: ExecutionError,
): ExecutionError[] {
  const duplicate = errors.some(
    (existing) =>
      existing.code === error.code && existing.message === error.message,
  );
  return duplicate ? errors : [...errors, error];
}

export function reduceRuntimeEvent(
  state: RuntimeView,
  event: RuntimeEvent,
): RuntimeView {
  if (event.seq <= state.latestSeq) return state;
  const next: RuntimeView = {
    ...state,
    latestSeq: event.seq,
    runId: event.run_id,
  };
  const eventState = event.data.state;
  if (typeof eventState === "string") next.runState = eventState as RunState;
  if (event.type === "run.started") next.startedAt = event.occurred_at;
  if (event.type === "node.started") next.activeNodeId = event.node_id ?? null;
  if (event.type === "node.finished" && event.node_id === state.activeNodeId)
    next.activeNodeId = null;
  if (event.type === "capability.progress") next.progress = event.data;
  if (event.type === "log") next.logs = [...state.logs, event];
  if (
    event.type === "error" ||
    event.type === "node.finished" ||
    event.type === "run.finished"
  ) {
    const error = eventError(event.data);
    if (error) next.errors = appendUniqueError(state.errors, error);
  }
  if (event.type === "run.finished") next.finishedAt = event.occurred_at;
  return next;
}

export function reconnectDelay(attempt: number): number {
  return Math.min(500 * 2 ** Math.max(0, attempt), 8_000);
}

export function elapsedMilliseconds(
  startedAt: string | null,
  finishedAt: string | null,
  now = Date.now(),
): number | null {
  if (!startedAt) return null;
  return Math.max(
    0,
    (finishedAt ? Date.parse(finishedAt) : now) - Date.parse(startedAt),
  );
}

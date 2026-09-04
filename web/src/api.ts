import type {
  CapabilityManifest,
  RunResult,
  RunState,
  RuntimeEvent,
  ValidationReport,
  WorkflowDocument,
} from "./domain";
import {
  validateCapabilityManifest,
  validateRuntimeEvent,
  validateValidationReport,
} from "./validation";

export interface StartRunResponse {
  run_id: string;
  state: RunState;
}
export interface CancelRunResponse {
  run_id: string;
  accepted: boolean;
  state: RunState;
}
export interface RunSnapshot {
  run_id: string;
  state: RunState;
  done: boolean;
  last_seq: number;
  result: RunResult | null;
}

export function apiUrl(path: string, origin = window.location.origin): string {
  return new URL(`/api/v1/${path.replace(/^\//, "")}`, origin).toString();
}

export function websocketUrl(
  runId: string,
  afterSeq: number,
  origin = window.location.origin,
): string {
  const url = new URL(
    `/api/v1/runs/${encodeURIComponent(runId)}/events`,
    origin,
  );
  url.protocol = url.protocol === "https:" ? "wss:" : "ws:";
  url.searchParams.set("after_seq", String(afterSeq));
  return url.toString();
}

async function request<T>(path: string, init?: RequestInit): Promise<T> {
  const headers = new Headers(init?.headers);
  headers.set("Content-Type", "application/json");
  const response = await fetch(apiUrl(path), {
    ...init,
    headers,
  });
  if (!response.ok) {
    const body: unknown = await response.json().catch(() => null);
    const detail =
      body && typeof body === "object" && "detail" in body
        ? JSON.stringify(body.detail)
        : response.statusText;
    throw new Error(`${String(response.status)} ${detail}`);
  }
  return (await response.json()) as T;
}

export async function discoverCapabilities(): Promise<CapabilityManifest[]> {
  const values = await request<unknown[]>("capabilities");
  if (
    !Array.isArray(values) ||
    !values.every((value) => validateCapabilityManifest(value))
  )
    throw new Error("Runtime returned invalid capability manifests.");
  return values as unknown as CapabilityManifest[];
}

export async function validateRemote(
  workflow: WorkflowDocument,
): Promise<ValidationReport> {
  const report = await request<unknown>("workflows/validate", {
    method: "POST",
    body: JSON.stringify(workflow),
  });
  if (!validateValidationReport(report))
    throw new Error("Runtime returned an invalid validation report.");
  return report as unknown as ValidationReport;
}

export function startRun(
  workflow: WorkflowDocument,
): Promise<StartRunResponse> {
  return request("runs", { method: "POST", body: JSON.stringify(workflow) });
}

export function cancelRun(runId: string): Promise<CancelRunResponse> {
  return request(`runs/${encodeURIComponent(runId)}/cancel`, {
    method: "POST",
  });
}

export function getRun(runId: string): Promise<RunSnapshot> {
  return request(`runs/${encodeURIComponent(runId)}`);
}

export async function getEvents(
  runId: string,
  afterSeq: number,
): Promise<RuntimeEvent[]> {
  const events = await request<unknown[]>(
    `runs/${encodeURIComponent(runId)}/events?after_seq=${String(afterSeq)}`,
  );
  return events.filter((event): event is RuntimeEvent =>
    validateRuntimeEvent(event),
  );
}

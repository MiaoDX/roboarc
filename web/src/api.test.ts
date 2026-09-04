import { afterEach, describe, expect, it, vi } from "vitest";

import { apiUrl, cancelRun, startRun, websocketUrl } from "./api";
import type { WorkflowDocument } from "./domain";

const workflow: WorkflowDocument = {
  workflow_schema_version: 1,
  id: "workflow",
  name: "Demo",
  workflow: { type: "wait", id: "wait", duration_ms: 5 },
};

afterEach(() => vi.unstubAllGlobals());

describe("runtime API client", () => {
  it("builds HTTP and WebSocket URLs with replay sequence", () => {
    expect(apiUrl("capabilities", "http://localhost:8000/base")).toBe(
      "http://localhost:8000/api/v1/capabilities",
    );
    expect(websocketUrl("run/a", 12, "https://robot.test")).toBe(
      "wss://robot.test/api/v1/runs/run%2Fa/events?after_seq=12",
    );
  });

  it("posts the canonical workflow body to start a run", async () => {
    const fetchMock = vi.fn().mockResolvedValue(
      new Response(JSON.stringify({ run_id: "run-1", state: "running" }), {
        status: 201,
        headers: { "Content-Type": "application/json" },
      }),
    );
    vi.stubGlobal("fetch", fetchMock);
    vi.stubGlobal("window", { location: { origin: "http://localhost:5173" } });
    await startRun(workflow);
    expect(fetchMock).toHaveBeenCalledWith(
      "http://localhost:5173/api/v1/runs",
      expect.objectContaining({
        method: "POST",
        body: JSON.stringify(workflow),
      }),
    );
  });

  it("posts cancellation without claiming completion", async () => {
    const fetchMock = vi.fn().mockResolvedValue(
      new Response(
        JSON.stringify({
          run_id: "run-1",
          accepted: true,
          state: "canceling",
        }),
        { status: 200, headers: { "Content-Type": "application/json" } },
      ),
    );
    vi.stubGlobal("fetch", fetchMock);
    vi.stubGlobal("window", { location: { origin: "http://localhost:5173" } });
    await expect(cancelRun("run-1")).resolves.toMatchObject({
      accepted: true,
      state: "canceling",
    });
    expect(fetchMock).toHaveBeenCalledWith(
      "http://localhost:5173/api/v1/runs/run-1/cancel",
      expect.objectContaining({ method: "POST" }),
    );
  });
});

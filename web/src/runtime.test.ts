import { describe, expect, it } from "vitest";

import type { RuntimeEvent } from "./domain";
import {
  elapsedMilliseconds,
  initialRuntimeView,
  reconnectDelay,
  reduceRuntimeEvent,
} from "./runtime";

function event(
  seq: number,
  type: RuntimeEvent["type"],
  data: RuntimeEvent["data"] = {},
): RuntimeEvent {
  return {
    event_protocol_version: 1,
    event_id: `00000000-0000-4000-8000-${String(seq).padStart(12, "0")}`,
    seq,
    run_id: "run-1",
    node_id: "block_61",
    type,
    occurred_at: `2026-01-01T00:00:0${String(seq)}Z`,
    data,
  };
}

describe("runtime event reduction", () => {
  it("accepts only increasing sequences and preserves replay cursor", () => {
    const started = reduceRuntimeEvent(
      initialRuntimeView,
      event(2, "node.started", { state: "running" }),
    );
    expect(started.activeNodeId).toBe("block_61");
    expect(
      reduceRuntimeEvent(
        started,
        event(2, "node.finished", { state: "succeeded" }),
      ),
    ).toBe(started);
    expect(
      reduceRuntimeEvent(started, event(1, "log", { message: "old" })),
    ).toBe(started);
  });

  it("retains progress provenance and cancellation-incomplete errors", () => {
    const progress = reduceRuntimeEvent(
      initialRuntimeView,
      event(1, "capability.progress", {
        percent: 40,
        source: "native",
        stage: "moving",
      }),
    );
    const failed = reduceRuntimeEvent(
      progress,
      event(2, "run.finished", {
        state: "failed",
        error: {
          code: "cancellation_incomplete",
          message: "cleanup expired",
          details: {},
        },
      }),
    );
    expect(failed.progress).toMatchObject({ percent: 40, source: "native" });
    expect(failed.errors[0].code).toBe("cancellation_incomplete");
    expect(failed.runState).toBe("failed");

    const duplicate = reduceRuntimeEvent(
      failed,
      event(3, "run.finished", {
        state: "failed",
        error: {
          code: "cancellation_incomplete",
          message: "cleanup expired",
          details: { source: "run" },
        },
      }),
    );
    expect(duplicate.errors).toHaveLength(1);
  });

  it("bounds reconnect backoff and computes terminal duration", () => {
    expect(reconnectDelay(0)).toBe(500);
    expect(reconnectDelay(20)).toBe(8_000);
    expect(
      elapsedMilliseconds("2026-01-01T00:00:00Z", "2026-01-01T00:00:02.500Z"),
    ).toBe(2_500);
  });
});

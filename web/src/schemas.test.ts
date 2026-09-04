import { describe, expect, it } from "vitest";

import type {
  CapabilityManifest,
  RuntimeEvent,
  ValidationReport,
} from "./domain";
import {
  validateCapabilityManifest,
  validateRuntimeEvent,
  validateValidationReport,
} from "./validation";

describe("vendored contract schemas", () => {
  it("validates a complete capability manifest", () => {
    const manifest: CapabilityManifest = {
      manifest_schema_version: 1,
      id: "speech.say",
      version: 2,
      title: "Say",
      category: "Speech",
      description: "Speak text",
      inputs: {},
      outputs: {},
      execution: { timeout_ms: 30_000, cancellable: true },
      progress: { mode: "none", source: null },
      resources: ["speaker"],
    };
    expect(validateCapabilityManifest(manifest)).toBe(true);
  });

  it("validates runtime events and validation reports", () => {
    const event: RuntimeEvent = {
      event_protocol_version: 1,
      event_id: "00000000-0000-4000-8000-000000000000",
      seq: 1,
      run_id: "run_1",
      node_id: null,
      type: "run.started",
      occurred_at: "2026-01-01T00:00:00Z",
      data: {},
    };
    const report: ValidationReport = { valid: true, issues: [] };

    expect(validateRuntimeEvent(event)).toBe(true);
    expect(validateValidationReport(report)).toBe(true);
  });

  it("rejects incorrect serialized version fields", () => {
    expect(
      validateRuntimeEvent({
        event_protocol_version: 2,
        seq: 1,
        run_id: "run_1",
        type: "run.started",
        occurred_at: "2026-01-01T00:00:00Z",
      }),
    ).toBe(false);
  });
});

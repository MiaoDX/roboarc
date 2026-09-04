import { describe, expect, it } from "vitest";

import type { WorkflowDocument } from "./domain";
import {
  activeNodeAt,
  groupReviewCatalog,
  nodeIntervals,
  parseReviewCatalog,
  parseReviewManifest,
  workflowSteps,
} from "./review";

const workflow: WorkflowDocument = {
  workflow_schema_version: 1,
  id: "nested-demo",
  name: "Nested demo",
  workflow: {
    type: "sequence",
    id: "root",
    children: [
      { type: "wait", id: "settle", duration_ms: 250 },
      {
        type: "sequence",
        id: "nested",
        children: [
          {
            type: "capability",
            id: "speak",
            capability: { id: "speech.say", version: 1 },
            args: { text: "hello" },
          },
        ],
      },
    ],
  },
};

function manifest() {
  return {
    review_schema_version: 1 as const,
    workflow,
    result: {
      run_id: "run-1",
      workflow_id: workflow.id,
      state: "succeeded",
      error: null,
      started_at: "2026-09-01T00:00:00Z",
      finished_at: "2026-09-01T00:00:01Z",
    },
    profile_id: "robot-sim",
    observation_count: 12,
    artifacts: { trace: "trace.jsonl", rerun: null, video: "review.mp4" },
  };
}

describe("review artifacts", () => {
  it("groups the recorded catalog into mock, TIAGo, and Reachy demos", () => {
    const entries = [
      "mock-demo",
      "simulation-observable",
      "tiago-look-and-say",
      "tiago-proof-final",
      "tiago-observable",
      "reachy-proof-final",
    ].map((id) => ({
      id,
      artifact_root: id,
      manifest: null,
      workflow,
      profile_id: null,
      recorded: false,
    }));

    expect(
      groupReviewCatalog(entries).map((group) => [
        group.id,
        group.entries.map(({ id }) => id),
      ]),
    ).toEqual([
      ["mock", ["mock-demo", "simulation-observable"]],
      [
        "tiago",
        ["tiago-look-and-say", "tiago-proof-final", "tiago-observable"],
      ],
      ["reachy", ["reachy-proof-final"]],
    ]);
  });

  it("parses a catalog of review artifact sets", () => {
    const parsed = parseReviewCatalog([
      {
        id: "tiago-proof-final",
        artifact_root: "tiago-proof-final",
        manifest: manifest(),
        workflow,
        profile_id: "robot-sim",
        recorded: true,
      },
    ]);
    expect(parsed[0].manifest?.workflow.id).toBe("nested-demo");
  });

  it("derives half-open leaf node intervals from a matching trace", () => {
    const events = [
      {
        event_protocol_version: 1 as const,
        event_id: "event-1",
        seq: 1,
        run_id: "run-1",
        node_id: "settle",
        type: "node.started" as const,
        occurred_at: "2026-09-01T00:00:00.100Z",
        data: {},
      },
      {
        event_protocol_version: 1 as const,
        event_id: "event-2",
        seq: 2,
        run_id: "run-1",
        node_id: "settle",
        type: "node.finished" as const,
        occurred_at: "2026-09-01T00:00:00.900Z",
        data: {},
      },
    ];
    const intervals = nodeIntervals(events, "run-1", "2026-09-01T00:00:00Z");
    expect(intervals).toEqual([{ nodeId: "settle", startMs: 100, endMs: 900 }]);
    expect(activeNodeAt(intervals, 100)).toBe("settle");
    expect(activeNodeAt(intervals, 900)).toBeNull();
  });

  it("prefers the nested node over its active parent sequence", () => {
    const intervals = [
      { nodeId: "root", startMs: 0, endMs: 1000 },
      { nodeId: "navigate", startMs: 100, endMs: 700 },
    ];
    expect(activeNodeAt(intervals, 400)).toBe("navigate");
  });

  it("accepts a matching run and recursively lists every workflow node", () => {
    const parsed = parseReviewManifest(manifest());

    expect(
      workflowSteps(parsed.workflow).map(({ node, depth }) => [node.id, depth]),
    ).toEqual([
      ["settle", 0],
      ["nested", 0],
      ["speak", 1],
    ]);
  });

  it("rejects mismatched run identity and unsafe artifact paths", () => {
    const wrongRun = manifest();
    wrongRun.result.workflow_id = "another-workflow";
    expect(() => parseReviewManifest(wrongRun)).toThrow(/does not match/);

    const unsafeArtifact = manifest();
    unsafeArtifact.artifacts.video = "../outside.mp4";
    expect(() => parseReviewManifest(unsafeArtifact)).toThrow(/metadata/);
  });
});

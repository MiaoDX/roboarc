import { describe, expect, it } from "vitest";

import type { CapabilityNode } from "./domain";
import { nodeSummary } from "./ReviewApp";

function capability(
  id: string,
  args: Record<string, string | number>,
): CapabilityNode {
  return {
    type: "capability",
    id,
    capability: { id, version: 1 },
    args,
  };
}

describe("TIAGo review summaries", () => {
  it("renders semantic labels for representable TIAGo capabilities", () => {
    expect([
      nodeSummary(
        capability("navigation.goto_location", { target: "reception" }),
        "tiago-sim",
      ),
      nodeSummary(
        capability("head.look_at", {
          frame: "base_footprint",
          x: 1.5,
          y: 0,
          z: 1.6,
        }),
        "tiago-sim",
      ),
      nodeSummary(capability("speech.say", { text: "Welcome!" }), "tiago-sim"),
      nodeSummary(capability("navigation.stop", {}), "tiago-sim"),
    ]).toEqual([
      { label: "Go to", detail: "reception" },
      { label: "Look", detail: "ahead" },
      { label: "Say", detail: "Welcome!" },
      { label: "Stop navigation", detail: "navigation control action" },
    ]);
  });

  it("keeps non-representable payloads technical and lossless", () => {
    expect(
      nodeSummary(
        capability("head.look_at", {
          frame: "base_footprint",
          x: 2,
          y: 0,
          z: 1.6,
          note: "keep",
        }),
        "tiago-sim",
      ),
    ).toEqual({
      label: "head.look_at@1",
      detail: '{"frame":"base_footprint","x":2,"y":0,"z":1.6,"note":"keep"}',
    });
    expect(
      nodeSummary(
        capability("navigation.goto_location", { target: "unknown" }),
        "tiago-sim",
      ),
    ).toEqual({
      label: "navigation.goto_location@1",
      detail: '{"target":"unknown"}',
    });
  });
});

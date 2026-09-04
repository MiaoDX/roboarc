import { describe, expect, it } from "vitest";

import type { CapabilityManifest } from "./domain";
import { toolboxFromManifests } from "./domain";

function manifest(
  id: string,
  version: number,
  category: string,
): CapabilityManifest {
  return {
    manifest_schema_version: 1,
    id,
    version,
    title: id,
    category,
    description: null,
    inputs: {},
    outputs: {},
    execution: { timeout_ms: 30_000, cancellable: false },
    progress: { mode: "none", source: null },
    resources: [],
  };
}

describe("capability toolbox", () => {
  it("groups exact capability versions by manifest category", () => {
    const toolbox = toolboxFromManifests([
      manifest("speech.say", 3, "Speech"),
      manifest("motion.goto", 1, "Motion"),
      manifest("speech.listen", 2, "Speech"),
    ]);

    expect(toolbox.contents.map((category) => category.name)).toEqual([
      "Workflow",
      "Motion",
      "Speech",
    ]);
    expect(toolbox.contents[2].contents.map((block) => block.fields)).toEqual([
      { CAPABILITY: "speech.listen@2" },
      { CAPABILITY: "speech.say@3" },
    ]);
  });

  it("uses named category styles instead of inline color tokens", () => {
    const toolbox = toolboxFromManifests([manifest("speech.say", 1, "Speech")]);
    const serialized = JSON.stringify(toolbox);

    expect(serialized).not.toMatch(/#[0-9a-f]{3,8}/i);
    expect(toolbox.contents.every((category) => category.categorystyle)).toBe(
      true,
    );
  });

  it("adds semantic Reachy actions when the arm pose contract is available", () => {
    const toolbox = toolboxFromManifests([
      manifest("reachy.arm.gesture", 1, "Reachy actions"),
    ]);
    expect(toolbox.contents.map((category) => category.name)).toEqual([
      "Workflow",
      "Reachy actions",
    ]);
    expect(toolbox.contents.at(-1)).toMatchObject({ name: "Reachy actions" });
  });

  it("uses semantic TIAGo blocks and hides their generic capability entries", () => {
    const toolbox = toolboxFromManifests(
      [
        manifest("navigation.goto_location", 1, "Navigation"),
        manifest("navigation.stop", 1, "Navigation"),
        manifest("head.look_at", 1, "Head"),
        manifest("speech.say", 1, "Speech"),
      ],
      "tiago-sim",
    );

    expect(toolbox.contents.map((category) => category.name)).toEqual([
      "Workflow",
      "TIAGo actions",
    ]);
    expect(
      toolbox.contents.at(-1)?.contents.map((block) => block.type),
    ).toEqual([
      "tiago_goto_location",
      "tiago_look_at",
      "tiago_say",
      "tiago_stop_navigation",
    ]);
    expect(JSON.stringify(toolbox)).not.toContain("robo_capability");
  });

  it("does not apply TIAGo presets to shared capabilities on other profiles", () => {
    const toolbox = toolboxFromManifests(
      [manifest("speech.say", 1, "Speech")],
      "another-robot",
    );

    expect(toolbox.contents.map((category) => category.name)).toEqual([
      "Workflow",
      "Speech",
    ]);
    expect(toolbox.contents[1].contents[0]).toMatchObject({
      type: "robo_capability",
      fields: { CAPABILITY: "speech.say@1" },
    });
  });
});

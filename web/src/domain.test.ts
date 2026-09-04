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
});

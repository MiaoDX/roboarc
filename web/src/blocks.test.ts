import * as Blockly from "blockly/core";
import { beforeAll, describe, expect, it } from "vitest";

import {
  getCapabilityArguments,
  getCapabilityReference,
  registerBlocks,
  setCapabilityArgument,
  setCapabilityArguments,
  setCapabilityReference,
} from "./blocks";
import { compileWorkspace, loadProject, saveProject } from "./compiler";
import type { CapabilityNode } from "./domain";

beforeAll(registerBlocks);

describe("capability block helpers", () => {
  it("sets typed references and arguments without a raw JSON field", () => {
    const workspace = new Blockly.Workspace();
    const block = workspace.newBlock("robo_capability");

    setCapabilityReference(block, { id: "speech.say", version: 2 });
    setCapabilityArguments(block, { text: "hello", repeat: 2 });
    setCapabilityArgument(block, "urgent", true);
    setCapabilityArgument(block, "repeat", undefined);

    expect(block.getField("ARGS")).toBeNull();
    expect(getCapabilityReference(block)).toEqual({
      id: "speech.say",
      version: 2,
    });
    expect(getCapabilityArguments(block)).toEqual({
      text: "hello",
      urgent: true,
    });
    expect(compileWorkspace(workspace).workflow).toMatchObject({
      capability: { id: "speech.say", version: 2 },
      args: { text: "hello", urgent: true },
    });
  });

  it("persists arguments in Blockly editor state", () => {
    const workspace = new Blockly.Workspace();
    const block = workspace.newBlock("robo_capability");
    setCapabilityArguments(block, { location: "dock", precise: true });
    const restored = new Blockly.Workspace();

    loadProject(saveProject(workspace, "Demo"), restored);

    const restoredNode = compileWorkspace(restored).workflow as CapabilityNode;
    expect(restoredNode.args).toEqual({ location: "dock", precise: true });
  });

  it("rejects non-JSON argument values", () => {
    const block = new Blockly.Workspace().newBlock("robo_capability");
    expect(() => {
      setCapabilityArguments(block, { bad: Number.POSITIVE_INFINITY });
    }).toThrow(/finite JSON/);
  });
});

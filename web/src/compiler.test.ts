import * as Blockly from "blockly/core";
import { beforeAll, describe, expect, it } from "vitest";

import { registerBlocks } from "./blocks";
import {
  blockForNodeId,
  compileWorkspace,
  loadProject,
  loadWorkflow,
  saveProject,
  WorkflowDraftError,
} from "./compiler";
import type { SequenceNode, WaitNode } from "./domain";
import { validateProject, validateWorkflow } from "./validation";

beforeAll(() => {
  registerBlocks();
  Blockly.common.defineBlocks(
    Blockly.common.createBlockDefinitionsFromJsonArray([
      { type: "unsupported_test", message0: "unsupported" },
    ]),
  );
});

function requireConnection(
  connection: Blockly.Connection | null,
): Blockly.Connection {
  if (connection === null) {
    throw new Error("test block connection is missing");
  }
  return connection;
}

function sequenceWorkspace(): {
  workspace: Blockly.Workspace;
  sequence: Blockly.Block;
  wait: Blockly.Block;
} {
  const workspace = new Blockly.Workspace();
  const sequence = workspace.newBlock("robo_sequence");
  const wait = workspace.newBlock("robo_wait");
  wait.setFieldValue("125", "DURATION");
  sequence
    .getInput("CHILDREN")
    ?.connection?.connect(requireConnection(wait.previousConnection));
  return { workspace, sequence, wait };
}

describe("workspace compiler", () => {
  it("distinguishes an empty authoring draft from malformed workflows", () => {
    const workspace = new Blockly.Workspace();
    workspace.newBlock("robo_sequence");

    expect(() => compileWorkspace(workspace)).toThrow(WorkflowDraftError);
    expect(() => compileWorkspace(workspace)).toThrow(
      "Add a step to generate Workflow IR.",
    );
  });

  it("emits exact versions and a schema-valid workflow", () => {
    const { workspace } = sequenceWorkspace();
    const workflow = compileWorkspace(workspace, "Demo");

    expect(workflow.workflow_schema_version).toBe(1);
    expect(validateWorkflow(workflow)).toBe(true);
  });

  it("keeps node IDs stable when a block moves structurally", () => {
    const { workspace, sequence, wait } = sequenceWorkspace();
    const before = (compileWorkspace(workspace).workflow as SequenceNode)
      .children[0].id;
    const inserted = workspace.newBlock("robo_wait");

    sequence.getInput("CHILDREN")?.connection?.disconnect();
    inserted.nextConnection?.connect(
      requireConnection(wait.previousConnection),
    );
    sequence
      .getInput("CHILDREN")
      ?.connection?.connect(requireConnection(inserted.previousConnection));

    const children = (compileWorkspace(workspace).workflow as SequenceNode)
      .children;
    expect(children[1].id).toBe(before);
    expect(blockForNodeId(workspace, before)).toBe(wait);
  });

  it("keeps block and node identity through a project round trip", () => {
    const { workspace, wait } = sequenceWorkspace();
    const project = saveProject(workspace, "Demo");
    const nodeId = (project.workflow.workflow as SequenceNode).children[0].id;
    const restored = new Blockly.Workspace();

    loadProject(project, restored);

    expect(blockForNodeId(restored, nodeId)?.id).toBe(wait.id);
    expect(compileWorkspace(restored, "Demo")).toEqual(project.workflow);
    expect(validateProject(project)).toBe(true);
  });

  it("loads canonical Workflow IR and preserves node IDs for highlighting", () => {
    const workflow = compileWorkspace(sequenceWorkspace().workspace, "Demo");
    workflow.workflow.id = "canonical-root";
    const sourceChild = (workflow.workflow as SequenceNode).children[0];
    sourceChild.id = "canonical-step";
    const destination = new Blockly.Workspace();
    loadWorkflow(workflow, destination);

    expect(blockForNodeId(destination, "canonical-step")).not.toBeNull();
    expect(blockForNodeId(destination, "missing-step")).toBeNull();
    expect(compileWorkspace(destination, "Demo").workflow).toEqual(
      workflow.workflow,
    );
  });

  it("rejects a full invalid project without mutating the destination", () => {
    const source = sequenceWorkspace().workspace;
    const invalid = saveProject(source, "Demo") as unknown as Record<
      string,
      unknown
    >;
    invalid.name = "";
    const destination = sequenceWorkspace().workspace;
    const before = Blockly.serialization.workspaces.save(destination);

    expect(() => {
      loadProject(invalid, destination);
    }).toThrow(/invalid ProjectDocument/);
    expect(Blockly.serialization.workspaces.save(destination)).toEqual(before);
  });

  it("rejects unsupported blocks and malformed capability versions", () => {
    const unsupported = new Blockly.Workspace();
    unsupported.newBlock("unsupported_test");
    expect(() => compileWorkspace(unsupported)).toThrow(/unsupported/);

    const capabilityWorkspace = new Blockly.Workspace();
    const capability = capabilityWorkspace.newBlock("robo_capability");
    capability.setFieldValue("bad", "CAPABILITY");
    expect(() => compileWorkspace(capabilityWorkspace)).toThrow(/id@version/);
    capability.setFieldValue("speech.say@0", "CAPABILITY");
    expect(() => compileWorkspace(capabilityWorkspace)).toThrow(
      /positive integer/,
    );
  });

  it("preserves literal wait values", () => {
    const { workspace } = sequenceWorkspace();
    const wait = (compileWorkspace(workspace).workflow as SequenceNode)
      .children[0] as WaitNode;
    expect(wait.duration_ms).toBe(125);
  });
});

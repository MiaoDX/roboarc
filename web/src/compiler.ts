import * as Blockly from "blockly/core";

import {
  getCapabilityArguments,
  getCapabilityReference,
  getWorkflowNodeId,
  setCapabilityArguments,
  setCapabilityReference,
  setWorkflowNodeId,
} from "./blocks";
import type { ProjectDocument, WorkflowDocument, WorkflowNode } from "./domain";
import { validateProject } from "./validation";

const NODE_ID_PREFIX = "block_";

export class WorkflowDraftError extends Error {
  constructor(message: string) {
    super(message);
    this.name = "WorkflowDraftError";
  }
}

export function nodeIdForBlockId(blockId: string): string {
  const bytes = new TextEncoder().encode(blockId);
  const encoded = [...bytes]
    .map((byte) => byte.toString(16).padStart(2, "0"))
    .join("");
  const nodeId = `${NODE_ID_PREFIX}${encoded}`;
  if (nodeId.length > 128) {
    throw new Error("Blockly block ID is too long for a Workflow node ID");
  }
  return nodeId;
}

export function blockIdForNodeId(nodeId: string): string | null {
  if (!nodeId.startsWith(NODE_ID_PREFIX)) {
    return null;
  }
  const encoded = nodeId.slice(NODE_ID_PREFIX.length);
  if (!encoded || encoded.length % 2 !== 0 || !/^[0-9a-f]+$/.test(encoded)) {
    return null;
  }
  const bytes = new Uint8Array(
    encoded.match(/../g)?.map((pair) => Number.parseInt(pair, 16)) ?? [],
  );
  try {
    return new TextDecoder("utf-8", { fatal: true }).decode(bytes);
  } catch {
    return null;
  }
}

export function blockForNodeId(
  workspace: Blockly.Workspace,
  nodeId: string,
): Blockly.Block | null {
  const blockId = blockIdForNodeId(nodeId);
  if (blockId !== null) return workspace.getBlockById(blockId);
  return (
    workspace
      .getAllBlocks(false)
      .find((block) => getWorkflowNodeId(block) === nodeId) ?? null
  );
}

function compileBlock(block: Blockly.Block): WorkflowNode {
  const id = getWorkflowNodeId(block) ?? nodeIdForBlockId(block.id);
  if (block.type === "robo_sequence") {
    const children: WorkflowNode[] = [];
    let child = block.getInputTargetBlock("CHILDREN");
    while (child) {
      children.push(compileBlock(child));
      child = child.getNextBlock();
    }
    if (children.length === 0) {
      throw new WorkflowDraftError("Add a step to generate Workflow IR.");
    }
    return { type: "sequence", id, children };
  }
  if (block.type === "robo_wait") {
    return {
      type: "wait",
      id,
      duration_ms: Number(block.getFieldValue("DURATION") ?? 0),
    };
  }
  if (block.type === "robo_capability") {
    return {
      type: "capability",
      id,
      capability: getCapabilityReference(block),
      args: getCapabilityArguments(block),
    };
  }
  throw new Error(`unsupported block: ${block.type}`);
}

export function compileWorkspace(
  workspace: Blockly.Workspace,
  name = "Untitled",
  workflowId = "workflow",
): WorkflowDocument {
  const roots = workspace.getTopBlocks(true);
  if (roots.length !== 1) {
    throw new Error("workspace must have exactly one root");
  }
  return {
    workflow_schema_version: 1,
    id: workflowId,
    name,
    workflow: compileBlock(roots[0]),
  };
}

export function saveProject(
  workspace: Blockly.Workspace,
  name: string,
): ProjectDocument {
  return {
    project_format_version: 1,
    name,
    editor: {
      editor_state_version: 1,
      type: "blockly",
      state: Blockly.serialization.workspaces.save(workspace),
    },
    workflow: compileWorkspace(workspace, name),
  };
}

export function loadProject(
  project: unknown,
  workspace: Blockly.Workspace,
): void {
  if (!validateProject(project)) {
    throw new Error("invalid ProjectDocument");
  }
  const validProject = project as unknown as ProjectDocument;
  if (validProject.editor?.editor_state_version !== 1) {
    throw new Error("unsupported editor state");
  }
  Blockly.serialization.workspaces.load(validProject.editor.state, workspace);
}

export function loadWorkflow(
  workflow: WorkflowDocument,
  workspace: Blockly.Workspace,
): void {
  workspace.clear();
  const build = (node: WorkflowNode): Blockly.Block => {
    const block = workspace.newBlock(
      node.type === "sequence"
        ? "robo_sequence"
        : node.type === "wait"
          ? "robo_wait"
          : "robo_capability",
      blockIdForNodeId(node.id) ?? undefined,
    );
    setWorkflowNodeId(block, node.id);
    if (block instanceof Blockly.BlockSvg) block.initSvg();
    if (node.type === "sequence") {
      let previous: Blockly.Block | null = null;
      for (const child of node.children) {
        const childBlock = build(child);
        const childConnection = childBlock.previousConnection;
        if (!childConnection)
          throw new Error("Workflow child block cannot join a sequence");
        if (previous) {
          const nextConnection = previous.nextConnection;
          if (!nextConnection)
            throw new Error("Workflow child block cannot precede another node");
          nextConnection.connect(childConnection);
        } else {
          const sequenceConnection = block.getInput("CHILDREN")?.connection;
          if (!sequenceConnection)
            throw new Error("Sequence block has no child connection");
          sequenceConnection.connect(childConnection);
        }
        previous = childBlock;
      }
    } else if (node.type === "wait")
      block.setFieldValue(String(node.duration_ms), "DURATION");
    else {
      setCapabilityReference(block, node.capability);
      setCapabilityArguments(block, node.args);
    }
    if (block instanceof Blockly.BlockSvg) block.render();
    return block;
  };
  const root = build(workflow.workflow);
  if (root instanceof Blockly.BlockSvg) root.moveBy(64, 48);
}

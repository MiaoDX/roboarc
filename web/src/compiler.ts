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
import {
  isReachyActionArgs,
  REACHY_ACTIONS,
  type ReachyActionId,
} from "./reachy-actions";
import {
  isExactArgs,
  tiagoLocation,
  tiagoLookPreset,
  TIAGO_LOOK_PRESETS,
} from "./tiago-actions";

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
  if (block.type === "robo_action") {
    const action = String(block.getFieldValue("ACTION")) as ReachyActionId;
    if (!REACHY_ACTIONS.some((item) => item.id === action))
      throw new WorkflowDraftError("Unknown Reachy action.");
    const side = String(block.getFieldValue("SIDE")) as "left" | "right";
    const duration_ms = Number(block.getFieldValue("DURATION") ?? 1000);
    return {
      type: "capability",
      id,
      capability: { id: "reachy.arm.gesture", version: 1 },
      args: { gesture: action, side, duration_ms },
    };
  }
  if (block.type === "tiago_goto_location") {
    const target = String(block.getFieldValue("LOCATION") ?? "");
    if (!tiagoLocation(target))
      throw new WorkflowDraftError("Unknown TIAGo map location.");
    return {
      type: "capability",
      id,
      capability: { id: "navigation.goto_location", version: 1 },
      args: { target },
    };
  }
  if (block.type === "tiago_look_at") {
    const preset = tiagoLookPreset(String(block.getFieldValue("TARGET")));
    if (!preset) throw new WorkflowDraftError("Unknown TIAGo look target.");
    return {
      type: "capability",
      id,
      capability: { id: "head.look_at", version: 1 },
      args: { ...preset.args },
    };
  }
  if (block.type === "tiago_say") {
    return {
      type: "capability",
      id,
      capability: { id: "speech.say", version: 1 },
      args: { text: String(block.getFieldValue("TEXT") ?? "") },
    };
  }
  if (block.type === "tiago_stop_navigation") {
    return {
      type: "capability",
      id,
      capability: { id: "navigation.stop", version: 1 },
      args: {},
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
  profileId?: string,
): void {
  workspace.clear();
  const build = (node: WorkflowNode): Blockly.Block => {
    const isReachyAction =
      node.type === "capability" &&
      node.capability.id === "reachy.arm.gesture" &&
      node.capability.version === 1 &&
      isReachyActionArgs(node.args);
    const tiagoType = (() => {
      if (
        profileId !== "tiago-sim" ||
        node.type !== "capability" ||
        node.capability.version !== 1
      )
        return null;
      if (
        node.capability.id === "navigation.goto_location" &&
        typeof node.args.target === "string" &&
        tiagoLocation(node.args.target) &&
        isExactArgs(node.args, { target: node.args.target })
      )
        return "tiago_goto_location";
      if (
        node.capability.id === "head.look_at" &&
        TIAGO_LOOK_PRESETS.some((preset) => isExactArgs(node.args, preset.args))
      )
        return "tiago_look_at";
      if (
        node.capability.id === "speech.say" &&
        typeof node.args.text === "string" &&
        isExactArgs(node.args, { text: node.args.text })
      )
        return "tiago_say";
      if (
        node.capability.id === "navigation.stop" &&
        isExactArgs(node.args, {})
      )
        return "tiago_stop_navigation";
      return null;
    })();
    const block = workspace.newBlock(
      node.type === "sequence"
        ? "robo_sequence"
        : node.type === "wait"
          ? "robo_wait"
          : isReachyAction
            ? "robo_action"
            : (tiagoType ?? "robo_capability"),
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
      if (block.type === "robo_action" && isReachyActionArgs(node.args)) {
        const gestureValue = node.args.gesture;
        const gesture =
          typeof gestureValue === "string" &&
          REACHY_ACTIONS.some((item) => item.id === gestureValue)
            ? gestureValue
            : "home";
        block.setFieldValue(gesture, "ACTION");
        block.setFieldValue(node.args.side, "SIDE");
        block.setFieldValue(String(node.args.duration_ms), "DURATION");
      } else if (block.type === "tiago_goto_location") {
        block.setFieldValue(
          typeof node.args.target === "string" ? node.args.target : "home",
          "LOCATION",
        );
      } else if (block.type === "tiago_look_at") {
        const preset = TIAGO_LOOK_PRESETS.find((item) =>
          isExactArgs(node.args, item.args),
        );
        block.setFieldValue(preset?.id ?? TIAGO_LOOK_PRESETS[0].id, "TARGET");
      } else if (block.type === "tiago_say") {
        block.setFieldValue(
          typeof node.args.text === "string" ? node.args.text : "",
          "TEXT",
        );
      } else if (block.type !== "tiago_stop_navigation") {
        setCapabilityReference(block, node.capability);
        setCapabilityArguments(block, node.args);
      }
    }
    if (block instanceof Blockly.BlockSvg) block.render();
    return block;
  };
  const root = build(workflow.workflow);
  if (root instanceof Blockly.BlockSvg) root.moveBy(64, 48);
}

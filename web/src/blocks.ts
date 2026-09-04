import * as Blockly from "blockly/core";

import type { CapabilityRef, JsonValue } from "./domain";

interface CapabilityBlockData {
  capabilityArguments?: Record<string, JsonValue>;
}

function capabilityData(block: Blockly.Block): CapabilityBlockData {
  if (!block.data) {
    return {};
  }
  try {
    const value: unknown = JSON.parse(block.data);
    return value !== null && typeof value === "object" && !Array.isArray(value)
      ? value
      : {};
  } catch {
    return {};
  }
}

function assertCapabilityBlock(block: Blockly.Block): void {
  if (block.type !== "robo_capability") {
    throw new Error("capability helpers require a robo_capability block");
  }
}

function isJsonValue(value: unknown): value is JsonValue {
  if (
    value === null ||
    typeof value === "string" ||
    typeof value === "boolean"
  ) {
    return true;
  }
  if (typeof value === "number") {
    return Number.isFinite(value);
  }
  if (Array.isArray(value)) {
    return value.every(isJsonValue);
  }
  if (typeof value === "object") {
    return Object.values(value).every(isJsonValue);
  }
  return false;
}

export function getCapabilityReference(block: Blockly.Block): CapabilityRef {
  assertCapabilityBlock(block);
  const raw = String(block.getFieldValue("CAPABILITY"));
  const separator = raw.lastIndexOf("@");
  const version = Number(raw.slice(separator + 1));
  if (separator < 1 || !Number.isInteger(version) || version < 1) {
    throw new Error(
      "capability must use id@version with a positive integer version",
    );
  }
  return { id: raw.slice(0, separator), version };
}

export function setCapabilityReference(
  block: Blockly.Block,
  capability: CapabilityRef,
): void {
  assertCapabilityBlock(block);
  if (
    !capability.id ||
    !Number.isInteger(capability.version) ||
    capability.version < 1
  ) {
    throw new Error("invalid capability reference");
  }
  block.setFieldValue(
    `${capability.id}@${String(capability.version)}`,
    "CAPABILITY",
  );
}

export function getCapabilityArguments(
  block: Blockly.Block,
): Record<string, JsonValue> {
  assertCapabilityBlock(block);
  return { ...capabilityData(block).capabilityArguments };
}

export function setCapabilityArguments(
  block: Blockly.Block,
  args: Record<string, JsonValue>,
): void {
  assertCapabilityBlock(block);
  if (!isJsonValue(args)) {
    throw new Error("capability arguments must contain finite JSON values");
  }
  block.data = JSON.stringify({
    ...capabilityData(block),
    capabilityArguments: args,
  });
}

export function setCapabilityArgument(
  block: Blockly.Block,
  name: string,
  value: JsonValue | undefined,
): void {
  const args = getCapabilityArguments(block);
  if (value === undefined) {
    Reflect.deleteProperty(args, name);
    setCapabilityArguments(block, args);
    return;
  }
  args[name] = value;
  setCapabilityArguments(block, args);
}

export function registerBlocks(): void {
  Blockly.common.defineBlocks(
    Blockly.common.createBlockDefinitionsFromJsonArray([
      {
        type: "robo_sequence",
        message0: "sequence %1",
        args0: [{ type: "input_statement", name: "CHILDREN" }],
        style: "roboarc_workflow_blocks",
      },
      {
        type: "robo_wait",
        message0: "wait %1 ms",
        args0: [
          {
            type: "field_number",
            name: "DURATION",
            value: 0,
            min: 0,
            max: 86_400_000,
            precision: 1,
          },
        ],
        previousStatement: null,
        nextStatement: null,
        style: "roboarc_workflow_blocks",
      },
      {
        type: "robo_capability",
        message0: "capability %1",
        args0: [
          {
            type: "field_input",
            name: "CAPABILITY",
            text: "example@1",
          },
        ],
        previousStatement: null,
        nextStatement: null,
        style: "roboarc_capability_blocks",
      },
    ]),
  );
}

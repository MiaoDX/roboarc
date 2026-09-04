export type JsonPrimitive = string | number | boolean | null;
export type JsonValue =
  JsonPrimitive | JsonValue[] | { [key: string]: JsonValue };

export type ValueType =
  "string" | "integer" | "number" | "boolean" | "duration_ms" | "map_location";

export interface ValueSpec {
  type: ValueType;
  required: boolean;
  title: string | null;
  description: string | null;
  default: JsonValue;
  enum: JsonValue[] | null;
  minimum: number | null;
  maximum: number | null;
}

export interface ExecutionTraits {
  timeout_ms: number;
  cancellable: boolean;
}

export interface ProgressSpec {
  mode: "none" | "stage" | "percent";
  source: "native" | "estimated" | null;
}

export interface CapabilityManifest {
  manifest_schema_version: 1;
  id: string;
  version: number;
  title: string;
  category: string;
  description: string | null;
  inputs: Record<string, ValueSpec>;
  outputs: Record<string, ValueSpec>;
  execution: ExecutionTraits;
  progress: ProgressSpec;
  resources: string[];
}

export interface RobotProfile {
  profile_schema_version: 1;
  id: string;
  title: string;
  adapter: string;
  capabilities: CapabilityRef[];
}

export type CompatibilityStatus =
  "compatible" | "missing" | "incompatible" | "unknown";
export interface CompatibilityNode {
  status: CompatibilityStatus;
  capability: CapabilityRef;
  reason: string;
}
export interface CompatibilityReport {
  active_profile_id: string;
  source_profile_id: string | null;
  compatible: boolean;
  nodes: Record<string, CompatibilityNode>;
}

export interface CapabilityRef {
  id: string;
  version: number;
}

export interface WaitNode {
  type: "wait";
  id: string;
  duration_ms: number;
}

export interface CapabilityNode {
  type: "capability";
  id: string;
  capability: CapabilityRef;
  args: Record<string, JsonValue>;
}

export interface SequenceNode {
  type: "sequence";
  id: string;
  children: WorkflowNode[];
}

export type WorkflowNode = WaitNode | CapabilityNode | SequenceNode;

export interface WorkflowDocument {
  workflow_schema_version: 1;
  id: string;
  name: string;
  workflow: WorkflowNode;
  profile_id?: string | null;
}

export interface EditorState {
  editor_state_version: number;
  type: "blockly";
  state: Record<string, unknown>;
}

export interface ProjectDocument {
  project_format_version: 1;
  name: string;
  editor: EditorState | null;
  workflow: WorkflowDocument;
}

export interface ValidationIssue {
  code: string;
  message: string;
  severity: "error" | "warning";
  node_id?: string | null;
  path?: string | null;
}

export interface ValidationReport {
  valid: boolean;
  issues: ValidationIssue[];
}

export type RunState =
  | "pending"
  | "running"
  | "canceling"
  | "succeeded"
  | "failed"
  | "canceled"
  | "timed_out";

export type ErrorCode =
  | "validation_error"
  | "unknown_capability"
  | "capability_failed"
  | "capability_timeout"
  | "adapter_contract_violation"
  | "cancellation_incomplete"
  | "internal_error";

export interface ExecutionError {
  code: ErrorCode;
  message: string;
  details: Record<string, JsonValue>;
}

export interface RunResult {
  run_id: string;
  workflow_id: string;
  state: RunState;
  error?: ExecutionError | null;
  started_at: string;
  finished_at: string;
}

export type EventType =
  | "run.started"
  | "run.cancel_requested"
  | "run.finished"
  | "node.started"
  | "node.cancel_requested"
  | "node.finished"
  | "capability.progress"
  | "log"
  | "error";

export interface RuntimeEvent {
  event_protocol_version: 1;
  event_id: string;
  seq: number;
  run_id: string;
  node_id?: string | null;
  type: EventType;
  occurred_at: string;
  data: Record<string, JsonValue>;
}

interface ToolboxBlock {
  kind: "block";
  type: string;
  fields?: Record<string, string>;
}

interface ToolboxCategory {
  kind: "category";
  name: string;
  categorystyle: string;
  contents: ToolboxBlock[];
}

export interface ToolboxDefinition {
  kind: "categoryToolbox";
  contents: ToolboxCategory[];
}

export function toolboxFromManifests(
  manifests: CapabilityManifest[],
  profileId?: string,
): ToolboxDefinition {
  const categories = new Map<string, CapabilityManifest[]>();
  for (const manifest of manifests) {
    const entries = categories.get(manifest.category) ?? [];
    entries.push(manifest);
    categories.set(manifest.category, entries);
  }

  const capabilityCategories = [...categories.entries()]
    .sort(([left], [right]) => left.localeCompare(right))
    .map(([name, entries]): ToolboxCategory => ({
      kind: "category",
      name,
      categorystyle: "roboarc_capability_category",
      contents: entries
        .filter(
          (manifest) =>
            !(
              (["reachy.arm.pose_joints", "reachy.arm.gesture"].includes(
                manifest.id,
              ) ||
                (profileId === "tiago-sim" &&
                  [
                    "navigation.goto_location",
                    "head.look_at",
                    "speech.say",
                    "navigation.stop",
                  ].includes(manifest.id))) &&
              manifest.version === 1
            ),
        )
        .sort((left, right) =>
          `${left.id}@${String(left.version)}`.localeCompare(
            `${right.id}@${String(right.version)}`,
          ),
        )
        .map((manifest) => ({
          kind: "block",
          type: "robo_capability",
          fields: {
            CAPABILITY: `${manifest.id}@${String(manifest.version)}`,
          },
        })),
    }))
    .filter((category) => category.contents.length > 0);

  const hasReachyArm = manifests.some(
    (manifest) =>
      manifest.id === "reachy.arm.gesture" && manifest.version === 1,
  );
  const tiagoBlocks =
    profileId === "tiago-sim"
      ? [
          ["navigation.goto_location", "tiago_goto_location"],
          ["head.look_at", "tiago_look_at"],
          ["speech.say", "tiago_say"],
          ["navigation.stop", "tiago_stop_navigation"],
        ]
          .filter(([id]) =>
            manifests.some(
              (manifest) => manifest.id === id && manifest.version === 1,
            ),
          )
          .map(([, type]) => ({ kind: "block" as const, type }))
      : [];
  return {
    kind: "categoryToolbox",
    contents: [
      {
        kind: "category",
        name: "Workflow",
        categorystyle: "roboarc_workflow_category",
        contents: [
          { kind: "block", type: "robo_sequence" },
          { kind: "block", type: "robo_wait" },
        ],
      },
      ...capabilityCategories,
      ...(hasReachyArm
        ? [
            {
              kind: "category" as const,
              name: "Reachy actions",
              categorystyle: "roboarc_capability_category",
              contents: [{ kind: "block" as const, type: "robo_action" }],
            },
          ]
        : []),
      ...(tiagoBlocks.length
        ? [
            {
              kind: "category" as const,
              name: "TIAGo actions",
              categorystyle: "roboarc_capability_category",
              contents: tiagoBlocks,
            },
          ]
        : []),
    ],
  };
}

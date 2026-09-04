import type {
  RunResult,
  RuntimeEvent,
  WorkflowDocument,
  WorkflowNode,
} from "./domain";
import { validateWorkflow } from "./validation";

export interface ReviewManifest {
  review_schema_version: 1;
  workflow: WorkflowDocument;
  result: RunResult;
  profile_id: string;
  observation_count: number;
  artifacts: { trace: string; rerun: string | null; video: string };
  timeline?: ReviewTimeline;
}

export interface ReviewTimeline {
  timebase: "utc";
  media: { id: string; artifact: string; origin: string }[];
}

export interface ReviewCatalogEntry {
  id: string;
  artifact_root: string;
  manifest: ReviewManifest | null;
  workflow: WorkflowDocument;
  profile_id: string | null;
  recorded: boolean;
}

export interface ReviewCatalogGroup {
  id: string;
  title: string;
  description: string;
  entries: ReviewCatalogEntry[];
}

const reviewGroupDefinitions: (Omit<ReviewCatalogGroup, "entries"> & {
  entryIds: string[];
})[] = [
  {
    id: "mock",
    title: "Mock / Deterministic Simulation",
    description:
      "Local, repeatable runs for checking workflow behavior without a robot.",
    entryIds: ["mock-demo", "simulation-observable"],
  },
  {
    id: "tiago",
    title: "TIAGo Gazebo",
    description:
      "Recorded task runs in the TIAGo Gazebo simulation environment.",
    entryIds: ["tiago-look-and-say", "tiago-proof-final", "tiago-observable"],
  },
  {
    id: "reachy",
    title: "Reachy 2 MuJoCo",
    description:
      "Recorded task runs in the Reachy 2 MuJoCo simulation environment.",
    entryIds: ["reachy-proof-final"],
  },
];

export function groupReviewCatalog(
  entries: ReviewCatalogEntry[],
): ReviewCatalogGroup[] {
  const assigned = new Set<string>();
  const groups: ReviewCatalogGroup[] = reviewGroupDefinitions
    .map(({ entryIds, ...definition }) => ({
      ...definition,
      entries: entries.filter((entry) => {
        if (!entryIds.includes(entry.id)) return false;
        assigned.add(entry.id);
        return true;
      }),
    }))
    .filter((group) => group.entries.length > 0);

  const unassigned = entries.filter((entry) => !assigned.has(entry.id));
  if (unassigned.length > 0) {
    groups.push({
      id: "other",
      title: "Other demos",
      description:
        "Additional workflow demos that are not assigned to a robot group yet.",
      entries: unassigned,
    });
  }
  return groups;
}

export function parseReviewCatalog(value: unknown): ReviewCatalogEntry[] {
  if (!Array.isArray(value)) throw new Error("Invalid review catalog");
  return value.map((entry) => {
    if (
      !isRecord(entry) ||
      typeof entry.id !== "string" ||
      !/^[A-Za-z0-9._-]+$/.test(entry.id) ||
      typeof entry.artifact_root !== "string" ||
      (entry.artifact_root !== "" &&
        !/^[A-Za-z0-9._-]+$/.test(entry.artifact_root))
    )
      throw new Error("Invalid review catalog entry");
    return {
      id: entry.id,
      artifact_root: entry.artifact_root,
      manifest:
        entry.manifest === null ? null : parseReviewManifest(entry.manifest),
      workflow: validateWorkflow(entry.workflow)
        ? (entry.workflow as unknown as WorkflowDocument)
        : (() => {
            throw new Error("Invalid review catalog workflow");
          })(),
      profile_id:
        typeof entry.profile_id === "string" ? entry.profile_id : null,
      recorded: entry.recorded === true,
    };
  });
}

export interface NodeInterval {
  nodeId: string;
  startMs: number;
  endMs: number;
}

export function parseTrace(value: unknown, runId: string): RuntimeEvent[] {
  if (!Array.isArray(value)) return [];
  return value.flatMap((event): RuntimeEvent[] => {
    if (!event || typeof event !== "object") return [];
    const item = event as Record<string, unknown>;
    if (item.run_id !== runId) return [];
    if (
      typeof item.type === "string" &&
      typeof item.occurred_at === "string" &&
      typeof item.seq === "number"
    )
      return [event as RuntimeEvent];
    if (typeof item.kind !== "string" || typeof item.timestamp !== "string")
      return [];
    return [
      {
        event_protocol_version: 1,
        event_id:
          typeof item.invocation_id === "string"
            ? item.invocation_id
            : `trace-${item.timestamp}`,
        seq: 1,
        run_id: runId,
        node_id: typeof item.node_id === "string" ? item.node_id : null,
        type: item.kind as RuntimeEvent["type"],
        occurred_at: item.timestamp,
        data: isRecord(item.data) ? (item.data as RuntimeEvent["data"]) : {},
      },
    ];
  });
}

export interface WorkflowStep {
  node: WorkflowNode;
  depth: number;
}

function isRecord(value: unknown): value is Record<string, unknown> {
  return value !== null && typeof value === "object" && !Array.isArray(value);
}

function artifactName(
  value: unknown,
  optional = false,
): value is string | null {
  if (optional && value === null) return true;
  return (
    typeof value === "string" &&
    value.length > 0 &&
    !value.startsWith("/") &&
    !value.split("/").includes("..")
  );
}

export function parseReviewManifest(value: unknown): ReviewManifest {
  if (!isRecord(value) || value.review_schema_version !== 1)
    throw new Error("Invalid review manifest");
  if (!validateWorkflow(value.workflow))
    throw new Error("Review manifest contains invalid Workflow IR");
  if (
    !isRecord(value.result) ||
    typeof value.result.run_id !== "string" ||
    typeof value.result.workflow_id !== "string" ||
    value.result.workflow_id !== value.workflow.id ||
    typeof value.result.state !== "string" ||
    typeof value.result.started_at !== "string" ||
    typeof value.result.finished_at !== "string"
  ) {
    throw new Error("Review manifest run does not match its workflow");
  }
  if (
    typeof value.profile_id !== "string" ||
    value.profile_id.length === 0 ||
    !Number.isSafeInteger(value.observation_count) ||
    (value.observation_count as number) < 0 ||
    !isRecord(value.artifacts) ||
    !artifactName(value.artifacts.trace) ||
    !artifactName(value.artifacts.rerun, true) ||
    !artifactName(value.artifacts.video)
  ) {
    throw new Error("Review manifest metadata is invalid");
  }
  if (value.timeline !== undefined) {
    if (
      !isRecord(value.timeline) ||
      value.timeline.timebase !== "utc" ||
      !Array.isArray(value.timeline.media)
    )
      throw new Error("Review manifest timeline is invalid");
    for (const media of value.timeline.media) {
      if (
        !isRecord(media) ||
        typeof media.id !== "string" ||
        typeof media.artifact !== "string" ||
        !artifactName(media.artifact) ||
        typeof media.origin !== "string" ||
        Number.isNaN(Date.parse(media.origin))
      )
        throw new Error("Review manifest timeline is invalid");
    }
  }
  return value as unknown as ReviewManifest;
}

export function nodeIntervals(
  events: RuntimeEvent[],
  runId: string,
  runStartedAt: string,
): NodeInterval[] {
  const origin = Date.parse(runStartedAt);
  if (!Number.isFinite(origin)) return [];
  const starts = new Map<string, number>();
  const intervals: NodeInterval[] = [];
  for (const event of events) {
    if (event.run_id !== runId || !event.node_id) continue;
    const elapsed = Date.parse(event.occurred_at) - origin;
    if (!Number.isFinite(elapsed)) continue;
    if (event.type === "node.started") starts.set(event.node_id, elapsed);
    if (event.type === "node.finished") {
      const start = starts.get(event.node_id);
      if (start !== undefined && elapsed >= start)
        intervals.push({
          nodeId: event.node_id,
          startMs: start,
          endMs: elapsed,
        });
      starts.delete(event.node_id);
    }
  }
  return intervals.sort((a, b) => a.startMs - b.startMs);
}

export function activeNodeAt(
  intervals: NodeInterval[],
  elapsedMs: number,
): string | null {
  const active = intervals.filter(
    ({ startMs, endMs }) => elapsedMs >= startMs && elapsedMs < endMs,
  );
  // Parent sequence intervals contain their children. Prefer the interval
  // that started latest so playback highlights the currently executing leaf.
  return (
    active.reduce<NodeInterval | null>(
      (selected, interval) =>
        !selected ||
        interval.startMs > selected.startMs ||
        (interval.startMs === selected.startMs &&
          interval.endMs < selected.endMs)
          ? interval
          : selected,
      null,
    )?.nodeId ?? null
  );
}

export function workflowSteps(workflow: WorkflowDocument): WorkflowStep[] {
  const steps: WorkflowStep[] = [];
  const visit = (node: WorkflowNode, depth: number): void => {
    steps.push({ node, depth });
    if (node.type === "sequence")
      for (const child of node.children) visit(child, depth + 1);
  };
  if (workflow.workflow.type === "sequence") {
    for (const child of workflow.workflow.children) visit(child, 0);
  } else visit(workflow.workflow, 0);
  return steps;
}

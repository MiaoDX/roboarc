import * as Blockly from "blockly/core";
import type { ISelectable } from "blockly/core";
import "blockly/blocks";
import {
  AlertCircle,
  Blocks,
  Check,
  ChevronDown,
  CircleStop,
  Download,
  FilePlus2,
  LoaderCircle,
  Play,
  Radio,
  Upload,
} from "lucide-react";
import React, {
  useCallback,
  useEffect,
  useMemo,
  useRef,
  useState,
} from "react";

import {
  cancelRun,
  discoverCapabilities,
  getCompatibility,
  getProfile,
  getEvents,
  getRun,
  startRun,
  validateRemote,
  websocketUrl,
} from "./api";
import {
  coerceArgument,
  defaultArguments,
  validateArguments,
} from "./arguments";
import {
  getCapabilityArguments,
  getCapabilityReference,
  registerBlocks,
  setCapabilityArgument,
} from "./blocks";
import {
  blockForNodeId,
  compileWorkspace,
  loadProject,
  saveProject,
  WorkflowDraftError,
} from "./compiler";
import { toolboxFromManifests } from "./domain";
import { reachyAction, REACHY_ACTIONS } from "./reachy-actions";
import { tiagoLookPreset } from "./tiago-actions";
import { createRoboArcTheme } from "./blockly-theme";
import type {
  CapabilityManifest,
  JsonValue,
  ProjectDocument,
  RuntimeEvent,
  ValidationReport,
  ValueSpec,
  WorkflowDocument,
} from "./domain";
import {
  elapsedMilliseconds,
  initialRuntimeView,
  reconnectDelay,
  reduceRuntimeEvent,
  type RuntimeView,
} from "./runtime";
import {
  validateProject,
  validateRuntimeEvent,
  validateWorkflow,
} from "./validation";

const terminalStates = new Set([
  "succeeded",
  "failed",
  "canceled",
  "timed_out",
]);

function displayValue(value: JsonValue | undefined, fallback = ""): string {
  if (value === undefined || value === null) return fallback;
  return typeof value === "object" ? JSON.stringify(value) : String(value);
}

function manifestKey(manifest: CapabilityManifest): string {
  return `${manifest.id}@${String(manifest.version)}`;
}

function localWorkflow(
  workspace: Blockly.WorkspaceSvg | null,
  name: string,
): WorkflowDocument {
  if (!workspace) throw new Error("Workspace is not ready.");
  const workflow = compileWorkspace(workspace, name.trim() || "Untitled");
  if (!validateWorkflow(workflow))
    throw new Error("Compiled Workflow IR does not match the local schema.");
  return workflow;
}

function useRuntimeStream(
  runId: string | null,
  onView: (view: RuntimeView) => void,
): RuntimeView {
  const [view, setView] = useState(initialRuntimeView);
  const viewRef = useRef(view);
  const onViewRef = useRef(onView);
  onViewRef.current = onView;
  useEffect(() => {
    viewRef.current = view;
    onViewRef.current(view);
  }, [view]);

  useEffect(() => {
    if (!runId) return;
    let stopped = false;
    let terminalObserved = false;
    let finishing = false;
    let cursor = 0;
    let socket: WebSocket | null = null;
    let timer: number | null = null;
    let attempt = 0;
    const resetView: RuntimeView = {
      ...initialRuntimeView,
      runId,
      runState: "running",
      connection: "connecting",
    };
    viewRef.current = resetView;
    setView(resetView);

    const accept = (event: RuntimeEvent): void => {
      if (event.run_id !== runId || event.seq <= cursor) return;
      cursor = event.seq;
      setView((current) => reduceRuntimeEvent(current, event));
    };
    const finish = async (): Promise<void> => {
      if (finishing) return;
      finishing = true;
      terminalObserved = true;
      socket?.close();
      try {
        const snapshot = await getRun(runId);
        if (!stopped) {
          setView((current) => ({
            ...current,
            connection: "idle",
            runState: snapshot.state,
            result: snapshot.result,
          }));
        }
      } catch {
        if (!stopped) {
          setView((current) => ({ ...current, connection: "offline" }));
        }
      }
    };
    const connect = async (): Promise<void> => {
      if (stopped || terminalObserved) return;
      setView((current) => ({
        ...current,
        connection: attempt ? "reconnecting" : "connecting",
      }));
      try {
        const replay = await getEvents(runId, cursor);
        replay.forEach(accept);
        if (replay.some((event) => event.type === "run.finished")) {
          await finish();
          return;
        }
        socket = new WebSocket(websocketUrl(runId, cursor));
        socket.onopen = () => {
          attempt = 0;
          setView((current) => ({ ...current, connection: "connected" }));
        };
        socket.onmessage = (message) => {
          try {
            const event: unknown = JSON.parse(String(message.data));
            if (!validateRuntimeEvent(event)) return;
            const runtimeEvent = event as unknown as RuntimeEvent;
            accept(runtimeEvent);
            if (runtimeEvent.type === "run.finished") void finish();
          } catch {
            /* malformed frames are ignored; HTTP replay remains authoritative */
          }
        };
        socket.onclose = () => {
          if (stopped || terminalObserved) return;
          timer = window.setTimeout(() => {
            attempt += 1;
            void connect();
          }, reconnectDelay(attempt));
        };
        socket.onerror = () => {
          socket?.close();
        };
      } catch {
        setView((current) => ({ ...current, connection: "offline" }));
        timer = window.setTimeout(() => {
          attempt += 1;
          void connect();
        }, reconnectDelay(attempt));
      }
    };
    void connect();
    return () => {
      stopped = true;
      socket?.close();
      if (timer !== null) window.clearTimeout(timer);
    };
  }, [runId]);
  return view;
}

function FieldEditor({
  name,
  spec,
  value,
  onChange,
  issue,
}: {
  name: string;
  spec: ValueSpec;
  value: JsonValue | undefined;
  onChange: (value: JsonValue | undefined) => void;
  issue?: string;
}) {
  const id = `arg-${name}`;
  const label = spec.title ?? name;
  const common = {
    id,
    "aria-invalid": Boolean(issue),
    "aria-describedby": `${id}-help`,
  };
  const commit = (raw: string | boolean): void => {
    try {
      onChange(coerceArgument(spec, raw));
    } catch {
      onChange(undefined);
    }
  };
  let control: React.ReactNode;
  if (spec.enum) {
    control = (
      <select
        {...common}
        value={displayValue(value)}
        onChange={(event) => {
          const selected = spec.enum?.find(
            (entry) => displayValue(entry) === event.target.value,
          );
          onChange(selected);
        }}
      >
        <option value="">Select</option>
        {spec.enum.map((entry) => (
          <option key={displayValue(entry)} value={displayValue(entry)}>
            {displayValue(entry)}
          </option>
        ))}
      </select>
    );
  } else if (spec.type === "boolean") {
    control = (
      <label className="checkbox-control">
        <input
          {...common}
          type="checkbox"
          checked={Boolean(value)}
          onChange={(event) => {
            commit(event.target.checked);
          }}
        />
        <span>{value ? "Enabled" : "Disabled"}</span>
      </label>
    );
  } else {
    const numeric = ["integer", "number", "duration_ms"].includes(spec.type);
    control = (
      <input
        {...common}
        type={numeric ? "number" : "text"}
        min={spec.minimum ?? undefined}
        max={spec.maximum ?? undefined}
        step={spec.type === "number" ? "any" : 1}
        value={displayValue(value)}
        onChange={(event) => {
          if (!event.target.value && !spec.required) onChange(undefined);
          else commit(event.target.value);
        }}
      />
    );
  }
  return (
    <div className="field">
      <label htmlFor={id}>{label}</label>
      {control}
      <span
        id={`${id}-help`}
        className={issue ? "field-help is-error" : "field-help"}
      >
        {issue ?? spec.description ?? " "}
      </span>
    </div>
  );
}

function Inspector({
  block,
  manifests,
  onEdit,
}: {
  block: Blockly.Block | null;
  manifests: CapabilityManifest[];
  onEdit: () => void;
}) {
  if (!block)
    return (
      <div className="empty-panel">
        <Blocks size={18} />
        <span>Select a block</span>
      </div>
    );
  if (block.type === "robo_wait")
    return (
      <section className="inspector-content">
        <div className="panel-kicker">Wait</div>
        <h2>Duration</h2>
        <div className="field">
          <label htmlFor="wait-duration">Milliseconds</label>
          <input
            id="wait-duration"
            type="number"
            min={0}
            max={86_400_000}
            step={1}
            value={String(block.getFieldValue("DURATION") ?? 0)}
            onChange={(event) => {
              block.setFieldValue(event.target.value, "DURATION");
              onEdit();
            }}
          />
          <span className="field-help">
            Runtime-native and immediately cancellable.
          </span>
        </div>
      </section>
    );
  if (block.type === "robo_sequence") {
    let count = 0;
    let child = block.getInputTargetBlock("CHILDREN");
    while (child) {
      count += 1;
      child = child.getNextBlock();
    }
    return (
      <section className="inspector-content">
        <div className="panel-kicker">Sequence</div>
        <h2>
          {count} {count === 1 ? "step" : "steps"}
        </h2>
        <p>Executes top to bottom and stops at the first unsuccessful child.</p>
      </section>
    );
  }
  if (block.type === "robo_action") {
    const action = String(block.getFieldValue("ACTION"));
    const metadata = REACHY_ACTIONS.find((item) => item.id === action);
    return (
      <section className="inspector-content">
        <div className="panel-kicker">Reachy action</div>
        <h2>{metadata?.label ?? reachyAction("home").label}</h2>
        <p>Semantic motion preset compiled to the Reachy arm pose contract.</p>
        <div className="metadata">
          <span>{String(block.getFieldValue("SIDE"))} arm</span>
          <span>{String(block.getFieldValue("DURATION"))} ms</span>
        </div>
      </section>
    );
  }
  if (block.type === "tiago_goto_location") {
    return (
      <section className="inspector-content">
        <div className="panel-kicker">TIAGo action</div>
        <h2>Go to</h2>
        <p>{String(block.getFieldValue("LOCATION"))}</p>
      </section>
    );
  }
  if (block.type === "tiago_look_at") {
    return (
      <section className="inspector-content">
        <div className="panel-kicker">TIAGo action</div>
        <h2>Look</h2>
        <p>
          {tiagoLookPreset(String(block.getFieldValue("TARGET")))?.label ??
            "target"}
        </p>
      </section>
    );
  }
  if (block.type === "tiago_say") {
    return (
      <section className="inspector-content">
        <div className="panel-kicker">TIAGo action</div>
        <h2>Say</h2>
        <p>{String(block.getFieldValue("TEXT"))}</p>
      </section>
    );
  }
  if (block.type === "tiago_stop_navigation") {
    return (
      <section className="inspector-content">
        <div className="panel-kicker">TIAGo control</div>
        <h2>Stop navigation</h2>
        <p>Navigation control action.</p>
      </section>
    );
  }
  if (block.type !== "robo_capability") return null;
  let reference;
  try {
    reference = getCapabilityReference(block);
  } catch {
    reference = null;
  }
  const manifest = manifests.find(
    (item) => item.id === reference?.id && item.version === reference.version,
  );
  if (!manifest)
    return (
      <section className="inspector-content">
        <div className="panel-kicker is-error">Unavailable</div>
        <h2>Unknown capability</h2>
        <p>
          The selected exact capability version is not in runtime discovery.
        </p>
      </section>
    );
  const args = {
    ...defaultArguments(manifest.inputs),
    ...getCapabilityArguments(block),
  };
  const issues = validateArguments(manifest.inputs, args);
  return (
    <section className="inspector-content">
      <div className="panel-kicker">{manifest.category}</div>
      <h2>{manifest.title}</h2>
      <p>{manifest.description ?? manifest.id}</p>
      <div className="metadata">
        <span>v{manifest.version}</span>
        <span>
          {manifest.execution.cancellable ? "Cancellable" : "Non-cancellable"}
        </span>
        <span>
          {manifest.progress.mode === "none"
            ? "No progress"
            : `${manifest.progress.mode} · ${manifest.progress.source ?? "unspecified"}`}
        </span>
      </div>
      <div className="inspector-fields">
        {Object.entries(manifest.inputs).map(([name, spec]) => (
          <FieldEditor
            key={name}
            name={name}
            spec={spec}
            value={args[name]}
            issue={issues.find((item) => item.name === name)?.message}
            onChange={(value) => {
              setCapabilityArgument(block, name, value);
              onEdit();
            }}
          />
        ))}
      </div>
      {Object.keys(manifest.inputs).length === 0 && (
        <p className="quiet">No arguments.</p>
      )}
    </section>
  );
}

function RuntimePanel({
  view,
  cancelPending,
  onCancel,
}: {
  view: RuntimeView;
  cancelPending: boolean;
  onCancel: () => void;
}) {
  const elapsed = elapsedMilliseconds(view.startedAt, view.finishedAt);
  const terminal = view.runState ? terminalStates.has(view.runState) : false;
  return (
    <section
      className="runtime-panel"
      aria-label="Runtime observation"
      data-testid="runtime-panel"
    >
      <div className="runtime-head">
        <div>
          <div className="panel-kicker">Runtime</div>
          <h2>{view.runState ?? "Not run"}</h2>
        </div>
        <span className={`connection is-${view.connection}`}>
          <Radio size={13} />
          {view.connection}
        </span>
      </div>
      <div className="runtime-stats">
        <div>
          <span>Run</span>
          <strong>{view.runId ?? "—"}</strong>
        </div>
        <div>
          <span>Active node</span>
          <strong>{view.activeNodeId ?? "—"}</strong>
        </div>
        <div>
          <span>{terminal ? "Duration" : "Elapsed"}</span>
          <strong>
            {elapsed === null ? "—" : `${(elapsed / 1000).toFixed(1)}s`}
          </strong>
        </div>
      </div>
      {view.progress && (
        <div className="progress-readout">
          <span>
            {displayValue(
              view.progress.stage ?? view.progress.message,
              "Progress",
            )}
          </span>
          {typeof view.progress.percent === "number" && (
            <>
              <progress max={100} value={view.progress.percent} />
              <strong>{view.progress.percent}%</strong>
            </>
          )}
          <small>
            {view.progress.source
              ? `${displayValue(view.progress.source)} provenance`
              : "Stage only"}
          </small>
        </div>
      )}
      {view.errors.map((error, index) => (
        <div
          className="runtime-error"
          key={`${error.code}-${String(index)}`}
          data-testid="runtime-error"
        >
          <AlertCircle size={16} />
          <div>
            <strong>{error.code}</strong>
            <p>{error.message}</p>
          </div>
        </div>
      ))}
      <div className="log-list" aria-label="Structured logs">
        {view.logs.length ? (
          view.logs.map((event) => (
            <div className="log-line" key={event.event_id}>
              <time>{new Date(event.occurred_at).toLocaleTimeString()}</time>
              <strong>{displayValue(event.data.level, "info")}</strong>
              <span>{displayValue(event.data.message)}</span>
            </div>
          ))
        ) : (
          <div className="empty-log">No runtime logs</div>
        )}
      </div>
      {view.result && (
        <pre className="result-output" data-testid="terminal-result">
          {JSON.stringify(view.result, null, 2)}
        </pre>
      )}
      <button
        className="button danger runtime-stop"
        onClick={onCancel}
        disabled={!view.runId || terminal || cancelPending}
        aria-label="Stop active run"
      >
        {cancelPending ? (
          <LoaderCircle className="spin" size={16} />
        ) : (
          <CircleStop size={16} />
        )}
        {cancelPending
          ? "Requesting"
          : view.runState === "canceling"
            ? "Canceling"
            : "Stop"}
      </button>
    </section>
  );
}

export default function App() {
  const workspaceHost = useRef<HTMLDivElement>(null);
  const workspaceRef = useRef<Blockly.WorkspaceSvg | null>(null);
  const loadInput = useRef<HTMLInputElement>(null);
  const [projectName, setProjectName] = useState("Untitled workflow");
  const [manifests, setManifests] = useState<CapabilityManifest[]>([]);
  const [profile, setProfile] = useState<{ id: string; title: string } | null>(
    null,
  );
  const [compatibility, setCompatibility] = useState<
    import("./domain").CompatibilityReport | null
  >(null);
  const [discovery, setDiscovery] = useState<
    "loading" | "ready" | "offline" | "error"
  >("loading");
  const [discoveryError, setDiscoveryError] = useState<string | null>(null);
  const [selected, setSelected] = useState<Blockly.Block | null>(null);
  const [revision, setRevision] = useState(0);
  const [report, setReport] = useState<ValidationReport | null>(null);
  const [actionError, setActionError] = useState<string | null>(null);
  const [busy, setBusy] = useState<"validate" | "run" | "cancel" | null>(null);
  const [runId, setRunId] = useState<string | null>(null);
  const [panelWidth, setPanelWidth] = useState(340);
  const runtimeView = useRuntimeStream(runId, (view) => {
    const workspace = workspaceRef.current;
    if (workspace)
      workspace.highlightBlock(
        view.activeNodeId
          ? (blockForNodeId(workspace, view.activeNodeId)?.id ?? null)
          : null,
      );
  });

  const manifestMap = useMemo(
    () => new Map(manifests.map((item) => [manifestKey(item), item])),
    [manifests],
  );
  const compile = useCallback(
    () => localWorkflow(workspaceRef.current, projectName),
    [projectName],
  );
  const localCheck = useCallback((): WorkflowDocument => {
    const workflow = compile();
    const stack = [workflow.workflow];
    while (stack.length) {
      const node = stack.pop();
      if (!node) continue;
      if (node.type === "sequence") stack.push(...node.children);
      if (node.type === "capability") {
        const manifest = manifestMap.get(
          `${node.capability.id}@${String(node.capability.version)}`,
        );
        if (!manifest)
          throw new Error(
            `Capability ${node.capability.id}@${String(node.capability.version)} is unavailable.`,
          );
        const issues = validateArguments(manifest.inputs, {
          ...defaultArguments(manifest.inputs),
          ...node.args,
        });
        if (issues.length)
          throw new Error(issues.map((issue) => issue.message).join(" "));
      }
    }
    return { ...workflow, profile_id: profile?.id ?? null };
  }, [compile, manifestMap, profile]);

  useEffect(() => {
    registerBlocks();
    let active = true;
    getProfile()
      .then((activeProfile) => {
        if (!active) return;
        setProfile(activeProfile);
        return discoverCapabilities().then((items) => {
          const allowed = new Set(
            activeProfile.capabilities.map(
              (capability) => `${capability.id}@${String(capability.version)}`,
            ),
          );
          return items.filter((item) => allowed.has(manifestKey(item)));
        });
      })
      .then((items) => {
        if (!items) return;
        if (active) {
          setManifests(items);
          setDiscovery("ready");
        }
      })
      .catch((error: unknown) => {
        if (active) {
          setDiscovery(navigator.onLine ? "error" : "offline");
          setDiscoveryError(
            error instanceof Error ? error.message : "Discovery failed.",
          );
        }
      });
    return () => {
      active = false;
    };
  }, []);

  useEffect(() => {
    if (!workspaceHost.current || discovery !== "ready") return;
    const workspace = Blockly.inject(workspaceHost.current, {
      toolbox: toolboxFromManifests(
        manifests,
        profile?.id,
      ) as Blockly.utils.toolbox.ToolboxDefinition,
      renderer: "zelos",
      trashcan: true,
      zoom: {
        controls: true,
        wheel: true,
        startScale: 0.9,
        minScale: 0.5,
        maxScale: 1.5,
      },
      move: { scrollbars: true, drag: true, wheel: true },
      grid: { spacing: 24, length: 2, colour: "var(--color-grid)", snap: true },
      theme: createRoboArcTheme(),
    });
    workspaceRef.current = workspace;
    if (workspace.getTopBlocks(false).length === 0) {
      const sequence = workspace.newBlock("robo_sequence");
      sequence.initSvg();
      sequence.render();
      sequence.moveBy(64, 48);
      Blockly.common.setSelected(sequence);
    }
    const listener = (event: Blockly.Events.Abstract) => {
      if (event.type === "selected")
        setSelected(
          workspace.getBlockById(
            (event as Blockly.Events.Selected).newElementId ?? "",
          ),
        );
      if (
        !new Set<string>([
          Blockly.Events.UI,
          Blockly.Events.VIEWPORT_CHANGE,
          Blockly.Events.TOOLBOX_ITEM_SELECT,
        ]).has(event.type)
      ) {
        setRevision((value) => value + 1);
        setReport(null);
        setCompatibility(null);
      }
    };
    workspace.addChangeListener(listener);
    const resize = () => {
      Blockly.svgResize(workspace);
    };
    const observer = new ResizeObserver(resize);
    observer.observe(workspaceHost.current);
    resize();
    return () => {
      observer.disconnect();
      workspace.removeChangeListener(listener);
      workspace.dispose();
      workspaceRef.current = null;
    };
  }, [discovery, manifests]);

  const compilation = useMemo(() => {
    try {
      return { ir: compile(), issue: null, draft: false };
    } catch (error) {
      const draft = error instanceof WorkflowDraftError;
      return {
        ir: null,
        issue: draft
          ? error.message
          : "Connect exactly one valid root workflow.",
        draft,
      };
    }
  }, [compile, revision]);
  const { ir } = compilation;
  const newProject = () => {
    const workspace = workspaceRef.current;
    if (!workspace) return;
    workspace.clear();
    const sequence = workspace.newBlock("robo_sequence");
    sequence.initSvg();
    sequence.render();
    sequence.moveBy(64, 48);
    setProjectName("Untitled workflow");
    setActionError(null);
    setReport(null);
    setCompatibility(null);
  };
  const save = () => {
    try {
      const workspace = workspaceRef.current;
      if (!workspace) throw new Error("Workspace is not ready.");
      const project = saveProject(
        workspace,
        projectName.trim() || "Untitled workflow",
      );
      const blob = new Blob([JSON.stringify(project, null, 2)], {
        type: "application/json",
      });
      const url = URL.createObjectURL(blob);
      const anchor = document.createElement("a");
      anchor.href = url;
      anchor.download = `${project.name.replace(/[^a-z0-9_-]+/gi, "-").toLowerCase() || "workflow"}.roboarc.json`;
      anchor.click();
      URL.revokeObjectURL(url);
      setActionError(null);
    } catch (error) {
      setActionError(error instanceof Error ? error.message : "Save failed.");
    }
  };
  const load = async (file: File) => {
    try {
      const value: unknown = JSON.parse(await file.text());
      if (!validateProject(value))
        throw new Error("File does not match the RoboArc project schema.");
      const project = value as unknown as ProjectDocument;
      const workspace = workspaceRef.current;
      if (!workspace) throw new Error("Workspace is not ready.");
      loadProject(project, workspace);
      setProjectName(project.name);
      setActionError(null);
      setReport(null);
      setCompatibility(null);
    } catch (error) {
      setActionError(error instanceof Error ? error.message : "Load failed.");
    } finally {
      if (loadInput.current) loadInput.current.value = "";
    }
  };
  const validate = async () => {
    setBusy("validate");
    setActionError(null);
    try {
      const workflow = localCheck();
      const [remoteReport, compatibilityReport] = await Promise.all([
        validateRemote(workflow),
        getCompatibility(workflow),
      ]);
      setReport(remoteReport);
      setCompatibility(compatibilityReport);
    } catch (error) {
      setActionError(
        error instanceof Error ? error.message : "Validation failed.",
      );
    } finally {
      setBusy(null);
    }
  };
  const run = async () => {
    setBusy("run");
    setActionError(null);
    try {
      const workflow = localCheck();
      const report = await getCompatibility(workflow);
      setCompatibility(report);
      const blocked = Object.entries(report.nodes).find(
        ([, node]) => node.status !== "compatible",
      );
      if (blocked) {
        throw new Error(
          `Node ${blocked[0]} is ${blocked[1].status}: ${blocked[1].reason}`,
        );
      }
      const response = await startRun(workflow);
      setRunId(response.run_id);
    } catch (error) {
      setActionError(error instanceof Error ? error.message : "Run failed.");
    } finally {
      setBusy(null);
    }
  };
  const stop = async () => {
    if (!runId) return;
    setBusy("cancel");
    setActionError(null);
    try {
      const response = await cancelRun(runId);
      if (!response.accepted && !terminalStates.has(response.state))
        setActionError(
          "Cancellation request was not accepted. Runtime observation continues.",
        );
    } catch (error) {
      setActionError(
        error instanceof Error ? error.message : "Cancellation request failed.",
      );
    } finally {
      setBusy(null);
    }
  };
  const dragSplitter = (event: React.PointerEvent) => {
    const start = event.clientX;
    const initial = panelWidth;
    event.currentTarget.setPointerCapture(event.pointerId);
    const move = (moveEvent: PointerEvent) => {
      setPanelWidth(
        Math.min(520, Math.max(260, initial + start - moveEvent.clientX)),
      );
    };
    const end = () => {
      window.removeEventListener("pointermove", move);
      window.removeEventListener("pointerup", end);
    };
    window.addEventListener("pointermove", move);
    window.addEventListener("pointerup", end);
  };

  return (
    <div
      className="app-shell"
      style={
        { "--panel-width": `${String(panelWidth)}px` } as React.CSSProperties
      }
    >
      <header className="product-header">
        <div className="brand">
          <Blocks size={20} aria-hidden="true" />
          <strong>RoboArc</strong>
          <span>Workbench</span>
        </div>
        <label className="project-name">
          <span className="sr-only">Project name</span>
          <input
            aria-label="Project name"
            value={projectName}
            onChange={(event) => {
              setProjectName(event.target.value);
            }}
          />
        </label>
        <div className="header-actions">
          <button
            className="icon-button"
            onClick={newProject}
            aria-label="New project"
            title="New project"
          >
            <FilePlus2 size={17} />
          </button>
          <button
            className="icon-button"
            onClick={save}
            aria-label="Download project"
            title="Save project"
          >
            <Download size={17} />
          </button>
          <button
            className="icon-button"
            onClick={() => loadInput.current?.click()}
            aria-label="Load project"
            title="Load project"
          >
            <Upload size={17} />
          </button>
          <input
            ref={loadInput}
            className="sr-only"
            type="file"
            accept="application/json,.json"
            onChange={(event) => {
              const file = event.target.files?.[0];
              if (file) void load(file);
            }}
            data-testid="project-file-input"
          />
          <span className={`discovery is-${discovery}`}>
            {discovery === "loading" && (
              <LoaderCircle className="spin" size={14} />
            )}
            {discovery === "ready" && <Check size={14} />}
            {(discovery === "offline" || discovery === "error") && (
              <AlertCircle size={14} />
            )}
            {discovery}
          </span>
          {profile && (
            <span className="profile-badge" data-testid="active-profile">
              {profile.title} ({profile.id})
            </span>
          )}
          <button
            className="button secondary"
            onClick={() => void validate()}
            disabled={discovery !== "ready" || busy !== null}
          >
            {busy === "validate" ? (
              <LoaderCircle className="spin" size={16} />
            ) : (
              <Check size={16} />
            )}
            Validate
          </button>
          <button
            className="button primary"
            onClick={() => void run()}
            disabled={discovery !== "ready" || busy !== null}
          >
            {busy === "run" ? (
              <LoaderCircle className="spin" size={16} />
            ) : (
              <Play size={16} />
            )}
            Run
          </button>
        </div>
      </header>
      {(actionError ?? discoveryError) && (
        <div className="status-banner is-error" role="alert">
          <AlertCircle size={16} />
          <span>{actionError ?? discoveryError}</span>
        </div>
      )}
      {compatibility && (
        <div className="status-banner" data-testid="compatibility-report">
          {Object.entries(compatibility.nodes).map(([nodeId, node]) => (
            <span key={nodeId} data-testid={`compatibility-${nodeId}`}>
              {nodeId}: {node.status} ({node.reason})
            </span>
          ))}
        </div>
      )}
      <main className="workbench">
        <section className="authoring-pane" aria-label="Workflow authoring">
          <div
            className="workspace"
            ref={workspaceHost}
            data-testid="blockly-workspace"
          >
            {discovery === "loading" && (
              <div className="workspace-loading">
                <LoaderCircle className="spin" />
                Loading capabilities
              </div>
            )}
            {(discovery === "offline" || discovery === "error") && (
              <div className="workspace-loading">
                <AlertCircle />
                Runtime unavailable
              </div>
            )}
          </div>
          <aside className="inspector" aria-label="Selected block inspector">
            <Inspector
              block={selected}
              manifests={manifests}
              onEdit={() => {
                setRevision((value) => value + 1);
              }}
            />
          </aside>
        </section>
        <div
          className="splitter"
          role="separator"
          aria-label="Resize runtime panel"
          aria-orientation="vertical"
          onPointerDown={dragSplitter}
        />
        <RuntimePanel
          view={runtimeView}
          cancelPending={busy === "cancel"}
          onCancel={() => void stop()}
        />
      </main>
      <section className="ir-drawer">
        <details>
          <summary>
            <span>Workflow IR</span>
            {ir ? (
              <span className="validity is-valid">
                <Check size={13} />
                Local schema valid
              </span>
            ) : compilation.draft ? (
              <span className="validity">Draft · Add a step</span>
            ) : (
              <span className="validity is-error">
                <AlertCircle size={13} />
                Incomplete
              </span>
            )}
            <ChevronDown size={15} />
          </summary>
          <div className="ir-content">
            <pre data-testid="workflow-ir">
              {ir ? JSON.stringify(ir, null, 2) : compilation.issue}
            </pre>
            <div className="validation-report" data-testid="validation-report">
              <div className="panel-kicker">Validation</div>
              {report ? (
                report.issues.length ? (
                  report.issues.map((issue, index) => (
                    <button
                      key={`${issue.code}-${String(index)}`}
                      onClick={() => {
                        const workspace = workspaceRef.current;
                        if (issue.node_id && workspace) {
                          const block = blockForNodeId(
                            workspace,
                            issue.node_id,
                          );
                          if (block) {
                            Blockly.common.setSelected(
                              block as unknown as ISelectable,
                            );
                          }
                        }
                      }}
                    >
                      <AlertCircle size={14} />
                      <span>
                        <strong>{issue.code}</strong>
                        {issue.message}
                      </span>
                    </button>
                  ))
                ) : (
                  <p className="validation-success">
                    <Check size={15} />
                    Backend validation passed.
                  </p>
                )
              ) : (
                <p>No backend report yet.</p>
              )}
            </div>
          </div>
        </details>
      </section>
    </div>
  );
}

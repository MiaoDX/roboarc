import * as Blockly from "blockly/core";
import "blockly/blocks";
import {
  Blocks,
  CheckCircle2,
  Clock3,
  ExternalLink,
  ListTree,
} from "lucide-react";
import React from "react";

import { registerBlocks } from "./blocks";
import { createRoboArcTheme } from "./blockly-theme";
import { blockForNodeId, loadWorkflow } from "./compiler";
import type { WorkflowNode } from "./domain";
import {
  activeNodeAt,
  nodeIntervals,
  parseTrace,
  parseReviewManifest,
  workflowSteps,
} from "./review";
import type { ReviewManifest } from "./review";
import "./review.css";
import "./review-blockly.css";

const artifactRoot = "/artifacts";

function nodeSummary(node: WorkflowNode): { label: string; detail: string } {
  if (node.type === "capability")
    return {
      label: `${node.capability.id}@${String(node.capability.version)}`,
      detail: JSON.stringify(node.args),
    };
  if (node.type === "wait")
    return { label: "wait", detail: `${String(node.duration_ms)} ms` };
  return {
    label: "sequence",
    detail: `${String(node.children.length)} children`,
  };
}

export default function ReviewApp() {
  const blockHost = React.useRef<HTMLDivElement>(null);
  const videoRef = React.useRef<HTMLVideoElement>(null);
  const workspaceRef = React.useRef<Blockly.WorkspaceSvg | null>(null);
  const [manifest, setManifest] = React.useState<ReviewManifest | null>(null);
  const [error, setError] = React.useState<string | null>(null);
  const [intervals, setIntervals] = React.useState<
    ReturnType<typeof nodeIntervals>
  >([]);

  React.useEffect(() => {
    fetch(`${artifactRoot}/review.json`, { cache: "no-store" })
      .then(async (response) => {
        if (!response.ok)
          throw new Error(
            `Review manifest returned ${String(response.status)}`,
          );
        return parseReviewManifest(await response.json());
      })
      .then(setManifest)
      .catch((reason: unknown) => {
        setError(
          reason instanceof Error
            ? reason.message
            : "Review manifest unavailable",
        );
      });
  }, []);

  React.useEffect(() => {
    if (!manifest) return;
    fetch(
      `${artifactRoot}/${manifest.artifacts.trace}?run=${encodeURIComponent(manifest.result.run_id)}`,
      { cache: "no-store" },
    )
      .then((response) => {
        if (!response.ok)
          throw new Error(`Trace returned ${String(response.status)}`);
        return response.text();
      })
      .then((text) => {
        const events = parseTrace(
          text
            .split("\n")
            .filter(Boolean)
            .map((line): unknown => JSON.parse(line) as unknown),
          manifest.result.run_id,
        );
        setIntervals(
          nodeIntervals(
            events,
            manifest.result.run_id,
            manifest.result.started_at,
          ),
        );
      })
      .catch(() => {
        setIntervals([]);
      });
  }, [manifest]);

  React.useEffect(() => {
    if (!blockHost.current || !manifest) return;
    registerBlocks();
    const workspace = Blockly.inject(blockHost.current, {
      readOnly: true,
      trashcan: false,
      zoom: { controls: true, wheel: true },
      grid: { spacing: 24, length: 2, colour: "#d9e1e8" },
      theme: createRoboArcTheme(),
    });
    loadWorkflow(manifest.workflow, workspace);
    workspaceRef.current = workspace;
    workspace.zoomToFit();
    return () => {
      workspace.dispose();
      workspaceRef.current = null;
    };
  }, [manifest]);

  React.useEffect(() => {
    const video = videoRef.current;
    const media = manifest?.timeline?.media.find(
      (item) => item.artifact === manifest.artifacts.video,
    );
    if (!video || !manifest || !media || !intervals.length) return;
    const update = () => {
      const elapsed =
        Date.parse(media.origin) +
        video.currentTime * 1000 -
        Date.parse(manifest.result.started_at);
      const nodeId = activeNodeAt(intervals, elapsed);
      workspaceRef.current?.highlightBlock(
        nodeId
          ? (blockForNodeId(workspaceRef.current, nodeId)?.id ?? null)
          : null,
      );
    };
    video.addEventListener("timeupdate", update);
    video.addEventListener("seeked", update);
    video.addEventListener("loadedmetadata", update);
    return () => {
      video.removeEventListener("timeupdate", update);
      video.removeEventListener("seeked", update);
      video.removeEventListener("loadedmetadata", update);
    };
  }, [manifest, intervals]);

  if (error) return <main className="review-unavailable">{error}</main>;
  if (!manifest)
    return (
      <main className="review-unavailable">Loading review manifest...</main>
    );
  const steps = workflowSteps(manifest.workflow);
  // Artifacts keep stable filenames for simple serving, so scope browser
  // cache entries to the run that produced them.
  const artifact = (name: string) =>
    `${artifactRoot}/${name}?run=${encodeURIComponent(manifest.result.run_id)}`;

  return (
    <main className="review-shell">
      <header className="review-header">
        <div className="review-brand">
          <Blocks size={21} />
          <strong>RoboArc</strong>
          <span>Workflow visual review</span>
        </div>
        <a href="/" className="review-link">
          Open Workbench <ExternalLink size={15} />
        </a>
      </header>
      <section className="review-hero">
        <div>
          <div className="review-kicker">Workflow · {manifest.workflow.id}</div>
          <h1>{manifest.workflow.name}</h1>
          <p>
            Canonical Workflow IR, rendered as Blockly, with artifacts from the
            same run.
          </p>
          <div className="review-status">
            <CheckCircle2 size={16} /> {manifest.result.state}
            <span>·</span>
            {manifest.observation_count.toLocaleString()} observations
          </div>
        </div>
        <a
          className="artifact-button"
          href={artifact(manifest.artifacts.video)}
          target="_blank"
          rel="noreferrer"
        >
          Open MP4 <ExternalLink size={15} />
        </a>
      </section>
      <section className="review-grid">
        <div className="workflow-panel">
          <div className="panel-heading">
            <div>
              <span className="review-kicker">Workflow IR → Blockly</span>
              <h2>Workflow · {steps.length} steps</h2>
            </div>
            <span className="ir-badge">canonical</span>
          </div>
          <div className="blockly-review" ref={blockHost} />
          <div className="step-list">
            {steps.map(({ node, depth }, index) => {
              const summary = nodeSummary(node);
              const NodeIcon =
                node.type === "wait"
                  ? Clock3
                  : node.type === "sequence"
                    ? ListTree
                    : CheckCircle2;
              return (
                <article
                  className="workflow-step"
                  key={node.id}
                  style={{ paddingLeft: `${String(depth * 18)}px` }}
                >
                  <div className="step-index">{index + 1}</div>
                  <NodeIcon size={19} className="step-icon" />
                  <div>
                    <h3>{node.id}</h3>
                    <code>{summary.label}</code>
                    <p>{summary.detail}</p>
                  </div>
                </article>
              );
            })}
          </div>
        </div>
        <aside className="review-side">
          <section className="video-panel">
            <div className="panel-heading">
              <div>
                <span className="review-kicker">Simulation recording</span>
                <h2>Recorded execution</h2>
              </div>
              <span className="video-meta">H.264 · 1600 × 900</span>
            </div>
            <video
              ref={videoRef}
              controls
              preload="metadata"
              src={artifact(manifest.artifacts.video)}
            />
          </section>
          <div className="run-panel">
            <div className="panel-heading">
              <div>
                <span className="review-kicker">Runtime result</span>
                <h2>Completed run</h2>
              </div>
              <span className="success-dot" />
            </div>
            <dl>
              <div>
                <dt>Profile</dt>
                <dd>{manifest.profile_id}</dd>
              </div>
              <div>
                <dt>Run ID</dt>
                <dd className="mono">{manifest.result.run_id}</dd>
              </div>
              <div>
                <dt>Artifacts</dt>
                <dd>
                  <a href={artifact(manifest.artifacts.trace)}>JSONL</a>
                  {manifest.artifacts.rerun && (
                    <>
                      <span> · </span>
                      <a href={artifact(manifest.artifacts.rerun)}>Rerun RRD</a>
                    </>
                  )}
                </dd>
              </div>
            </dl>
          </div>
        </aside>
      </section>
    </main>
  );
}

import { ArrowRight, Blocks, CheckCircle2, ExternalLink } from "lucide-react";
import React from "react";

import {
  groupReviewCatalog,
  parseReviewCatalog,
  type ReviewCatalogEntry,
  workflowSteps,
} from "./review";
import "./review.css";

const artifactsBase = "./artifacts";
const isStaticReview =
  typeof document !== "undefined" &&
  document.querySelector('meta[name="roboarc-default-view"]') !== null;

const artifactUrl = (entry: ReviewCatalogEntry, name: string) => {
  if (!entry.manifest) return "";
  const root = entry.artifact_root
    ? `${artifactsBase}/${entry.artifact_root}`
    : artifactsBase;
  return `${root}/${name}?run=${encodeURIComponent(entry.manifest.result.run_id)}`;
};

export default function ReviewCatalog() {
  const [reviews, setReviews] = React.useState<ReviewCatalogEntry[] | null>(
    null,
  );
  const [error, setError] = React.useState<string | null>(null);

  React.useEffect(() => {
    fetch(`${artifactsBase}/reviews.json`, { cache: "no-store" })
      .then(async (response) => {
        if (!response.ok)
          throw new Error(`Review catalog returned ${String(response.status)}`);
        return parseReviewCatalog(await response.json());
      })
      .then(setReviews)
      .catch((reason: unknown) => {
        setError(
          reason instanceof Error
            ? reason.message
            : "Review catalog unavailable",
        );
      });
  }, []);

  if (error) return <main className="review-unavailable">{error}</main>;
  if (!reviews)
    return <main className="review-unavailable">Loading demos...</main>;

  const groups = groupReviewCatalog(reviews);

  return (
    <main className="review-shell demo-catalog-shell">
      <header className="review-header">
        <div className="review-brand">
          <Blocks size={21} />
          <strong>RoboArc</strong>
          <span>Recorded demos</span>
        </div>
        {!isStaticReview && (
          <a href="./" className="review-link">
            Open Workbench <ExternalLink size={15} />
          </a>
        )}
      </header>
      <section className="catalog-heading">
        <div className="review-kicker">Simulation review library</div>
        <h1>Robot task demos</h1>
        <p>
          {reviews.length} demos. Recorded runs include matching workflow,
          trace, result, and video.
        </p>
      </section>
      {groups.map((group) => (
        <section className="catalog-group" key={group.id}>
          <div className="catalog-group-heading">
            <div>
              <div className="review-kicker">Demo group</div>
              <h2>{group.title}</h2>
              <p>{group.description}</p>
            </div>
            <span className="catalog-group-count">
              {group.entries.length}{" "}
              {group.entries.length === 1 ? "demo" : "demos"}
            </span>
          </div>
          <div className="demo-grid" aria-label={`${group.title} demos`}>
            {group.entries.map((entry) => {
              const { manifest } = entry;
              const href = manifest
                ? `?review=${encodeURIComponent(entry.id)}`
                : "/";
              const steps = workflowSteps(entry.workflow);
              return (
                <article className="demo-card" key={entry.id}>
                  <a className="demo-media" href={href}>
                    {manifest ? (
                      <video
                        muted
                        playsInline
                        preload="metadata"
                        src={artifactUrl(entry, manifest.artifacts.video)}
                      />
                    ) : (
                      <div className="demo-placeholder">
                        <Blocks size={38} />
                        <span>Workflow fixture</span>
                      </div>
                    )}
                    <span className="demo-profile">
                      {entry.profile_id ?? "mock"}
                    </span>
                  </a>
                  <div className="demo-card-body">
                    <div
                      className={`demo-state${manifest ? "" : " is-fixture"}`}
                    >
                      {manifest && <CheckCircle2 size={15} />}
                      {manifest
                        ? manifest.result.state
                        : "Available in Workbench"}
                      <span>
                        {manifest
                          ? `${manifest.observation_count.toLocaleString()} observations`
                          : `${String(steps.length)} workflow steps`}
                      </span>
                    </div>
                    <h2>{entry.workflow.name}</h2>
                    <p>{entry.workflow.id}</p>
                    <a className="demo-open" href={href}>
                      {manifest ? "Review run" : "Open Workbench"}{" "}
                      <ArrowRight size={16} />
                    </a>
                  </div>
                </article>
              );
            })}
          </div>
        </section>
      ))}
    </main>
  );
}

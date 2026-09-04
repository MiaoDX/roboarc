#!/usr/bin/env python3
"""Validate a manifest-backed RoboArc review artifact directory."""

from __future__ import annotations

import argparse
import json
import shutil
import subprocess
import sys
from datetime import datetime
from pathlib import Path
from typing import Any

from roboarc.contracts import WorkflowDocument


class ReviewArtifactError(ValueError):
    """Raised when a review artifact set is incomplete or inconsistent."""


def _record(value: Any) -> dict[str, Any]:
    if not isinstance(value, dict):
        raise ReviewArtifactError("trace record must be an object")
    return value


def _artifact_path(root: Path, name: Any, field: str) -> Path:
    if not isinstance(name, str) or not name or Path(name).is_absolute():
        raise ReviewArtifactError(f"{field} must be a relative filename")
    path = (root / name).resolve()
    if root.resolve() not in path.parents:
        raise ReviewArtifactError(f"{field} escapes the artifact directory")
    if not path.is_file():
        raise ReviewArtifactError(f"{field} does not exist: {name}")
    return path


def _node_ids(node: dict[str, Any]) -> set[str]:
    node_id = node.get("id")
    if not isinstance(node_id, str) or not node_id:
        raise ReviewArtifactError("workflow node has no stable id")
    ids = {node_id}
    if node.get("type") == "sequence":
        children = node.get("children")
        if not isinstance(children, list):
            raise ReviewArtifactError(f"sequence node {node_id} has invalid children")
        for child in children:
            if not isinstance(child, dict):
                raise ReviewArtifactError(f"sequence node {node_id} has invalid child")
            ids.update(_node_ids(child))
    return ids


def _event_fields(event: dict[str, Any]) -> tuple[str | None, str | None, str | None]:
    run_id = event.get("run_id")
    node_id = event.get("node_id")
    kind = event.get("kind", event.get("type"))
    if not isinstance(run_id, str) or not isinstance(kind, str):
        raise ReviewArtifactError("trace records require run_id and kind/type")
    if node_id is not None and not isinstance(node_id, str):
        raise ReviewArtifactError("trace node_id must be a string or null")
    return run_id, node_id, kind


def _check_trace(path: Path, run_id: str, node_ids: set[str]) -> int:
    starts: set[str] = set()
    started_nodes: set[str] = set()
    finished_nodes: set[str] = set()
    saw_started = False
    saw_finished = False
    count = 0
    for line_number, line in enumerate(path.read_text(encoding="utf-8").splitlines(), 1):
        if not line.strip():
            continue
        try:
            event = _record(json.loads(line))
        except json.JSONDecodeError as error:
            raise ReviewArtifactError(f"invalid JSON in trace line {line_number}") from error
        event_run, node_id, kind = _event_fields(event)
        if event_run != run_id:
            raise ReviewArtifactError(f"trace line {line_number} has a different run_id")
        if node_id is not None and node_id not in node_ids:
            raise ReviewArtifactError(f"trace line {line_number} names unknown node {node_id}")
        timestamp = event.get("timestamp", event.get("occurred_at"))
        if not isinstance(timestamp, str):
            raise ReviewArtifactError(f"trace line {line_number} has no timestamp")
        try:
            datetime.fromisoformat(timestamp.replace("Z", "+00:00"))
        except ValueError as error:
            raise ReviewArtifactError(f"trace line {line_number} has invalid timestamp") from error
        count += 1
        if kind == "run.started":
            saw_started = True
        elif kind == "run.finished":
            saw_finished = True
        elif kind == "node.started" and node_id is not None:
            starts.add(node_id)
            started_nodes.add(node_id)
        elif kind == "node.finished" and node_id is not None:
            starts.discard(node_id)
            finished_nodes.add(node_id)
    if count == 0 or not saw_started or not saw_finished:
        raise ReviewArtifactError("trace must contain run.started and run.finished")
    if starts:
        raise ReviewArtifactError(f"trace has unfinished nodes: {sorted(starts)}")
    missing_started = node_ids - started_nodes
    missing_finished = node_ids - finished_nodes
    if missing_started or missing_finished:
        missing = sorted(missing_started | missing_finished)
        raise ReviewArtifactError(f"trace is missing node lifecycle events: {missing}")
    return count


def _run_optional_tool(command: list[str], label: str) -> str:
    result = subprocess.run(command, check=False, capture_output=True, text=True)
    if result.returncode != 0:
        detail = result.stderr.strip() or result.stdout.strip() or "unknown error"
        raise ReviewArtifactError(f"{label} failed: {detail}")
    return result.stdout.strip()


def validate_review_artifacts(
    root: Path, *, check_media: bool = False, check_rerun: bool = False
) -> dict[str, Any]:
    manifest_path = root / "review.json"
    if not manifest_path.is_file():
        raise ReviewArtifactError("review.json does not exist")
    try:
        manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    except json.JSONDecodeError as error:
        raise ReviewArtifactError("review.json is not valid JSON") from error
    if not isinstance(manifest, dict) or manifest.get("review_schema_version") != 1:
        raise ReviewArtifactError("review_schema_version must be 1")
    workflow = manifest.get("workflow")
    result = manifest.get("result")
    if not isinstance(workflow, dict) or not isinstance(result, dict):
        raise ReviewArtifactError("manifest requires workflow and result objects")
    workflow_id = workflow.get("id")
    run_id = result.get("run_id")
    if not isinstance(workflow_id, str) or not isinstance(run_id, str):
        raise ReviewArtifactError("workflow.id and result.run_id are required")
    if result.get("workflow_id") != workflow_id:
        raise ReviewArtifactError("result.workflow_id does not match workflow.id")
    profile_id = manifest.get("profile_id")
    if not isinstance(profile_id, str) or not profile_id:
        raise ReviewArtifactError("manifest.profile_id is required")
    result_profile = result.get("profile_id")
    if result_profile is not None and result_profile != profile_id:
        raise ReviewArtifactError("result.profile_id does not match manifest.profile_id")
    workflow_profile = workflow.get("profile_id")
    if workflow_profile is not None and workflow_profile != profile_id:
        raise ReviewArtifactError("workflow.profile_id does not match manifest.profile_id")
    started_at = result.get("started_at")
    finished_at = result.get("finished_at")
    if not isinstance(started_at, str) or not isinstance(finished_at, str):
        raise ReviewArtifactError("result.started_at and result.finished_at are required")
    for timestamp in (started_at, finished_at):
        try:
            datetime.fromisoformat(timestamp.replace("Z", "+00:00"))
        except ValueError as error:
            raise ReviewArtifactError("result timestamps must be ISO-8601") from error
    root_node = workflow.get("workflow")
    if not isinstance(root_node, dict):
        raise ReviewArtifactError("workflow.workflow is required")
    try:
        WorkflowDocument.model_validate(workflow)
    except Exception as error:
        raise ReviewArtifactError("manifest workflow is not valid Workflow IR") from error
    node_ids = _node_ids(root_node)
    artifacts = manifest.get("artifacts")
    if not isinstance(artifacts, dict):
        raise ReviewArtifactError("manifest.artifacts is required")
    trace_path = _artifact_path(root, artifacts.get("trace"), "artifacts.trace")
    video_path = _artifact_path(root, artifacts.get("video"), "artifacts.video")
    rerun_name = artifacts.get("rerun")
    rerun_path = None if rerun_name is None else _artifact_path(root, rerun_name, "artifacts.rerun")
    trace_count = _check_trace(trace_path, run_id, node_ids)
    observation_count = manifest.get("observation_count")
    if observation_count is not None and observation_count != trace_count:
        raise ReviewArtifactError("manifest.observation_count does not match trace record count")
    timeline = manifest.get("timeline")
    if timeline is not None:
        if not isinstance(timeline, dict) or timeline.get("timebase") != "utc":
            raise ReviewArtifactError("timeline.timebase must be utc")
        media = timeline.get("media")
        if not isinstance(media, list) or not any(
            isinstance(item, dict) and item.get("artifact") == artifacts.get("video")
            for item in media
        ):
            raise ReviewArtifactError("timeline must reference the review video")
    media_probe = None
    rerun_probe = None
    if check_media:
        ffprobe = shutil.which("ffprobe")
        if ffprobe is None:
            raise ReviewArtifactError("--check-media requires ffprobe")
        media_probe = _run_optional_tool(
            [
                ffprobe,
                "-v",
                "error",
                "-show_entries",
                "stream=codec_name,width,height",
                "-show_entries",
                "format=duration",
                "-of",
                "json",
                str(video_path),
            ],
            "ffprobe",
        )
    if check_rerun:
        if rerun_path is None:
            raise ReviewArtifactError("--check-rerun requires artifacts.rerun")
        rerun = shutil.which("rerun")
        if rerun is None:
            raise ReviewArtifactError("--check-rerun requires the rerun CLI")
        rerun_probe = _run_optional_tool([rerun, "rrd", "verify", str(rerun_path)], "rerun")
    return {
        "status": "ok",
        "workflow_id": workflow_id,
        "profile_id": profile_id,
        "run_id": run_id,
        "state": result.get("state"),
        "node_count": len(node_ids),
        "trace_records": trace_count,
        "video": str(video_path.name),
        "media_probe": media_probe,
        "rerun_probe": rerun_probe,
    }


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("artifact_dir", type=Path)
    parser.add_argument("--check-media", action="store_true")
    parser.add_argument("--check-rerun", action="store_true")
    args = parser.parse_args()
    try:
        print(
            json.dumps(
                validate_review_artifacts(
                    args.artifact_dir, check_media=args.check_media, check_rerun=args.check_rerun
                ),
                indent=2,
            )
        )
    except ReviewArtifactError as error:
        print(f"error: {error}", file=sys.stderr)
        return 2
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

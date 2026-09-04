from __future__ import annotations

import json
from pathlib import Path

import pytest

from scripts.validate_review_artifacts import ReviewArtifactError, validate_review_artifacts


def _fixture(tmp_path: Path) -> Path:
    (tmp_path / "trace.jsonl").write_text(
        "\n".join(
            json.dumps(item)
            for item in (
                {
                    "kind": "run.started",
                    "run_id": "run-1",
                    "timestamp": "2026-01-01T00:00:00Z",
                    "node_id": None,
                },
                {
                    "kind": "node.started",
                    "run_id": "run-1",
                    "timestamp": "2026-01-01T00:00:01Z",
                    "node_id": "step",
                },
                {
                    "kind": "node.finished",
                    "run_id": "run-1",
                    "timestamp": "2026-01-01T00:00:02Z",
                    "node_id": "step",
                },
                {
                    "kind": "node.started",
                    "run_id": "run-1",
                    "timestamp": "2026-01-01T00:00:00Z",
                    "node_id": "root",
                },
                {
                    "kind": "node.finished",
                    "run_id": "run-1",
                    "timestamp": "2026-01-01T00:00:03Z",
                    "node_id": "root",
                },
                {
                    "kind": "run.finished",
                    "run_id": "run-1",
                    "timestamp": "2026-01-01T00:00:03Z",
                    "node_id": None,
                },
            )
        ),
        encoding="utf-8",
    )
    (tmp_path / "review.mp4").write_bytes(b"fixture")
    (tmp_path / "review.json").write_text(
        json.dumps(
            {
                "review_schema_version": 1,
                "workflow": {
                    "workflow_schema_version": 1,
                    "id": "demo",
                    "name": "Review fixture",
                    "workflow": {
                        "id": "root",
                        "type": "sequence",
                        "children": [{"id": "step", "type": "wait", "duration_ms": 1}],
                    },
                },
                "result": {
                    "run_id": "run-1",
                    "workflow_id": "demo",
                    "profile_id": "mock",
                    "state": "succeeded",
                    "started_at": "2026-01-01T00:00:00Z",
                    "finished_at": "2026-01-01T00:00:03Z",
                },
                "profile_id": "mock",
                "observation_count": 6,
                "artifacts": {"trace": "trace.jsonl", "rerun": None, "video": "review.mp4"},
                "timeline": {
                    "timebase": "utc",
                    "media": [
                        {"id": "camera", "artifact": "review.mp4", "origin": "2026-01-01T00:00:00Z"}
                    ],
                },
            }
        ),
        encoding="utf-8",
    )
    return tmp_path


def test_validates_manifest_trace_and_artifact_references(tmp_path: Path) -> None:
    result = validate_review_artifacts(_fixture(tmp_path))
    assert result["status"] == "ok"
    assert result["trace_records"] == 6


def test_rejects_trace_with_unknown_node(tmp_path: Path) -> None:
    root = _fixture(tmp_path)
    trace = root / "trace.jsonl"
    trace.write_text(
        trace.read_text(encoding="utf-8").replace('"step"', '"unknown"'), encoding="utf-8"
    )
    with pytest.raises(ReviewArtifactError, match="unknown node"):
        validate_review_artifacts(root)


def test_rejects_trace_missing_node_lifecycle(tmp_path: Path) -> None:
    root = _fixture(tmp_path)
    trace = root / "trace.jsonl"
    lines = trace.read_text(encoding="utf-8").splitlines()
    trace.write_text("\n".join(lines[:1] + lines[-1:]), encoding="utf-8")
    with pytest.raises(ReviewArtifactError, match="missing node lifecycle"):
        validate_review_artifacts(root)

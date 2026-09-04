from __future__ import annotations

import json
from datetime import UTC, datetime, timedelta

import pytest

from roboarc.contracts import EventType, ProgressSource, RuntimeEvent
from roboarc.telemetry import (
    ActionPhase,
    ActionState,
    Observation,
    Pose,
    Progress,
    TelemetryKind,
    Trajectory,
    TrajectoryPoint,
    observation_from_event,
    write_trace,
)

NOW = datetime(2026, 8, 31, 10, 0, tzinfo=UTC)
POSE = Pose(frame_id="map", position=(1.0, 2.0, 0.0), orientation=(0.0, 0.0, 0.0, 1.0))


def test_pose_and_trajectory_have_explicit_frames_and_time() -> None:
    later = NOW + timedelta(seconds=1)
    trajectory = Trajectory(
        frame_id="map",
        points=(TrajectoryPoint(NOW, POSE), TrajectoryPoint(later, POSE)),
    )
    observation = Observation.trajectory(
        timestamp=later,
        run_id="run-1",
        node_id="move",
        invocation_id="inv-1",
        trajectory=trajectory,
    )

    assert observation.kind == TelemetryKind.TRAJECTORY
    assert observation.data["frame_id"] == "map"
    assert observation.data["points"][0]["timestamp"] == NOW.isoformat()


def test_pose_rejects_non_finite_or_non_normalized_values() -> None:
    with pytest.raises(ValueError, match="finite"):
        Pose("map", (float("nan"), 0.0, 0.0), (0.0, 0.0, 0.0, 1.0))
    with pytest.raises(ValueError, match="normalized"):
        Pose("map", (0.0, 0.0, 0.0), (0.0, 0.0, 0.0, 2.0))


def test_trajectory_rejects_time_or_frame_discontinuity() -> None:
    odom_pose = Pose("odom", (0.0, 0.0, 0.0), (0.0, 0.0, 0.0, 1.0))
    with pytest.raises(ValueError, match="non-decreasing"):
        Trajectory(
            points=(
                TrajectoryPoint(NOW, POSE),
                TrajectoryPoint(NOW - timedelta(seconds=1), POSE),
            )
        )
    with pytest.raises(ValueError, match="frame_id"):
        Trajectory(frame_id="map", points=(TrajectoryPoint(NOW, odom_pose),))


def test_progress_requires_truthful_percent_and_distance() -> None:
    with pytest.raises(ValueError, match="source"):
        Progress(percent=50.0)
    with pytest.raises(ValueError, match="supplied together"):
        Progress(stage="moving", current=1.0)

    progress = Progress(
        stage="moving",
        percent=50.0,
        source=ProgressSource.ESTIMATED,
        current=1.0,
        total=2.0,
        unit="m",
    )
    observation = Observation.progress(
        timestamp=NOW,
        run_id="run-1",
        node_id="move",
        invocation_id="inv-1",
        progress=progress,
    )
    assert observation.data["source"] == "estimated"
    assert observation.invocation_id == "inv-1"


def test_action_state_is_correlated_with_invocation() -> None:
    observation = Observation.action_state(
        timestamp=NOW,
        run_id="run-1",
        node_id="move",
        invocation_id="inv-1",
        action=ActionState("navigation.goto_location", ActionPhase.EXECUTING),
    )
    assert observation.kind == TelemetryKind.ACTION_STATE
    assert observation.data == {
        "action_id": "navigation.goto_location",
        "state": "executing",
        "message": None,
    }


def test_runtime_event_conversion_preserves_correlation() -> None:
    event = RuntimeEvent(
        seq=1,
        run_id="run-1",
        node_id="move",
        type=EventType.CAPABILITY_PROGRESS,
        occurred_at=NOW,
        data={"invocation_id": "inv-1", "stage": "moving"},
    )
    observation = observation_from_event(event)
    assert observation.timestamp == NOW
    assert observation.run_id == "run-1"
    assert observation.node_id == "move"
    assert observation.invocation_id == "inv-1"


def test_trace_serializes_runtime_and_robot_observations(tmp_path) -> None:
    event = RuntimeEvent(
        seq=1,
        run_id="run-1",
        type=EventType.RUN_STARTED,
        occurred_at=NOW,
    )
    pose = Observation.pose(timestamp=NOW, run_id="run-1", pose=POSE)
    path = tmp_path / "trace.jsonl"

    assert write_trace(path, (event, pose)) == 2
    records = [json.loads(line) for line in path.read_text().splitlines()]
    assert [record["kind"] for record in records] == ["run.started", "robot.pose"]
    assert all(record["timestamp"] == NOW.isoformat() for record in records)


def test_observation_rejects_naive_time_and_non_json_data() -> None:
    with pytest.raises(ValueError, match="timezone"):
        Observation(datetime(2026, 8, 31), "run-1", None, None, "test", {})
    with pytest.raises(ValueError, match="JSON"):
        Observation(NOW, "run-1", None, None, "test", {"bad": object()})

from __future__ import annotations

from datetime import UTC, datetime

import pytest

from roboarc_tiago.telemetry_bridge import (
    estimated_distance_observation,
    pose_observations,
    ros_timestamp,
)

NOW = datetime(2026, 8, 31, 12, 0, tzinfo=UTC)


def test_pose_and_trajectory_preserve_ros_correlation() -> None:
    records = pose_observations(
        timestamp=NOW,
        run_id="run-1",
        node_id="navigate",
        invocation_id="inv-1",
        frame_id="map",
        position=(1.0, 2.0, 0.0),
        orientation=(0.0, 0.0, 0.0, 1.0),
    )
    assert [record.kind for record in records] == ["robot.pose", "robot.trajectory"]
    assert {(record.run_id, record.node_id, record.invocation_id) for record in records} == {
        ("run-1", "navigate", "inv-1")
    }
    assert records[1].data["points"][0]["pose"] == records[0].data


def test_ros_time_and_estimated_distance_are_explicit() -> None:
    assert ros_timestamp(1, 500_000_000) == datetime(1970, 1, 1, 0, 0, 1, 500000, tzinfo=UTC)
    record = estimated_distance_observation(
        timestamp=NOW,
        run_id="run-1",
        node_id="navigate",
        invocation_id="inv-1",
        remaining=3.0,
        initial=4.0,
    )
    assert record.data["percent"] == pytest.approx(25.0)
    assert record.data["source"] == "estimated"
    assert record.data["current"] == pytest.approx(1.0)

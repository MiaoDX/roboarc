"""Pure conversion helpers for ROS-native state entering RoboArc telemetry."""

from __future__ import annotations

from datetime import UTC, datetime

from roboarc.contracts import ProgressSource
from roboarc.telemetry import Observation, Pose, Progress, Trajectory, TrajectoryPoint


def ros_timestamp(seconds: int, nanoseconds: int) -> datetime:
    """Translate a ROS stamp, using wall time for an unset simulation stamp."""
    if seconds == 0 and nanoseconds == 0:
        return datetime.now(UTC)
    return datetime.fromtimestamp(seconds + nanoseconds / 1_000_000_000, tz=UTC)


def pose_observations(
    *,
    timestamp: datetime,
    run_id: str,
    node_id: str,
    invocation_id: str,
    frame_id: str,
    position: tuple[float, float, float],
    orientation: tuple[float, float, float, float],
) -> tuple[Observation, Observation]:
    """Emit one pose sample and its one-point trajectory representation."""
    pose = Pose(frame_id, position, orientation)
    correlation = {
        "timestamp": timestamp,
        "run_id": run_id,
        "node_id": node_id,
        "invocation_id": invocation_id,
    }
    return (
        Observation.pose(pose=pose, **correlation),
        Observation.trajectory(
            trajectory=Trajectory(
                points=(TrajectoryPoint(timestamp, pose),),
                frame_id=frame_id,
            ),
            **correlation,
        ),
    )


def native_feedback_observation(
    *,
    timestamp: datetime,
    run_id: str,
    node_id: str,
    invocation_id: str,
    stage: str,
    message: str,
) -> Observation:
    return Observation.progress(
        timestamp=timestamp,
        run_id=run_id,
        node_id=node_id,
        invocation_id=invocation_id,
        progress=Progress(stage=stage, message=message),
    )


def estimated_distance_observation(
    *,
    timestamp: datetime,
    run_id: str,
    node_id: str,
    invocation_id: str,
    remaining: float,
    initial: float,
) -> Observation:
    completed = max(0.0, min(initial, initial - remaining))
    percent = 100.0 if initial == 0 else completed * 100.0 / initial
    return Observation.progress(
        timestamp=timestamp,
        run_id=run_id,
        node_id=node_id,
        invocation_id=invocation_id,
        progress=Progress(
            stage="navigating",
            percent=percent,
            source=ProgressSource.ESTIMATED,
            current=completed,
            total=max(initial, 1e-12),
            unit="m",
        ),
    )

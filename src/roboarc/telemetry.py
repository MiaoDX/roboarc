"""Backend-neutral robot observations and trace export.

The classes in this module are deliberately small value objects.  A simulator,
ROS adapter, or another observation backend can produce the same records
without importing one another (or leaking their native message types).
"""
from __future__ import annotations

import json
import math
from collections.abc import Iterable, Mapping
from dataclasses import dataclass
from datetime import datetime
from enum import StrEnum
from itertools import pairwise
from pathlib import Path
from typing import Any

from roboarc.contracts import EventType, ProgressSource, RuntimeEvent
from roboarc.contracts.common import is_json_value


def _timestamp(value: datetime) -> None:
    if value.tzinfo is None or value.utcoffset() is None:
        raise ValueError("timestamp must include a timezone")


def _finite(values: tuple[float, ...], name: str) -> None:
    if not all(math.isfinite(value) for value in values):
        raise ValueError(f"{name} values must be finite")


class TelemetryKind(StrEnum):
    POSE = "robot.pose"
    TRAJECTORY = "robot.trajectory"
    ACTION_STATE = "action.state"
    PROGRESS = "capability.progress"


class ActionPhase(StrEnum):
    PENDING = "pending"
    ACCEPTED = "accepted"
    EXECUTING = "executing"
    SUCCEEDED = "succeeded"
    FAILED = "failed"
    CANCELED = "canceled"
    TIMED_OUT = "timed_out"


@dataclass(frozen=True, slots=True)
class Pose:
    """A 3D pose in a named coordinate frame (quaternion is ``x,y,z,w``)."""

    frame_id: str
    position: tuple[float, float, float]
    orientation: tuple[float, float, float, float]

    def __post_init__(self) -> None:
        if not self.frame_id:
            raise ValueError("frame_id must not be empty")
        if len(self.position) != 3 or len(self.orientation) != 4:
            raise ValueError("pose position must have 3 and orientation 4 values")
        _finite(self.position, "position")
        _finite(self.orientation, "orientation")
        norm = math.sqrt(sum(value * value for value in self.orientation))
        if not math.isclose(norm, 1.0, abs_tol=1e-6):
            raise ValueError("orientation quaternion must be normalized")

    def as_dict(self) -> dict[str, Any]:
        return {
            "frame_id": self.frame_id,
            "position": list(self.position),
            "orientation": list(self.orientation),
        }


@dataclass(frozen=True, slots=True)
class TrajectoryPoint:
    timestamp: datetime
    pose: Pose

    def __post_init__(self) -> None:
        _timestamp(self.timestamp)

    def as_dict(self) -> dict[str, Any]:
        return {"timestamp": self.timestamp.isoformat(), "pose": self.pose.as_dict()}


@dataclass(frozen=True, slots=True)
class Trajectory:
    points: tuple[TrajectoryPoint, ...]
    frame_id: str | None = None

    def __post_init__(self) -> None:
        if not self.points:
            raise ValueError("trajectory must contain at least one point")
        timestamps = tuple(point.timestamp for point in self.points)
        if any(current < previous for previous, current in pairwise(timestamps)):
            raise ValueError("trajectory timestamps must be non-decreasing")
        if self.frame_id is not None and any(
            point.pose.frame_id != self.frame_id for point in self.points
        ):
            raise ValueError("trajectory points must use trajectory frame_id")

    def as_dict(self) -> dict[str, Any]:
        return {"frame_id": self.frame_id, "points": [point.as_dict() for point in self.points]}


@dataclass(frozen=True, slots=True)
class ActionState:
    action_id: str
    state: ActionPhase
    message: str | None = None

    def __post_init__(self) -> None:
        if not self.action_id:
            raise ValueError("action_id must not be empty")

    def as_dict(self) -> dict[str, Any]:
        return {"action_id": self.action_id, "state": self.state.value, "message": self.message}


@dataclass(frozen=True, slots=True)
class Progress:
    stage: str | None = None
    percent: float | None = None
    source: ProgressSource | None = None
    message: str | None = None
    current: float | None = None
    total: float | None = None
    unit: str | None = None

    def __post_init__(self) -> None:
        if self.stage == "":
            raise ValueError("stage must not be empty")
        if self.stage is None and self.percent is None:
            raise ValueError("progress requires stage or percent")
        if self.percent is not None:
            if not math.isfinite(self.percent) or not 0 <= self.percent <= 100:
                raise ValueError("percent must be between 0 and 100")
            if self.source is None:
                raise ValueError("percent progress requires a source")
        elif self.source is not None:
            raise ValueError("progress source is only valid with percent")
        if self.current is not None and not math.isfinite(self.current):
            raise ValueError("current must be finite")
        if self.total is not None and (not math.isfinite(self.total) or self.total <= 0):
            raise ValueError("total must be positive and finite")
        if (self.current is None) != (self.total is None):
            raise ValueError("current and total must be supplied together")
        if self.current is not None and self.total is not None:
            if self.current < 0 or self.current > self.total:
                raise ValueError("current must be between zero and total")
            if not self.unit:
                raise ValueError("current and total require a unit")
        elif self.unit is not None:
            raise ValueError("unit is only valid with current and total")

    def as_dict(self) -> dict[str, Any]:
        result: dict[str, Any] = {}
        values = (
            ("stage", self.stage),
            ("percent", self.percent),
            ("source", self.source.value if self.source else None),
            ("message", self.message),
            ("current", self.current),
            ("total", self.total),
            ("unit", self.unit),
        )
        for key, value in values:
            if value is not None:
                result[key] = value
        return result


@dataclass(frozen=True, slots=True)
class Observation:
    timestamp: datetime
    run_id: str
    node_id: str | None
    invocation_id: str | None
    kind: str
    data: Mapping[str, Any]

    def __post_init__(self) -> None:
        _timestamp(self.timestamp)
        if not self.run_id or not self.kind:
            raise ValueError("run_id and kind must not be empty")
        if not is_json_value(dict(self.data)):
            raise ValueError("observation data must be JSON-serializable")

    def as_dict(self) -> dict[str, Any]:
        return {
            "timestamp": self.timestamp.isoformat(),
            "run_id": self.run_id,
            "node_id": self.node_id,
            "invocation_id": self.invocation_id,
            "kind": self.kind,
            "data": dict(self.data),
        }

    @classmethod
    def pose(
        cls,
        *,
        timestamp: datetime,
        run_id: str,
        pose: Pose,
        node_id: str | None = None,
        invocation_id: str | None = None,
    ) -> Observation:
        return cls(
            timestamp, run_id, node_id, invocation_id, TelemetryKind.POSE, pose.as_dict()
        )

    @classmethod
    def trajectory(
        cls,
        *,
        timestamp: datetime,
        run_id: str,
        trajectory: Trajectory,
        node_id: str | None = None,
        invocation_id: str | None = None,
    ) -> Observation:
        return cls(
            timestamp,
            run_id,
            node_id,
            invocation_id,
            TelemetryKind.TRAJECTORY,
            trajectory.as_dict(),
        )

    @classmethod
    def action_state(
        cls,
        *,
        timestamp: datetime,
        run_id: str,
        node_id: str,
        invocation_id: str,
        action: ActionState,
    ) -> Observation:
        return cls(
            timestamp,
            run_id,
            node_id,
            invocation_id,
            TelemetryKind.ACTION_STATE,
            action.as_dict(),
        )

    @classmethod
    def progress(
        cls,
        *,
        timestamp: datetime,
        run_id: str,
        node_id: str,
        invocation_id: str,
        progress: Progress,
    ) -> Observation:
        return cls(
            timestamp,
            run_id,
            node_id,
            invocation_id,
            TelemetryKind.PROGRESS,
            progress.as_dict(),
        )


def observation_from_event(event: RuntimeEvent) -> Observation:
    """Convert one runtime event while preserving correlation identity."""
    event_type = event.type.value if isinstance(event.type, EventType) else str(event.type)
    node_id = str(event.node_id) if event.node_id is not None else None
    invocation_id = event.data.get("invocation_id")
    return Observation(
        event.occurred_at,
        str(event.run_id),
        node_id,
        str(invocation_id) if invocation_id is not None else None,
        event_type,
        dict(event.data),
    )


def observations(events: Iterable[RuntimeEvent | Observation]) -> tuple[Observation, ...]:
    return tuple(
        event if isinstance(event, Observation) else observation_from_event(event)
        for event in events
    )


def write_trace(path: Path, events: Iterable[RuntimeEvent | Observation]) -> int:
    records = observations(events)
    with path.open("w", encoding="utf-8") as handle:
        for record in records:
            handle.write(json.dumps(record.as_dict(), sort_keys=True) + "\n")
    return len(records)

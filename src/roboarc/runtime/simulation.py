"""Deterministic, no-ROS simulation adapter for observable runtime proofs.

The adapter intentionally models only a planar point robot.  Its state source is
fixed-step and deterministic, making traces suitable for replay and correlation
tests without requiring Gazebo, ROS, or a wall-clock simulator.
"""

from __future__ import annotations

import asyncio
from dataclasses import dataclass
from datetime import UTC, datetime
from typing import Any, cast

from roboarc.contracts import (
    CapabilityManifest,
    CapabilityRef,
    CapabilityResult,
    ExecutionTraits,
    ProgressMode,
    ProgressSource,
    ProgressSpec,
    ResultStatus,
    RobotProfile,
    ValueSpec,
    ValueType,
)
from roboarc.runtime.adapter import CancellationDisposition, CapabilityInvocation
from roboarc.runtime.context import ExecutionContext
from roboarc.telemetry import (
    ActionPhase,
    ActionState,
    Observation,
    Pose,
    Progress,
    TelemetryKind,
    Trajectory,
    TrajectoryPoint,
)


@dataclass(frozen=True, slots=True)
class SimulatedPose:
    """A planar pose in the simulator's stable ``map`` frame."""

    x: float
    y: float
    yaw: float = 0.0
    frame: str = "map"

    def as_dict(self) -> dict[str, Any]:
        return {"frame": self.frame, "x": self.x, "y": self.y, "yaw": self.yaw}


class _SimulationInvocation(CapabilityInvocation):
    def __init__(self, task: asyncio.Task[CapabilityResult], cancel_event: asyncio.Event) -> None:
        self._task = task
        self._cancel_event = cancel_event

    async def result(self) -> CapabilityResult:
        return await asyncio.shield(self._task)

    async def request_cancel(self) -> CancellationDisposition:
        if self._task.done():
            return CancellationDisposition.ALREADY_COMPLETE
        self._cancel_event.set()
        return CancellationDisposition.ACCEPTED

    async def detach(self) -> None:
        self._task.add_done_callback(
            lambda task: task.exception() if not task.cancelled() else None
        )


class DeterministicSimulationAdapter:
    """Small deterministic adapter that emits correlated robot-state telemetry."""

    capability = CapabilityManifest(
        id="simulation.navigate",
        version=1,
        title="Simulated navigation",
        category="Simulation",
        inputs={
            "target_x": ValueSpec(type=ValueType.NUMBER, required=True),
            "target_y": ValueSpec(type=ValueType.NUMBER, required=True),
            "duration_ms": ValueSpec(type=ValueType.DURATION_MS, default=40, minimum=1),
        },
        outputs={
            "x": ValueSpec(type=ValueType.NUMBER, required=True),
            "y": ValueSpec(type=ValueType.NUMBER, required=True),
        },
        execution=ExecutionTraits(cancellable=True),
        progress=ProgressSpec(mode=ProgressMode.PERCENT, source=ProgressSource.ESTIMATED),
    )

    def __init__(self, *, initial_pose: SimulatedPose | None = None, step_ms: int = 10) -> None:
        if step_ms < 1:
            raise ValueError("step_ms must be positive")
        self._pose = initial_pose or SimulatedPose(0.0, 0.0)
        self.step_ms = step_ms
        self._records: list[Observation] = []
        self._tasks: set[asyncio.Task[CapabilityResult]] = set()
        self._profile = RobotProfile(
            id="deterministic-simulation",
            title="RoboArc Deterministic Simulation",
            adapter="deterministic_simulation",
            capabilities=(self.capability.ref,),
        )

    @property
    def profile(self) -> RobotProfile:
        return self._profile

    @property
    def manifests(self) -> tuple[CapabilityManifest, ...]:
        return (self.capability,)

    @property
    def pose(self) -> SimulatedPose:
        return self._pose

    @property
    def telemetry(self) -> tuple[Observation, ...]:
        return tuple(self._records)

    def reset(self, pose: SimulatedPose | None = None) -> None:
        """Reset state and discard samples between deterministic runs."""
        self._pose = pose or SimulatedPose(0.0, 0.0)
        self._records.clear()

    async def invoke(
        self,
        capability: CapabilityRef,
        args: dict[str, object],
        context: ExecutionContext,
    ) -> _SimulationInvocation:
        if capability != self.capability.ref:
            raise KeyError(
                f"unsupported simulation capability: {capability.id}@{capability.version}"
            )
        cancel_event = asyncio.Event()
        task = asyncio.create_task(
            self._navigate(args, context, cancel_event),
            name=f"simulation:{context.invocation_id}",
        )
        self._tasks.add(task)
        task.add_done_callback(self._tasks.discard)
        return _SimulationInvocation(task, cancel_event)

    async def wait_for_idle(self) -> None:
        if self._tasks:
            await asyncio.gather(*tuple(self._tasks), return_exceptions=True)

    async def _navigate(
        self, args: dict[str, object], context: ExecutionContext, cancel_event: asyncio.Event
    ) -> CapabilityResult:
        target_x = float(cast(float | int, args["target_x"]))
        target_y = float(cast(float | int, args["target_y"]))
        duration_ms = int(cast(int, args["duration_ms"]))
        steps = max(1, (duration_ms + self.step_ms - 1) // self.step_ms)
        start = self._pose
        await self._emit_action(context, ActionPhase.ACCEPTED)
        await self._emit_action(context, ActionPhase.EXECUTING)
        for index in range(1, steps + 1):
            if cancel_event.is_set():
                await self._emit_action(context, ActionPhase.CANCELED)
                return CapabilityResult(status=ResultStatus.CANCELED, output=self._pose.as_dict())
            ratio = index / steps
            self._pose = SimulatedPose(
                x=start.x + (target_x - start.x) * ratio,
                y=start.y + (target_y - start.y) * ratio,
                yaw=start.yaw,
                frame=start.frame,
            )
            pose = self._pose.as_dict()
            telemetry_pose = Pose("map", (self._pose.x, self._pose.y, 0.0), (0.0, 0.0, 0.0, 1.0))
            await self._emit(context, TelemetryKind.POSE, telemetry_pose.as_dict())
            point = TrajectoryPoint(self._timestamp(), telemetry_pose)
            await self._emit(
                context,
                TelemetryKind.TRAJECTORY,
                Trajectory((point,), frame_id="map").as_dict(),
            )
            del pose
            await self._emit_progress(context, ratio, index, steps)
            await asyncio.sleep(self.step_ms / 1000)
        await self._emit_action(context, ActionPhase.SUCCEEDED)
        return CapabilityResult(
            status=ResultStatus.SUCCESS,
            output={"x": self._pose.x, "y": self._pose.y},
        )

    def _timestamp(self) -> datetime:
        return datetime.now(UTC)

    async def _emit(self, context: ExecutionContext, kind: str, sample: dict[str, Any]) -> None:
        self._records.append(
            Observation(
                self._timestamp(),
                context.run_id,
                context.node_id,
                context.invocation_id,
                kind,
                sample,
            )
        )

    async def _emit_action(self, context: ExecutionContext, state: ActionPhase) -> None:
        action = ActionState(context.invocation_id, state)
        await self._emit(context, TelemetryKind.ACTION_STATE, action.as_dict())

    async def _emit_progress(
        self, context: ExecutionContext, ratio: float, current: int, total: int
    ) -> None:
        progress = Progress(
            percent=ratio * 100,
            source=ProgressSource.ESTIMATED,
            current=current,
            total=total,
            unit="step",
        )
        await self._emit(context, TelemetryKind.PROGRESS, progress.as_dict())
        await context.report_progress(
            percent=ratio * 100,
            source=ProgressSource.ESTIMATED,
            current=current,
            total=total,
            unit="step",
        )


# Short alias for callers that do not need to spell out the determinism.
SimulationAdapter = DeterministicSimulationAdapter

"""Reachy SDK adapter with vendor imports isolated behind a lazy connector."""

from __future__ import annotations

import asyncio
from collections.abc import Sequence
from typing import Protocol, cast

from roboarc.contracts import (
    CapabilityManifest,
    CapabilityRef,
    CapabilityResult,
    ErrorCode,
    ExecutionError,
    ProgressSource,
    ResultStatus,
    RobotProfile,
)
from roboarc.runtime.adapter import CancellationDisposition, CapabilityAdapter, CapabilityInvocation
from roboarc.runtime.context import ExecutionContext

from .fake_sdk import FakeReachy
from .profile import ARM_POSE_JOINTS, JOINT_FIELDS, REACHY_MANIFESTS, REACHY_PROFILE


class ReachyArm(Protocol):
    def get_present_positions(self) -> Sequence[float]: ...
    def set_goal_positions(self, target: Sequence[float]) -> None: ...


class ReachyClient(Protocol):
    l_arm: ReachyArm
    r_arm: ReachyArm

    def send_goal_positions(self) -> None: ...


def connect_reachy(host: str = "127.0.0.1", port: int = 18861) -> ReachyClient:
    try:
        import rpyc  # type: ignore[import-untyped]
    except ImportError as error:
        raise RuntimeError(
            "Reachy support requires the optional 'reachy' extra (rpyc); "
            "use FakeReachy for always-on tests"
        ) from error
    connection = rpyc.connect(
        host,
        port=port,
        config={"allow_pickle": True, "allow_all_attrs": True},
    )
    return cast(ReachyClient, connection.root.reachy)


class ReachyAdapter(CapabilityAdapter):
    def __init__(self, robot: ReachyClient | None = None) -> None:
        self.robot = robot or FakeReachy()

    @property
    def profile(self) -> RobotProfile:
        return REACHY_PROFILE

    @property
    def manifests(self) -> tuple[CapabilityManifest, ...]:
        return REACHY_MANIFESTS

    async def invoke(
        self, capability: CapabilityRef, args: dict[str, object], context: ExecutionContext
    ) -> CapabilityInvocation:
        if capability != ARM_POSE_JOINTS.ref:
            raise KeyError(f"unsupported Reachy capability: {capability.id}@{capability.version}")
        try:
            side = cast(str, args["side"])
            if side not in {"left", "right"}:
                raise ValueError("side must be 'left' or 'right'")
            values = tuple(_number(args[field], field) for field in JOINT_FIELDS)
            duration_ms = args.get("duration_ms", 1000)
            if isinstance(duration_ms, bool) or not isinstance(duration_ms, int):
                raise ValueError("duration_ms must be an integer")
            if not 0 <= duration_ms <= 10_000:
                raise ValueError("duration_ms must be between 0 and 10000")
        except (KeyError, ValueError) as error:
            return _Immediate(_failure(ErrorCode.VALIDATION_ERROR, str(error)))
        return _Invocation(cast(ReachyClient, self.robot), side, values, duration_ms, context)


def _number(value: object, field: str) -> float:
    if isinstance(value, bool) or not isinstance(value, (int, float)) or not -180 <= value <= 180:
        raise ValueError(f"{field} must be a number between -180 and 180")
    return float(value)


def _failure(code: ErrorCode, message: str) -> CapabilityResult:
    return CapabilityResult(
        status=ResultStatus.FAILURE, error=ExecutionError(code=code, message=message)
    )


class _Immediate(CapabilityInvocation):
    def __init__(self, result: CapabilityResult):
        self._result = result

    async def result(self) -> CapabilityResult:
        return self._result

    async def request_cancel(self) -> CancellationDisposition:
        return CancellationDisposition.ALREADY_COMPLETE

    async def detach(self) -> None:
        return None


class _Invocation(CapabilityInvocation):
    def __init__(
        self,
        robot: ReachyClient,
        side: str,
        target: tuple[float, ...],
        duration_ms: int,
        context: ExecutionContext,
    ) -> None:
        self._side = side
        self._task = asyncio.create_task(_move_arm(robot, side, target, duration_ms, context))

    async def result(self) -> CapabilityResult:
        try:
            await self._task
        except Exception as error:
            return _failure(ErrorCode.CAPABILITY_FAILED, str(error))
        return CapabilityResult(
            status=ResultStatus.SUCCESS, output={"side": self._side, "completed": True}
        )

    async def request_cancel(self) -> CancellationDisposition:
        return CancellationDisposition.UNSUPPORTED

    async def detach(self) -> None:
        return None


async def _move_arm(
    robot: ReachyClient,
    side: str,
    target: tuple[float, ...],
    duration_ms: int,
    context: ExecutionContext,
) -> None:
    arm = robot.l_arm if side == "left" else robot.r_arm
    start = tuple(float(value) for value in await asyncio.to_thread(arm.get_present_positions))
    if len(start) != len(target):
        raise RuntimeError(f"Reachy SDK returned {len(start)} arm joints; expected {len(target)}")
    steps = max(1, min(100, (duration_ms + 49) // 50))
    interval = duration_ms / steps / 1000
    for step in range(1, steps + 1):
        fraction = step / steps
        position = tuple(a + (b - a) * fraction for a, b in zip(start, target, strict=True))
        await asyncio.to_thread(arm.set_goal_positions, position)
        await asyncio.to_thread(robot.send_goal_positions)
        await context.report_progress(
            stage="posing",
            percent=100 * fraction,
            source=ProgressSource.ESTIMATED,
            current=step,
            total=steps,
            unit="step",
        )
        if step < steps and interval:
            await asyncio.sleep(interval)

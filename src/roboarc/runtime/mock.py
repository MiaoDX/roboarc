"""Deterministic first-class mock robot adapter."""

from __future__ import annotations

import asyncio
from collections.abc import Awaitable, Callable
from typing import Any

from roboarc.contracts import (
    CapabilityManifest,
    CapabilityRef,
    CapabilityResult,
    ErrorCode,
    ExecutionError,
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

Handler = Callable[
    [dict[str, object], ExecutionContext, asyncio.Event], Awaitable[CapabilityResult]
]


class MockInvocation(CapabilityInvocation):
    def __init__(
        self,
        task: asyncio.Task[CapabilityResult],
        cancel_event: asyncio.Event,
        cancellable: bool,
    ) -> None:
        self._task = task
        self._cancel_event = cancel_event
        self._cancellable = cancellable

    async def result(self) -> CapabilityResult:
        return await asyncio.shield(self._task)

    async def request_cancel(self) -> CancellationDisposition:
        if self._task.done():
            return CancellationDisposition.ALREADY_COMPLETE
        if not self._cancellable:
            return CancellationDisposition.UNSUPPORTED
        self._cancel_event.set()
        return CancellationDisposition.ACCEPTED

    async def detach(self) -> None:
        # The task deliberately continues: detaching local observation must not pretend
        # that an uncancellable native action stopped. Consume any later exception.
        self._task.add_done_callback(
            lambda task: task.exception() if not task.cancelled() else None
        )


class MockAdapter:
    """Mock profile covering progress, failure, timeout, and cancellation semantics."""

    def __init__(self) -> None:
        self._manifests = _build_manifests()
        self._profile = RobotProfile(
            id="mock",
            title="RoboArc Mock Robot",
            adapter="mock",
            capabilities=tuple(manifest.ref for manifest in self._manifests),
        )
        self._handlers: dict[str, Handler] = {
            "demo.instant_success": self._instant_success,
            "demo.staged_action": self._staged_action,
            "demo.percent_action": self._percent_action,
            "demo.fail": self._fail,
            "demo.cancellable_action": self._cancellable_action,
            "demo.uncancellable_action": self._uncancellable_action,
        }
        self._tasks: set[asyncio.Task[CapabilityResult]] = set()

    @property
    def profile(self) -> RobotProfile:
        return self._profile

    @property
    def manifests(self) -> tuple[CapabilityManifest, ...]:
        return self._manifests

    async def invoke(
        self,
        capability: CapabilityRef,
        args: dict[str, object],
        context: ExecutionContext,
    ) -> MockInvocation:
        manifest = next(
            (
                item
                for item in self._manifests
                if item.id == capability.id and item.version == capability.version
            ),
            None,
        )
        if manifest is None:
            raise KeyError(f"unsupported mock capability: {capability.id}@{capability.version}")
        handler = self._handlers[capability.id]
        cancel_event = asyncio.Event()
        task = asyncio.create_task(
            handler(args, context, cancel_event),
            name=f"mock:{context.invocation_id}",
        )
        self._tasks.add(task)
        task.add_done_callback(self._tasks.discard)
        return MockInvocation(task, cancel_event, manifest.execution.cancellable)

    async def wait_for_idle(self) -> None:
        if self._tasks:
            await asyncio.gather(*tuple(self._tasks), return_exceptions=True)

    async def _instant_success(
        self,
        args: dict[str, object],
        context: ExecutionContext,
        cancel_event: asyncio.Event,
    ) -> CapabilityResult:
        del context, cancel_event
        return CapabilityResult(
            status=ResultStatus.SUCCESS,
            output={"value": str(args.get("value", "ok"))},
        )

    async def _staged_action(
        self,
        args: dict[str, object],
        context: ExecutionContext,
        cancel_event: asyncio.Event,
    ) -> CapabilityResult:
        del cancel_event
        delay = int(args.get("stage_delay_ms", 10)) / 1000
        for stage in ("planning", "executing", "finishing"):
            await context.report_progress(stage=stage, message=f"Mock stage: {stage}")
            await asyncio.sleep(delay)
        return CapabilityResult(status=ResultStatus.SUCCESS, output={"stage": "finished"})

    async def _percent_action(
        self,
        args: dict[str, object],
        context: ExecutionContext,
        cancel_event: asyncio.Event,
    ) -> CapabilityResult:
        del cancel_event
        steps = int(args.get("steps", 4))
        delay = int(args.get("step_delay_ms", 5)) / 1000
        for index in range(steps + 1):
            percent = 100 * index / steps
            await context.report_progress(
                percent=percent,
                source=ProgressSource.NATIVE,
                current=index,
                total=steps,
                unit="step",
            )
            if index < steps:
                await asyncio.sleep(delay)
        return CapabilityResult(status=ResultStatus.SUCCESS, output={"percent": 100.0})

    async def _fail(
        self,
        args: dict[str, object],
        context: ExecutionContext,
        cancel_event: asyncio.Event,
    ) -> CapabilityResult:
        del context, cancel_event
        message = str(args.get("message", "deterministic mock failure"))
        return CapabilityResult(
            status=ResultStatus.FAILURE,
            error=ExecutionError(code=ErrorCode.CAPABILITY_FAILED, message=message),
        )

    async def _cancellable_action(
        self,
        args: dict[str, object],
        context: ExecutionContext,
        cancel_event: asyncio.Event,
    ) -> CapabilityResult:
        duration_ms = int(args.get("duration_ms", 200))
        tick_ms = int(args.get("tick_ms", 10))
        cleanup_ms = int(args.get("cleanup_ms", 5))
        elapsed = 0
        while elapsed < duration_ms:
            if cancel_event.is_set():
                await context.log("info", "mock cancellation acknowledged")
                await asyncio.sleep(cleanup_ms / 1000)
                return CapabilityResult(status=ResultStatus.CANCELED)
            await asyncio.sleep(min(tick_ms, duration_ms - elapsed) / 1000)
            elapsed += tick_ms
        return CapabilityResult(status=ResultStatus.SUCCESS, output={"completed": True})

    async def _uncancellable_action(
        self,
        args: dict[str, object],
        context: ExecutionContext,
        cancel_event: asyncio.Event,
    ) -> CapabilityResult:
        del context, cancel_event
        await asyncio.sleep(int(args.get("duration_ms", 100)) / 1000)
        return CapabilityResult(status=ResultStatus.SUCCESS, output={"completed": True})


def _build_manifests() -> tuple[CapabilityManifest, ...]:
    return (
        CapabilityManifest(
            id="demo.instant_success",
            version=1,
            title="Instant success",
            category="Demo",
            inputs={
                "value": ValueSpec(type=ValueType.STRING, default="ok"),
            },
            outputs={
                "value": ValueSpec(type=ValueType.STRING, required=True),
            },
        ),
        CapabilityManifest(
            id="demo.staged_action",
            version=1,
            title="Staged action",
            category="Demo",
            inputs={
                "stage_delay_ms": ValueSpec(
                    type=ValueType.DURATION_MS,
                    default=10,
                    maximum=10_000,
                ),
            },
            outputs={"stage": ValueSpec(type=ValueType.STRING, required=True)},
            progress=ProgressSpec(mode=ProgressMode.STAGE),
        ),
        CapabilityManifest(
            id="demo.percent_action",
            version=1,
            title="Percent action",
            category="Demo",
            inputs={
                "steps": ValueSpec(type=ValueType.INTEGER, default=4, minimum=1, maximum=100),
                "step_delay_ms": ValueSpec(
                    type=ValueType.DURATION_MS,
                    default=5,
                    maximum=10_000,
                ),
            },
            outputs={"percent": ValueSpec(type=ValueType.NUMBER, required=True)},
            progress=ProgressSpec(mode=ProgressMode.PERCENT, source=ProgressSource.NATIVE),
        ),
        CapabilityManifest(
            id="demo.fail",
            version=1,
            title="Fail",
            category="Demo",
            inputs={"message": ValueSpec(type=ValueType.STRING, default="mock failure")},
        ),
        CapabilityManifest(
            id="demo.cancellable_action",
            version=1,
            title="Cancellable action",
            category="Demo",
            inputs={
                "duration_ms": ValueSpec(type=ValueType.DURATION_MS, default=200),
                "tick_ms": ValueSpec(type=ValueType.DURATION_MS, default=10, minimum=1),
                "cleanup_ms": ValueSpec(type=ValueType.DURATION_MS, default=5),
            },
            outputs={"completed": ValueSpec(type=ValueType.BOOLEAN, required=True)},
            execution=ExecutionTraits(timeout_ms=5_000, cancellable=True),
            progress=ProgressSpec(mode=ProgressMode.STAGE),
        ),
        CapabilityManifest(
            id="demo.uncancellable_action",
            version=1,
            title="Uncancellable action",
            category="Demo",
            inputs={
                "duration_ms": ValueSpec(type=ValueType.DURATION_MS, default=100),
            },
            outputs={"completed": ValueSpec(type=ValueType.BOOLEAN, required=True)},
            execution=ExecutionTraits(timeout_ms=5_000, cancellable=False),
        ),
    )

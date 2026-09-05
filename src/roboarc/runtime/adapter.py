"""Adapter boundary between the RoboArc runtime and robot-native operations."""

from __future__ import annotations

import asyncio
from enum import StrEnum
from typing import Protocol

from roboarc.contracts import (
    CapabilityManifest,
    CapabilityRef,
    CapabilityResult,
    RobotProfile,
)
from roboarc.runtime.context import ExecutionContext


class CancellationDisposition(StrEnum):
    """Truthful response to a request to stop a native operation."""

    ACCEPTED = "accepted"
    UNSUPPORTED = "unsupported"
    ALREADY_COMPLETE = "already_complete"


class CapabilityInvocation(Protocol):
    """One in-flight native capability operation."""

    async def result(self) -> CapabilityResult:
        """Wait for the terminal native result."""

    async def request_cancel(self) -> CancellationDisposition:
        """Request native cancellation without implying that it has completed."""

    async def detach(self) -> None:
        """Release local observation after the runtime stops waiting for the operation."""


class TaskInvocation:
    """Task-backed invocation shared by deterministic adapters."""

    def __init__(
        self,
        task: asyncio.Task[CapabilityResult],
        cancel_event: asyncio.Event,
        cancellable: bool = True,
    ) -> None:
        self._task, self._cancel_event, self._cancellable = task, cancel_event, cancellable

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
        self._task.add_done_callback(
            lambda task: task.exception() if not task.cancelled() else None
        )


class CapabilityAdapter(Protocol):
    """Robot profile and invocation factory consumed by the runtime core."""

    @property
    def profile(self) -> RobotProfile:
        """Return the active robot profile."""

    @property
    def manifests(self) -> tuple[CapabilityManifest, ...]:
        """Return all manifests implemented by this adapter."""

    async def invoke(
        self,
        capability: CapabilityRef,
        args: dict[str, object],
        context: ExecutionContext,
    ) -> CapabilityInvocation:
        """Start an operation and return its lifecycle handle."""

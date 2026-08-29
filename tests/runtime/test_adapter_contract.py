from __future__ import annotations

import asyncio

import pytest

from roboarc.contracts import (
    CapabilityManifest,
    CapabilityRef,
    CapabilityResult,
    ErrorCode,
    ExecutionTraits,
    ResultStatus,
    RobotProfile,
    RunState,
    ValueSpec,
    ValueType,
    WorkflowDocument,
)
from roboarc.runtime import CancellationDisposition, Runtime, RuntimeConfig
from roboarc.runtime.context import ExecutionContext


class _TimedInvocation:
    def __init__(self) -> None:
        self.cancel_event = asyncio.Event()

    async def result(self) -> CapabilityResult:
        await self.cancel_event.wait()
        return CapabilityResult(status=ResultStatus.CANCELED)

    async def request_cancel(self) -> CancellationDisposition:
        self.cancel_event.set()
        return CancellationDisposition.ACCEPTED

    async def detach(self) -> None:
        return None


class _TimeoutAdapter:
    manifest = CapabilityManifest(
        id="test.slow",
        version=1,
        title="Slow",
        category="Test",
        execution=ExecutionTraits(timeout_ms=5, cancellable=True),
    )

    @property
    def profile(self) -> RobotProfile:
        return RobotProfile(
            id="timeout-test",
            title="Timeout test",
            adapter="timeout-test",
            capabilities=(self.manifest.ref,),
        )

    @property
    def manifests(self) -> tuple[CapabilityManifest, ...]:
        return (self.manifest,)

    async def invoke(
        self,
        capability: CapabilityRef,
        args: dict[str, object],
        context: ExecutionContext,
    ) -> _TimedInvocation:
        del capability, args, context
        return _TimedInvocation()


class _BadOutputInvocation:
    async def result(self) -> CapabilityResult:
        return CapabilityResult(status=ResultStatus.SUCCESS, output={})

    async def request_cancel(self) -> CancellationDisposition:
        return CancellationDisposition.ALREADY_COMPLETE

    async def detach(self) -> None:
        return None


class _BadOutputAdapter:
    manifest = CapabilityManifest(
        id="test.bad_output",
        version=1,
        title="Bad output",
        category="Test",
        outputs={"value": ValueSpec(type=ValueType.STRING, required=True)},
    )

    @property
    def profile(self) -> RobotProfile:
        return RobotProfile(
            id="bad-output-test",
            title="Bad output test",
            adapter="bad-output-test",
            capabilities=(self.manifest.ref,),
        )

    @property
    def manifests(self) -> tuple[CapabilityManifest, ...]:
        return (self.manifest,)

    async def invoke(
        self,
        capability: CapabilityRef,
        args: dict[str, object],
        context: ExecutionContext,
    ) -> _BadOutputInvocation:
        del capability, args, context
        return _BadOutputInvocation()


def _workflow(capability_id: str) -> WorkflowDocument:
    return WorkflowDocument.model_validate(
        {
            "workflow_schema_version": 1,
            "id": "adapter-contract-test",
            "name": "Adapter contract test",
            "workflow": {
                "id": "action",
                "type": "capability",
                "capability": {"id": capability_id, "version": 1},
                "args": {},
            },
        }
    )


@pytest.mark.asyncio
async def test_timeout_is_reported_only_after_native_terminal_acknowledgement() -> None:
    runtime = Runtime(_TimeoutAdapter(), config=RuntimeConfig(cancel_grace_ms=50))
    result = await runtime.run(_workflow("test.slow"))

    assert result.state is RunState.TIMED_OUT
    assert result.error is not None
    assert result.error.code is ErrorCode.CAPABILITY_TIMEOUT
    assert result.error.details["terminal_status"] == "canceled"


@pytest.mark.asyncio
async def test_invalid_adapter_output_is_a_contract_failure() -> None:
    runtime = Runtime(_BadOutputAdapter())
    result = await runtime.run(_workflow("test.bad_output"))

    assert result.state is RunState.FAILED
    assert result.error is not None
    assert result.error.code is ErrorCode.ADAPTER_CONTRACT_VIOLATION

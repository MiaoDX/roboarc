from __future__ import annotations

import asyncio

import pytest

from roboarc.contracts import ErrorCode, EventType, RunState, WorkflowDocument
from roboarc.runtime import MockAdapter, Runtime, RuntimeConfig


def workflow_for(capability_id: str, args: dict[str, object] | None = None) -> WorkflowDocument:
    return WorkflowDocument.model_validate(
        {
            "workflow_schema_version": 1,
            "id": "runtime-test",
            "name": "Runtime test",
            "workflow": {
                "id": "root",
                "type": "sequence",
                "children": [
                    {
                        "id": "action",
                        "type": "capability",
                        "capability": {"id": capability_id, "version": 1},
                        "args": args or {},
                    },
                    {"id": "after", "type": "wait", "duration_ms": 1},
                ],
            },
        }
    )


@pytest.mark.asyncio
async def test_successful_sequence_has_monotonic_observable_events() -> None:
    adapter = MockAdapter()
    runtime = Runtime(adapter)
    handle = await runtime.start(workflow_for("demo.staged_action", {"stage_delay_ms": 1}))
    result = await handle.result()
    events = handle.stream.snapshot()

    assert result.state is RunState.SUCCEEDED
    assert [event.seq for event in events] == list(range(1, len(events) + 1))
    assert events[0].type is EventType.RUN_STARTED
    assert events[-1].type is EventType.RUN_FINISHED
    assert len([event for event in events if event.type is EventType.CAPABILITY_PROGRESS]) == 3
    await adapter.wait_for_idle()


@pytest.mark.asyncio
async def test_failure_is_fail_fast() -> None:
    adapter = MockAdapter()
    runtime = Runtime(adapter)
    handle = await runtime.start(workflow_for("demo.fail", {"message": "expected"}))
    result = await handle.result()
    events = handle.stream.snapshot()

    assert result.state is RunState.FAILED
    assert result.error is not None
    assert result.error.message == "expected"
    assert not any(event.node_id == "after" for event in events)
    await adapter.wait_for_idle()


@pytest.mark.asyncio
async def test_cancellable_operation_only_reports_canceled_after_acknowledgement() -> None:
    adapter = MockAdapter()
    runtime = Runtime(adapter, config=RuntimeConfig(cancel_grace_ms=100))
    handle = await runtime.start(
        workflow_for(
            "demo.cancellable_action",
            {"duration_ms": 500, "tick_ms": 5, "cleanup_ms": 5},
        )
    )
    await asyncio.sleep(0.02)
    assert await handle.cancel()
    result = await handle.result()

    assert result.state is RunState.CANCELED
    events = handle.stream.snapshot()
    cancel_event = next(event for event in events if event.type is EventType.NODE_CANCEL_REQUESTED)
    finish_event = next(
        event
        for event in events
        if event.type is EventType.NODE_FINISHED and event.node_id == "action"
    )
    assert cancel_event.seq < finish_event.seq
    assert finish_event.data["state"] == "canceled"
    await adapter.wait_for_idle()


@pytest.mark.asyncio
async def test_uncancellable_operation_does_not_lie_about_cancellation() -> None:
    adapter = MockAdapter()
    runtime = Runtime(adapter, config=RuntimeConfig(cancel_grace_ms=5))
    handle = await runtime.start(
        workflow_for("demo.uncancellable_action", {"duration_ms": 30})
    )
    await asyncio.sleep(0.002)
    await handle.cancel()
    result = await handle.result()

    assert result.state is RunState.FAILED
    assert result.error is not None
    assert result.error.code is ErrorCode.CANCELLATION_INCOMPLETE
    await adapter.wait_for_idle()

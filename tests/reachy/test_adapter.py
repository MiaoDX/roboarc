from __future__ import annotations

from datetime import UTC, datetime
from pathlib import Path
from typing import Any

import pytest

from roboarc.contracts import EventType, ResultStatus, WorkflowDocument
from roboarc.runtime import Runtime
from roboarc.runtime.adapter import CancellationDisposition
from roboarc.runtime.context import ExecutionContext
from roboarc_reachy import ReachyAdapter
from roboarc_reachy.fake_sdk import FakeReachy, FakeReachyArm
from roboarc_reachy.profile import ARM_POSE_JOINTS, JOINT_FIELDS, REACHY_PROFILE


def args(side="left", duration_ms=0):
    return {
        "side": side,
        **{field: index * 5.0 for index, field in enumerate(JOINT_FIELDS, 1)},
        "duration_ms": duration_ms,
    }


def context(events):
    async def emit(kind: EventType, data: dict[str, Any]) -> None:
        events.append((kind, data, datetime.now(UTC)))

    return ExecutionContext("run", "node", "invocation", emit)


@pytest.mark.asyncio
async def test_profile_and_validation():
    assert REACHY_PROFILE.id == "reachy2-sim"
    result = await (await ReachyAdapter().invoke(ARM_POSE_JOINTS.ref, {}, context([]))).result()
    assert result.status is ResultStatus.FAILURE and result.error.code.value == "validation_error"


@pytest.mark.asyncio
async def test_success_sdk_shape_progress_and_non_cancellable():
    events = []
    robot = FakeReachy()
    invocation = await ReachyAdapter(robot).invoke(
        ARM_POSE_JOINTS.ref, args("right", 100), context(events)
    )
    assert await invocation.request_cancel() is CancellationDisposition.UNSUPPORTED
    result = await invocation.result()
    assert result.status is ResultStatus.SUCCESS and result.output == {
        "side": "right",
        "completed": True,
    }
    assert (
        robot.r_arm.positions == tuple(index * 5.0 for index in range(1, 8))
        and robot.send_count == 2
    )
    assert [data["percent"] for _, data, _ in events] == [50.0, 100.0]
    assert all(
        data["source"] == "estimated" and timestamp.tzinfo is UTC for _, data, timestamp in events
    )


@pytest.mark.asyncio
async def test_sdk_error_propagates():
    invocation = await ReachyAdapter(
        FakeReachy(l_arm=FakeReachyArm(fail=RuntimeError("servo fault")))
    ).invoke(ARM_POSE_JOINTS.ref, args(), context([]))
    result = await invocation.result()
    assert result.status is ResultStatus.FAILURE and result.error.message == "servo fault"


@pytest.mark.asyncio
async def test_example_runs_through_runtime():
    workflow_path = Path("examples/workflows/reachy-observable.json")
    workflow = WorkflowDocument.model_validate_json(
        workflow_path.read_text(encoding="utf-8")
    )
    handle = await Runtime(ReachyAdapter()).start(workflow)
    assert (await handle.result()).state.value == "succeeded"

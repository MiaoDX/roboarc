from __future__ import annotations

import json
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

import pytest

from roboarc.contracts import EventType, ResultStatus, WorkflowDocument
from roboarc.runtime import Runtime
from roboarc.runtime.adapter import CancellationDisposition
from roboarc.runtime.context import ExecutionContext
from roboarc_reachy import ReachyAdapter
from roboarc_reachy.adapter import GESTURE_POSES
from roboarc_reachy.fake_sdk import FakeReachy, FakeReachyArm
from roboarc_reachy.profile import ARM_GESTURE, REACHY_PROFILE


def args(side="left", duration_ms=100, gesture="raise"):
    return {"gesture": gesture, "side": side, "duration_ms": duration_ms}


def context(events):
    async def emit(kind: EventType, data: dict[str, Any]) -> None:
        events.append((kind, data, datetime.now(UTC)))

    return ExecutionContext("run", "node", "invocation", emit)


@pytest.mark.asyncio
async def test_profile_and_validation():
    assert REACHY_PROFILE.id == "reachy2-sim"
    result = await (await ReachyAdapter().invoke(ARM_GESTURE.ref, {}, context([]))).result()
    assert result.status is ResultStatus.FAILURE and result.error.code.value == "validation_error"


@pytest.mark.asyncio
async def test_success_sdk_shape_progress_and_non_cancellable():
    events = []
    robot = FakeReachy()
    invocation = await ReachyAdapter(robot).invoke(
        ARM_GESTURE.ref, args("right", 100), context(events)
    )
    assert await invocation.request_cancel() is CancellationDisposition.UNSUPPORTED
    result = await invocation.result()
    assert result.status is ResultStatus.SUCCESS and result.output == {
        "gesture": "raise", "side": "right",
        "completed": True,
    }
    assert (
        robot.r_arm.positions == (0.0, -40.0, 0.0, -90.0, 0.0, 0.0, 0.0)
        and robot.send_count == 4
    )
    assert [data["percent"] for _, data, _ in events] == [25.0, 50.0, 75.0, 100.0]
    assert all(
        data["source"] == "estimated" and timestamp.tzinfo is UTC for _, data, timestamp in events
    )


@pytest.mark.asyncio
async def test_wave_uses_a_visible_multi_joint_trajectory():
    robot = FakeReachy()
    invocation = await ReachyAdapter(robot).invoke(
        ARM_GESTURE.ref, args(duration_ms=500, gesture="wave"), context([])
    )

    assert (await invocation.result()).status is ResultStatus.SUCCESS
    targets = robot.l_arm.targets
    assert len(targets) > len(GESTURE_POSES["wave"])
    assert targets[0] != GESTURE_POSES["wave"][0]
    assert GESTURE_POSES["wave"][0] in targets
    assert len({target[2] for target in targets}) > 1
    assert len({target[3] for target in targets}) > 1
    assert len({target[6] for target in targets}) > 1


@pytest.mark.asyncio
async def test_sdk_error_propagates():
    invocation = await ReachyAdapter(
        FakeReachy(l_arm=FakeReachyArm(fail=RuntimeError("servo fault")))
    ).invoke(ARM_GESTURE.ref, args(), context([]))
    result = await invocation.result()
    assert result.status is ResultStatus.FAILURE and result.error.message == "servo fault"


@pytest.mark.asyncio
async def test_example_runs_through_runtime():
    workflow_path = Path("examples/workflows/reachy-observable.json")
    workflow_data = json.loads(workflow_path.read_text(encoding="utf-8"))
    for node in workflow_data["workflow"]["children"]:
        node["args"]["duration_ms"] = 100
    workflow = WorkflowDocument.model_validate(workflow_data)
    handle = await Runtime(ReachyAdapter()).start(workflow)
    assert (await handle.result()).state.value == "succeeded"

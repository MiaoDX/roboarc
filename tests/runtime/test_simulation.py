from __future__ import annotations

import asyncio

import pytest

from roboarc.contracts import EventType, RunState, WorkflowDocument
from roboarc.runtime import Runtime, RuntimeConfig
from roboarc.runtime.simulation import DeterministicSimulationAdapter, SimulatedPose


def _workflow(args: dict[str, object]) -> WorkflowDocument:
    return WorkflowDocument.model_validate(
        {
            "workflow_schema_version": 1,
            "id": "simulation-test",
            "name": "Simulation test",
            "workflow": {
                "id": "navigate",
                "type": "capability",
                "capability": {"id": "simulation.navigate", "version": 1},
                "args": args,
            },
        }
    )


@pytest.mark.asyncio
async def test_navigation_emits_correlated_pose_trajectory_and_progress() -> None:
    adapter = DeterministicSimulationAdapter(step_ms=1)
    runtime = Runtime(adapter)
    handle = await runtime.start(_workflow({"target_x": 2, "target_y": -1, "duration_ms": 3}))
    result = await handle.result()

    assert result.state is RunState.SUCCEEDED
    assert adapter.pose == SimulatedPose(2.0, -1.0)
    records = adapter.telemetry
    assert [record.kind for record in records] == [
        "action.state",
        "action.state",
        "robot.pose",
        "robot.trajectory",
        "capability.progress",
        "robot.pose",
        "robot.trajectory",
        "capability.progress",
        "robot.pose",
        "robot.trajectory",
        "capability.progress",
        "action.state",
    ]
    assert records[0].data["state"] == "accepted"
    assert records[-1].data["state"] == "succeeded"
    assert {record.run_id for record in records} == {handle.run_id}
    assert {record.node_id for record in records} == {"navigate"}
    assert len({record.invocation_id for record in records}) == 1
    events = handle.stream.snapshot()
    progress = [event for event in events if event.type is EventType.CAPABILITY_PROGRESS]
    assert len(progress) == 3
    assert [event.data["percent"] for event in progress] == [
        pytest.approx(100 / 3),
        pytest.approx(200 / 3),
        100.0,
    ]
    assert all(event.data["source"] == "estimated" for event in progress)
    await adapter.wait_for_idle()


@pytest.mark.asyncio
async def test_simulation_state_evolution_is_repeatable() -> None:
    adapter = DeterministicSimulationAdapter(step_ms=1)
    runtime = Runtime(adapter)
    workflow = _workflow({"target_x": 1.5, "target_y": 3, "duration_ms": 2})

    first = await runtime.run(workflow)
    first_samples = tuple(
        record.data for record in adapter.telemetry if record.kind == "robot.pose"
    )
    adapter.reset()
    second = await runtime.run(workflow)
    second_samples = tuple(
        record.data for record in adapter.telemetry if record.kind == "robot.pose"
    )

    assert first.state is second.state is RunState.SUCCEEDED
    assert first_samples == second_samples


@pytest.mark.asyncio
async def test_simulation_cancellation_records_terminal_canceled_action() -> None:
    adapter = DeterministicSimulationAdapter(step_ms=5)
    runtime = Runtime(adapter, config=RuntimeConfig(cancel_grace_ms=100))
    handle = await runtime.start(_workflow({"target_x": 10, "target_y": 0, "duration_ms": 200}))
    await asyncio.sleep(0.01)
    assert await handle.cancel()
    result = await handle.result()

    assert result.state is RunState.CANCELED
    assert adapter.telemetry[-1].kind == "action.state"
    assert adapter.telemetry[-1].data["state"] == "canceled"
    await adapter.wait_for_idle()

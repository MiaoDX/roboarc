from __future__ import annotations

from itertools import pairwise

import pytest

from roboarc.contracts import EventType, RunState
from roboarc.runtime import DeterministicSimulationAdapter, Runtime
from roboarc_reachy import ReachyAdapter


@pytest.mark.asyncio
async def test_profile_appropriate_workflows_preserve_runtime_invariants(workflow_document) -> None:
    simulation = DeterministicSimulationAdapter(step_ms=10)
    cases = (
        (
            simulation,
            workflow_document(
                profile_id="deterministic-simulation",
                capability_id="simulation.navigate",
                args={"target_x": 1.0, "target_y": 0.5, "duration_ms": 20},
                document_id="deterministic-simulation-observable",
                name="deterministic-simulation observable workflow",
                node_id="visible-motion",
            ),
        ),
        (
            ReachyAdapter(),
            workflow_document(
                profile_id="reachy2-sim",
                capability_id="reachy.arm.gesture",
                args={
                    "gesture": "raise",
                    "side": "left",
                    "duration_ms": 100,
                },
                document_id="reachy2-sim-observable",
                name="reachy2-sim observable workflow",
                node_id="visible-motion",
            ),
        ),
    )

    for adapter, workflow in cases:
        handle = await Runtime(adapter).start(workflow)
        result = await handle.result()
        events = handle.stream.history

        assert result.state is RunState.SUCCEEDED
        assert handle.profile_id == workflow.profile_id
        assert [event.type for event in events] == [
            EventType.RUN_STARTED,
            EventType.NODE_STARTED,
            *[event.type for event in events if event.type is EventType.CAPABILITY_PROGRESS],
            EventType.NODE_FINISHED,
            EventType.RUN_FINISHED,
        ]
        correlated = [event for event in events if event.node_id is not None]
        assert {event.node_id for event in correlated} == {"visible-motion"}
        invocation_ids = {
            event.data.get("invocation_id")
            for event in correlated
            if event.data.get("invocation_id") is not None
        }
        assert len(invocation_ids) == 1
        assert all(
            left.occurred_at <= right.occurred_at
            for left, right in pairwise(events)
        )

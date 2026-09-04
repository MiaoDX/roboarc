from __future__ import annotations

from itertools import pairwise

import pytest

from roboarc.contracts import EventType, RunState, WorkflowDocument
from roboarc.runtime import DeterministicSimulationAdapter, Runtime
from roboarc_reachy import ReachyAdapter
from roboarc_reachy.profile import JOINT_FIELDS


def _workflow(profile_id: str, capability_id: str, args: dict[str, object]) -> WorkflowDocument:
    return WorkflowDocument.model_validate(
        {
            "workflow_schema_version": 1,
            "id": f"{profile_id}-observable",
            "name": f"{profile_id} observable workflow",
            "profile_id": profile_id,
            "workflow": {
                "id": "visible-motion",
                "type": "capability",
                "capability": {"id": capability_id, "version": 1},
                "args": args,
            },
        }
    )


@pytest.mark.asyncio
async def test_profile_appropriate_workflows_preserve_runtime_invariants() -> None:
    simulation = DeterministicSimulationAdapter(step_ms=10)
    cases = (
        (
            simulation,
            _workflow(
                "deterministic-simulation",
                "simulation.navigate",
                {"target_x": 1.0, "target_y": 0.5, "duration_ms": 20},
            ),
        ),
        (
            ReachyAdapter(),
            _workflow(
                "reachy2-sim",
                "reachy.arm.pose_joints",
                {
                    "side": "left",
                    **{field: 10.0 for field in JOINT_FIELDS},
                    "duration_ms": 50,
                },
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

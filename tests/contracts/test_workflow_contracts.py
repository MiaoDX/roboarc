from __future__ import annotations

import json
from pathlib import Path

import pytest
from pydantic import ValidationError

from roboarc.contracts import WorkflowDocument


def test_example_workflow_parses() -> None:
    path = Path("examples/workflows/mock-demo.json")
    workflow = WorkflowDocument.model_validate_json(path.read_text(encoding="utf-8"))
    assert workflow.workflow.id == "root"


def test_workflow_rejects_duplicate_node_ids() -> None:
    payload = {
        "workflow_schema_version": 1,
        "id": "duplicate-test",
        "name": "Duplicate test",
        "workflow": {
            "id": "root",
            "type": "sequence",
            "children": [
                {"id": "same", "type": "wait", "duration_ms": 1},
                {"id": "same", "type": "wait", "duration_ms": 1},
            ],
        },
    }
    with pytest.raises(ValidationError, match="duplicate workflow node id"):
        WorkflowDocument.model_validate(payload)


def test_workflow_rejects_unknown_fields() -> None:
    payload = {
        "workflow_schema_version": 1,
        "id": "strict-test",
        "name": "Strict test",
        "workflow": {"id": "root", "type": "wait", "duration_ms": 1, "surprise": True},
    }
    with pytest.raises(ValidationError, match="Extra inputs"):
        WorkflowDocument.model_validate(payload)


def test_capability_args_must_be_json_data() -> None:
    payload = {
        "workflow_schema_version": 1,
        "id": "json-test",
        "name": "JSON test",
        "workflow": {
            "id": "root",
            "type": "capability",
            "capability": {"id": "demo.action", "version": 1},
            "args": {"bad": object()},
        },
    }
    with pytest.raises(ValidationError, match="JSON-serializable"):
        WorkflowDocument.model_validate(payload)


def test_workflow_json_round_trip_is_stable() -> None:
    original = json.loads(Path("examples/workflows/mock-demo.json").read_text(encoding="utf-8"))
    workflow = WorkflowDocument.model_validate(original)
    reparsed = WorkflowDocument.model_validate(workflow.model_dump(mode="json"))
    assert reparsed == workflow

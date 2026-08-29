from __future__ import annotations

from roboarc.contracts import WorkflowDocument
from roboarc.runtime import MockAdapter, Runtime


def test_unknown_capability_is_rejected_before_execution() -> None:
    workflow = WorkflowDocument.model_validate(
        {
            "workflow_schema_version": 1,
            "id": "unknown-test",
            "name": "Unknown capability",
            "workflow": {
                "id": "root",
                "type": "capability",
                "capability": {"id": "missing.action", "version": 1},
                "args": {},
            },
        }
    )
    report = Runtime(MockAdapter()).validate(workflow)
    assert not report.valid
    assert report.issues[0].code == "unknown_capability"
    assert report.issues[0].node_id == "root"


def test_arguments_are_strict_and_typed() -> None:
    workflow = WorkflowDocument.model_validate(
        {
            "workflow_schema_version": 1,
            "id": "args-test",
            "name": "Arguments",
            "workflow": {
                "id": "root",
                "type": "capability",
                "capability": {"id": "demo.percent_action", "version": 1},
                "args": {"steps": True, "extra": 1},
            },
        }
    )
    report = Runtime(MockAdapter()).validate(workflow)
    assert {issue.code for issue in report.issues} == {"invalid_input", "unknown_input"}

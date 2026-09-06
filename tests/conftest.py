from __future__ import annotations

from collections.abc import Callable
from typing import Any

import pytest

from roboarc.contracts import WorkflowDocument


@pytest.fixture
def workflow_document() -> Callable[..., WorkflowDocument]:
    """Build a small capability workflow for runtime and adapter tests."""

    def build(
        *,
        capability_id: str,
        args: dict[str, Any] | None = None,
        document_id: str = "test-workflow",
        name: str = "Test workflow",
        profile_id: str | None = None,
        node_id: str = "action",
        version: int = 1,
        wait_after_ms: int | None = None,
    ) -> WorkflowDocument:
        capability = {
            "id": node_id,
            "type": "capability",
            "capability": {"id": capability_id, "version": version},
            "args": args or {},
        }
        workflow: dict[str, Any] = capability
        if wait_after_ms is not None:
            workflow = {
                "id": "root",
                "type": "sequence",
                "children": [
                    capability,
                    {"id": "after", "type": "wait", "duration_ms": wait_after_ms},
                ],
            }
        payload: dict[str, Any] = {
            "workflow_schema_version": 1,
            "id": document_id,
            "name": name,
            "workflow": workflow,
        }
        if profile_id is not None:
            payload["profile_id"] = profile_id
        return WorkflowDocument.model_validate(payload)

    return build

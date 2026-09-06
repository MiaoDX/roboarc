from __future__ import annotations

import pytest

from roboarc.contracts import (
    CapabilityManifest,
    CompatibilityReason,
    CompatibilityStatus,
    RobotProfile,
    WorkflowDocument,
)
from roboarc.runtime import MockAdapter, Runtime, WorkflowValidationError


class _NoInvokeAdapter:
    def __init__(
        self, profile_id: str, manifests: tuple[CapabilityManifest, ...]
    ) -> None:
        self.invocations = 0
        self._manifests = manifests
        self._profile = RobotProfile(
            id=profile_id,
            title=profile_id,
            adapter="test",
            capabilities=tuple(manifest.ref for manifest in manifests),
        )

    @property
    def profile(self) -> RobotProfile:
        return self._profile

    @property
    def manifests(self) -> tuple[CapabilityManifest, ...]:
        return self._manifests

    async def invoke(self, *args: object) -> None:
        self.invocations += 1
        raise AssertionError("preflight must block invocation")


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
    assert report.issues[0].code == "capability_missing"
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


def test_compatibility_report_is_node_keyed_and_conservative(workflow_document) -> None:
    manifest = CapabilityManifest(
        id="demo.action",
        version=1,
        title="Action",
        category="Demo",
        compatible_profiles=("declared-source",),
    )
    runtime = Runtime(_NoInvokeAdapter("active", (manifest,)))

    declared = runtime.compatibility(
        workflow_document(
            capability_id="demo.action",
            profile_id="declared-source",
            document_id="compatibility-test",
            name="Compatibility",
        )
    )
    assert declared.compatible
    assert declared.nodes["action"].status is CompatibilityStatus.COMPATIBLE
    assert (
        declared.nodes["action"].reason
        is CompatibilityReason.DECLARED_PROFILE_COMPATIBILITY
    )

    unknown = runtime.compatibility(
        workflow_document(
            capability_id="demo.action",
            profile_id="other-source",
            document_id="compatibility-test",
            name="Compatibility",
        )
    )
    assert not unknown.compatible
    assert unknown.nodes["action"].status is CompatibilityStatus.UNKNOWN
    assert unknown.nodes["action"].capability.version == 1

    incompatible = runtime.compatibility(
        workflow_document(
            capability_id="demo.action",
            version=2,
            document_id="compatibility-test",
            name="Compatibility",
        )
    )
    assert incompatible.nodes["action"].status is CompatibilityStatus.INCOMPATIBLE

    missing = runtime.compatibility(
        WorkflowDocument.model_validate(
            {
                "workflow_schema_version": 1,
                "id": "missing",
                "name": "Missing",
                "workflow": {
                    "id": "missing-node",
                    "type": "capability",
                    "capability": {"id": "other.action", "version": 1},
                },
            }
        )
    )
    assert missing.nodes["missing-node"].status is CompatibilityStatus.MISSING


@pytest.mark.asyncio
async def test_non_compatible_workflow_blocks_before_invocation(workflow_document) -> None:
    manifest = CapabilityManifest(
        id="demo.action", version=1, title="Action", category="Demo"
    )
    adapter = _NoInvokeAdapter("active", (manifest,))

    with pytest.raises(WorkflowValidationError) as raised:
        await Runtime(adapter).start(
            workflow_document(
                capability_id="demo.action",
                profile_id="foreign",
                document_id="compatibility-test",
                name="Compatibility",
            )
        )

    assert raised.value.report.issues[0].code == "profile_compatibility_unknown"
    assert adapter.invocations == 0

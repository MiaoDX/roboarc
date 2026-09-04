from __future__ import annotations

import pytest
from pydantic import ValidationError

from roboarc.contracts import (
    CapabilityManifest,
    CapabilityRef,
    ExecutionTraits,
    ProgressMode,
    ProgressSource,
    ProgressSpec,
    RobotProfile,
    ValueSpec,
    ValueType,
)


def test_percent_progress_requires_provenance() -> None:
    with pytest.raises(ValidationError, match="percent progress"):
        ProgressSpec(mode=ProgressMode.PERCENT)

    progress = ProgressSpec(mode=ProgressMode.PERCENT, source=ProgressSource.ESTIMATED)
    assert progress.source is ProgressSource.ESTIMATED


def test_manifest_rejects_duplicate_resources_and_invalid_field_names() -> None:
    with pytest.raises(ValidationError, match="duplicates"):
        CapabilityManifest(
            id="demo.action",
            version=1,
            title="Action",
            category="Demo",
            resources=("base_motion", "base_motion"),
        )

    with pytest.raises(ValidationError, match="field name"):
        CapabilityManifest(
            id="demo.action",
            version=1,
            title="Action",
            category="Demo",
            inputs={"not valid": ValueSpec(type=ValueType.STRING)},
        )


def test_profile_references_exact_contract_versions() -> None:
    profile = RobotProfile(
        id="mock",
        title="Mock Robot",
        adapter="mock",
        capabilities=(CapabilityRef(id="demo.action", version=1),),
    )
    assert profile.capabilities[0].version == 1


def test_manifest_v1_compatibility_metadata_is_optional() -> None:
    legacy = CapabilityManifest.model_validate(
        {
            "manifest_schema_version": 1,
            "id": "demo.action",
            "version": 1,
            "title": "Action",
            "category": "Demo",
        }
    )
    assert legacy.compatible_profiles == ()


def test_execution_timeout_is_bounded() -> None:
    with pytest.raises(ValidationError):
        ExecutionTraits(timeout_ms=0)


def test_value_spec_validates_defaults_and_constraints() -> None:
    with pytest.raises(ValidationError, match="invalid default"):
        ValueSpec(type=ValueType.INTEGER, default=True)

    with pytest.raises(ValidationError, match="only valid for numeric"):
        ValueSpec(type=ValueType.STRING, minimum=1)

    with pytest.raises(ValidationError, match="invalid enum value"):
        ValueSpec(type=ValueType.BOOLEAN, enum=(True, "yes"))

    with pytest.raises(ValidationError, match="JSON-serializable"):
        ValueSpec(type=ValueType.NUMBER, default=float("nan"))

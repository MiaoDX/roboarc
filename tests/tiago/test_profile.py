from __future__ import annotations

import json
from pathlib import Path

from roboarc.contracts import WorkflowDocument
from roboarc.runtime.adapter import CapabilityAdapter
from roboarc.runtime.registry import CapabilityRegistry
from roboarc_tiago.profile import TIAGO_MANIFESTS, TIAGO_PROFILE


def test_tiago_profile_exposes_exact_v1_capability_refs() -> None:
    assert [(ref.id, ref.version) for ref in TIAGO_PROFILE.capabilities] == [
        ("navigation.goto_location", 1),
        ("navigation.stop", 1),
        ("head.look_at", 1),
        ("speech.say", 1),
        ("community.say", 1),
    ]
    assert tuple(manifest.ref for manifest in TIAGO_MANIFESTS) == TIAGO_PROFILE.capabilities


def test_tiago_manifests_form_a_valid_registry() -> None:
    registry = CapabilityRegistry(TIAGO_PROFILE, TIAGO_MANIFESTS)
    assert registry.get(TIAGO_PROFILE.capabilities[0]).id == "navigation.goto_location"


def test_observable_workflow_uses_only_profile_contracts() -> None:
    path = Path(__file__).parents[2] / "examples/workflows/tiago-observable.json"
    workflow = WorkflowDocument.model_validate(json.loads(path.read_text(encoding="utf-8")))
    refs = []
    assert workflow.workflow.type == "sequence"
    for node in workflow.workflow.children:
        if node.type == "capability":
            refs.append(node.capability)
    assert tuple(refs) == TIAGO_PROFILE.capabilities


def test_ros_adapter_declares_runtime_boundary_without_importing_ros() -> None:
    source = (
        Path(__file__).parents[2] / "src/roboarc_tiago/adapter.py"
    ).read_text(encoding="utf-8")
    assert "class TiagoRosAdapter(CapabilityAdapter)" in source
    assert CapabilityAdapter.__module__ == "roboarc.runtime.adapter"

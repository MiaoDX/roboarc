"""Deterministic workflow and capability argument validation."""

from __future__ import annotations

from collections.abc import Iterator
from typing import Any

from roboarc.contracts import (
    CapabilityManifest,
    CapabilityNode,
    CompatibilityReason,
    CompatibilityReport,
    CompatibilityStatus,
    NodeCompatibility,
    SequenceNode,
    ValidationIssue,
    ValidationReport,
    ValueSpec,
    WorkflowDocument,
    WorkflowNode,
)
from roboarc.contracts.capability import validate_value_against_spec
from roboarc.runtime.registry import CapabilityRegistry


def iter_nodes(node: WorkflowNode) -> Iterator[WorkflowNode]:
    yield node
    if isinstance(node, SequenceNode):
        for child in node.children:
            yield from iter_nodes(child)


def validate_workflow(
    workflow: WorkflowDocument,
    registry: CapabilityRegistry,
) -> ValidationReport:
    issues: list[ValidationIssue] = []
    compatibility_nodes = compatibility_report(workflow, registry).nodes
    for node in iter_nodes(workflow.workflow):
        if not isinstance(node, CapabilityNode):
            continue
        compatibility = compatibility_nodes[node.id]
        if compatibility.status is not CompatibilityStatus.COMPATIBLE:
            issues.append(
                ValidationIssue(
                    code=compatibility.reason.value,
                    message=(
                        f"node is {compatibility.status.value} on active profile "
                        f"{registry.profile.id!r}: {compatibility.reason.value}"
                    ),
                    node_id=node.id,
                    path=f"node:{node.id}.capability",
                )
            )
            continue
        manifest = registry.require(node.capability)
        issues.extend(validate_values(node.args, manifest.inputs, node_id=node.id, kind="input"))

    return ValidationReport(valid=not issues, issues=tuple(issues))


def compatibility_report(
    workflow: WorkflowDocument,
    registry: CapabilityRegistry,
) -> CompatibilityReport:
    nodes: dict[str, NodeCompatibility] = {}
    active_profile_id = registry.profile.id
    for node in iter_nodes(workflow.workflow):
        if not isinstance(node, CapabilityNode):
            continue
        exact = registry.get(node.capability)
        available_versions = registry.versions(node.capability.id)
        if exact is None and not available_versions:
            status = CompatibilityStatus.MISSING
            reason = CompatibilityReason.CAPABILITY_MISSING
        elif exact is None:
            status = CompatibilityStatus.INCOMPATIBLE
            reason = CompatibilityReason.CAPABILITY_VERSION_MISMATCH
        elif workflow.profile_id is None or workflow.profile_id == active_profile_id:
            status = CompatibilityStatus.COMPATIBLE
            reason = CompatibilityReason.EXACT_CAPABILITY_MATCH
        elif workflow.profile_id in exact.compatible_profiles:
            status = CompatibilityStatus.COMPATIBLE
            reason = CompatibilityReason.DECLARED_PROFILE_COMPATIBILITY
        else:
            status = CompatibilityStatus.UNKNOWN
            reason = CompatibilityReason.PROFILE_COMPATIBILITY_UNKNOWN
        nodes[node.id] = NodeCompatibility(
            status=status,
            capability=node.capability,
            reason=reason,
        )
    return CompatibilityReport(
        active_profile_id=active_profile_id,
        source_profile_id=workflow.profile_id,
        compatible=all(
            node.status is CompatibilityStatus.COMPATIBLE for node in nodes.values()
        ),
        nodes=nodes,
    )


def normalize_arguments(manifest: CapabilityManifest, args: dict[str, Any]) -> dict[str, Any]:
    normalized = dict(args)
    for name, spec in manifest.inputs.items():
        if name not in normalized and spec.default is not None:
            normalized[name] = spec.default
    return normalized


def validate_output(
    manifest: CapabilityManifest,
    output: dict[str, Any],
    *,
    node_id: str,
) -> tuple[ValidationIssue, ...]:
    return tuple(validate_values(output, manifest.outputs, node_id=node_id, kind="output"))


def validate_values(
    values: dict[str, Any],
    specs: dict[str, ValueSpec],
    *,
    node_id: str,
    kind: str,
) -> list[ValidationIssue]:
    issues: list[ValidationIssue] = []
    unknown = sorted(set(values) - set(specs))
    for name in unknown:
        issues.append(
            ValidationIssue(
                code=f"unknown_{kind}",
                message=f"unknown capability {kind}: {name}",
                node_id=node_id,
                path=(
                    f"node:{node_id}.args.{name}"
                    if kind == "input"
                    else f"node:{node_id}.output.{name}"
                ),
            )
        )

    for name, spec in specs.items():
        if name not in values:
            if spec.required and spec.default is None:
                issues.append(
                    ValidationIssue(
                        code=f"missing_{kind}",
                        message=f"required capability {kind} is missing: {name}",
                        node_id=node_id,
                        path=(
                            f"node:{node_id}.args.{name}"
                            if kind == "input"
                            else f"node:{node_id}.output.{name}"
                        ),
                    )
                )
            continue
        message = validate_value_against_spec(values[name], spec)
        if message is not None:
            issues.append(
                ValidationIssue(
                    code=f"invalid_{kind}",
                    message=f"invalid {kind} {name!r}: {message}",
                    node_id=node_id,
                    path=(
                        f"node:{node_id}.args.{name}"
                        if kind == "input"
                        else f"node:{node_id}.output.{name}"
                    ),
                )
            )
    return issues

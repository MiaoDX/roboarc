"""Deterministic workflow and capability argument validation."""

from __future__ import annotations

from collections.abc import Iterator
from typing import Any

from roboarc.contracts import (
    CapabilityManifest,
    CapabilityNode,
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
    for node in iter_nodes(workflow.workflow):
        if not isinstance(node, CapabilityNode):
            continue
        manifest = registry.get(node.capability)
        if manifest is None:
            issues.append(
                ValidationIssue(
                    code="unknown_capability",
                    message=(
                        f"active profile {registry.profile.id!r} does not provide "
                        f"{node.capability.id}@{node.capability.version}"
                    ),
                    node_id=node.id,
                    path=f"node:{node.id}.capability",
                )
            )
            continue
        issues.extend(validate_values(node.args, manifest.inputs, node_id=node.id, kind="input"))

    return ValidationReport(valid=not issues, issues=tuple(issues))


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



"""Canonical editor-neutral Workflow IR contracts."""

from __future__ import annotations

from typing import Annotated, Any, Literal, TypeAlias

from pydantic import Field, field_validator, model_validator

from roboarc.contracts.capability import CapabilityRef
from roboarc.contracts.common import ContractModel, Identifier, is_json_value

MAX_WORKFLOW_NODES = 1_000
MAX_WORKFLOW_DEPTH = 64


class NodeBase(ContractModel):
    id: Identifier


class WaitNode(NodeBase):
    type: Literal["wait"] = "wait"
    duration_ms: int = Field(ge=0, le=86_400_000)


class CapabilityNode(NodeBase):
    type: Literal["capability"] = "capability"
    capability: CapabilityRef
    args: dict[str, Any] = Field(default_factory=dict)

    @field_validator("args")
    @classmethod
    def args_must_be_json(cls, value: dict[str, Any]) -> dict[str, Any]:
        if not is_json_value(value):
            raise ValueError("capability args must be JSON-serializable")
        return value


class SequenceNode(NodeBase):
    type: Literal["sequence"] = "sequence"
    children: tuple[WorkflowNode, ...] = Field(min_length=1)


WorkflowNode: TypeAlias = Annotated[
    SequenceNode | WaitNode | CapabilityNode,
    Field(discriminator="type"),
]

SequenceNode.model_rebuild(_types_namespace={"WorkflowNode": WorkflowNode})


class WorkflowDocument(ContractModel):
    """Executable v0.1 workflow document."""

    workflow_schema_version: Literal[1] = 1
    id: Identifier
    name: str = Field(min_length=1, max_length=200)
    workflow: WorkflowNode

    @model_validator(mode="after")
    def node_ids_and_shape_are_bounded(self) -> WorkflowDocument:
        ids: set[str] = set()
        count = 0

        def visit(node: WorkflowNode, depth: int) -> None:
            nonlocal count
            if depth > MAX_WORKFLOW_DEPTH:
                raise ValueError(f"workflow depth exceeds {MAX_WORKFLOW_DEPTH}")
            count += 1
            if count > MAX_WORKFLOW_NODES:
                raise ValueError(f"workflow contains more than {MAX_WORKFLOW_NODES} nodes")
            if node.id in ids:
                raise ValueError(f"duplicate workflow node id: {node.id}")
            ids.add(node.id)
            if isinstance(node, SequenceNode):
                for child in node.children:
                    visit(child, depth + 1)

        visit(self.workflow, 1)
        return self


class EditorState(ContractModel):
    editor_state_version: int = Field(default=1, ge=1)
    type: Literal["blockly"] = "blockly"
    state: dict[str, Any]

    @field_validator("state")
    @classmethod
    def state_must_be_json(cls, value: dict[str, Any]) -> dict[str, Any]:
        if not is_json_value(value):
            raise ValueError("editor state must be JSON-serializable")
        return value


class ProjectDocument(ContractModel):
    """Saved authoring project; editor state evolves separately from Workflow IR."""

    project_format_version: Literal[1] = 1
    name: str = Field(min_length=1, max_length=200)
    editor: EditorState | None = None
    workflow: WorkflowDocument

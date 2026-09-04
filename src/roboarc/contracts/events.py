"""Runtime event protocol and execution result contracts."""

from __future__ import annotations

from datetime import datetime
from enum import StrEnum
from typing import Any, Literal
from uuid import UUID, uuid4

from pydantic import Field, field_validator, model_validator

from roboarc.contracts.common import ContractModel, Identifier, is_json_value


class EventType(StrEnum):
    RUN_STARTED = "run.started"
    RUN_CANCEL_REQUESTED = "run.cancel_requested"
    RUN_FINISHED = "run.finished"
    NODE_STARTED = "node.started"
    NODE_CANCEL_REQUESTED = "node.cancel_requested"
    NODE_FINISHED = "node.finished"
    CAPABILITY_PROGRESS = "capability.progress"
    LOG = "log"
    ERROR = "error"


class RunState(StrEnum):
    PENDING = "pending"
    RUNNING = "running"
    CANCELING = "canceling"
    SUCCEEDED = "succeeded"
    FAILED = "failed"
    CANCELED = "canceled"
    TIMED_OUT = "timed_out"


class NodeState(StrEnum):
    PENDING = "pending"
    RUNNING = "running"
    CANCELING = "canceling"
    SUCCEEDED = "succeeded"
    FAILED = "failed"
    CANCELED = "canceled"
    TIMED_OUT = "timed_out"


class ResultStatus(StrEnum):
    SUCCESS = "success"
    FAILURE = "failure"
    CANCELED = "canceled"
    TIMEOUT = "timeout"


class ErrorCode(StrEnum):
    VALIDATION_ERROR = "validation_error"
    UNKNOWN_CAPABILITY = "unknown_capability"
    CAPABILITY_FAILED = "capability_failed"
    CAPABILITY_TIMEOUT = "capability_timeout"
    ADAPTER_CONTRACT_VIOLATION = "adapter_contract_violation"
    CANCELLATION_INCOMPLETE = "cancellation_incomplete"
    INTERNAL_ERROR = "internal_error"


class ExecutionError(ContractModel):
    code: ErrorCode
    message: str = Field(min_length=1, max_length=2000)
    details: dict[str, Any] = Field(default_factory=dict)

    @field_validator("details")
    @classmethod
    def details_must_be_json(cls, value: dict[str, Any]) -> dict[str, Any]:
        if not is_json_value(value):
            raise ValueError("error details must be JSON-serializable")
        return value


class RuntimeEvent(ContractModel):
    """Ordered, replayable event envelope sent to runtime clients."""

    event_protocol_version: Literal[1] = 1
    event_id: UUID = Field(default_factory=uuid4)
    seq: int = Field(ge=1)
    run_id: Identifier
    node_id: Identifier | None = None
    type: EventType
    occurred_at: datetime
    data: dict[str, Any] = Field(default_factory=dict)

    @field_validator("occurred_at")
    @classmethod
    def timestamp_must_be_timezone_aware(cls, value: datetime) -> datetime:
        if value.tzinfo is None or value.utcoffset() is None:
            raise ValueError("occurred_at must include a timezone")
        return value

    @field_validator("data")
    @classmethod
    def data_must_be_json(cls, value: dict[str, Any]) -> dict[str, Any]:
        if not is_json_value(value):
            raise ValueError("event data must be JSON-serializable")
        return value


class CapabilityResult(ContractModel):
    status: ResultStatus
    output: dict[str, Any] = Field(default_factory=dict)
    error: ExecutionError | None = None

    @field_validator("output")
    @classmethod
    def output_must_be_json(cls, value: dict[str, Any]) -> dict[str, Any]:
        if not is_json_value(value):
            raise ValueError("capability output must be JSON-serializable")
        return value

    @model_validator(mode="after")
    def status_matches_error(self) -> CapabilityResult:
        if self.status is ResultStatus.SUCCESS and self.error is not None:
            raise ValueError("successful capability results must not contain an error")
        if self.status in {ResultStatus.FAILURE, ResultStatus.TIMEOUT} and self.error is None:
            raise ValueError("failure and timeout results must contain an error")
        return self


class NodeResult(ContractModel):
    node_id: Identifier
    state: NodeState
    output: dict[str, Any] = Field(default_factory=dict)
    error: ExecutionError | None = None
    started_at: datetime
    finished_at: datetime


class RunResult(ContractModel):
    run_id: Identifier
    workflow_id: Identifier
    profile_id: Identifier | None = None
    state: RunState
    error: ExecutionError | None = None
    started_at: datetime
    finished_at: datetime

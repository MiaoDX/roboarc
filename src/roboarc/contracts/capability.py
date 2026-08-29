"""Capability and robot-profile contracts."""

from __future__ import annotations

import math
from enum import StrEnum
from typing import Any, Literal

from pydantic import Field, field_validator, model_validator

from roboarc.contracts.common import (
    ContractModel,
    Identifier,
    ResourceName,
    ensure_unique,
    is_json_value,
    validate_identifier,
)


class ValueType(StrEnum):
    """Small v0.1 value vocabulary shared by manifests and editors."""

    STRING = "string"
    INTEGER = "integer"
    NUMBER = "number"
    BOOLEAN = "boolean"
    DURATION_MS = "duration_ms"
    MAP_LOCATION = "map_location"


class ProgressMode(StrEnum):
    NONE = "none"
    STAGE = "stage"
    PERCENT = "percent"


class ProgressSource(StrEnum):
    NATIVE = "native"
    ESTIMATED = "estimated"


class CapabilityRef(ContractModel):
    """Exact reference to a capability contract version."""

    id: Identifier
    version: int = Field(ge=1)


class ValueSpec(ContractModel):
    """Minimal field schema suitable for validation and generated editors."""

    type: ValueType
    required: bool = False
    title: str | None = Field(default=None, min_length=1, max_length=120)
    description: str | None = Field(default=None, max_length=1000)
    default: Any | None = None
    enum: tuple[Any, ...] | None = None
    minimum: float | None = None
    maximum: float | None = None

    @field_validator("default")
    @classmethod
    def default_must_be_json(cls, value: Any) -> Any:
        if not is_json_value(value):
            raise ValueError("default must be JSON-serializable")
        return value

    @field_validator("enum")
    @classmethod
    def enum_values_must_be_json(cls, value: tuple[Any, ...] | None) -> tuple[Any, ...] | None:
        if value is None:
            return None
        if not value:
            raise ValueError("enum must contain at least one value")
        if not all(is_json_value(item) for item in value):
            raise ValueError("enum values must be JSON-serializable")
        return value

    @model_validator(mode="after")
    def validate_constraints(self) -> "ValueSpec":
        if self.minimum is not None and self.maximum is not None and self.minimum > self.maximum:
            raise ValueError("minimum must not be greater than maximum")
        if (self.minimum is not None or self.maximum is not None) and self.type not in {
            ValueType.INTEGER,
            ValueType.NUMBER,
            ValueType.DURATION_MS,
        }:
            raise ValueError("minimum and maximum are only valid for numeric value types")
        if self.default is not None:
            message = validate_value_against_spec(self.default, self)
            if message is not None:
                raise ValueError(f"invalid default: {message}")
        if self.enum is not None:
            for item in self.enum:
                message = validate_value_against_spec(item, self, check_enum=False)
                if message is not None:
                    raise ValueError(f"invalid enum value {item!r}: {message}")
            if any(
                left == right
                for index, left in enumerate(self.enum)
                for right in self.enum[index + 1 :]
            ):
                raise ValueError("enum values must be unique")
        return self


def validate_value_against_spec(
    value: Any,
    spec: ValueSpec,
    *,
    check_enum: bool = True,
) -> str | None:
    """Validate one primitive value against the shared manifest vocabulary."""

    type_error: str | None = None
    if spec.type is ValueType.STRING:
        if not isinstance(value, str):
            type_error = "expected string"
    elif spec.type is ValueType.INTEGER:
        if not isinstance(value, int) or isinstance(value, bool):
            type_error = "expected integer"
    elif spec.type is ValueType.NUMBER:
        if (
            not isinstance(value, (int, float))
            or isinstance(value, bool)
            or (isinstance(value, float) and not math.isfinite(value))
        ):
            type_error = "expected a finite number"
    elif spec.type is ValueType.BOOLEAN:
        if not isinstance(value, bool):
            type_error = "expected boolean"
    elif spec.type is ValueType.DURATION_MS:
        if not isinstance(value, int) or isinstance(value, bool) or value < 0:
            type_error = "expected a non-negative integer duration in milliseconds"
    elif spec.type is ValueType.MAP_LOCATION:
        if not isinstance(value, str) or not value.strip():
            type_error = "expected a non-empty map location identifier"

    if type_error is not None:
        return type_error
    if check_enum and spec.enum is not None and value not in spec.enum:
        return f"expected one of {list(spec.enum)!r}"
    if isinstance(value, (int, float)) and not isinstance(value, bool):
        if spec.minimum is not None and value < spec.minimum:
            return f"must be greater than or equal to {spec.minimum}"
        if spec.maximum is not None and value > spec.maximum:
            return f"must be less than or equal to {spec.maximum}"
    return None


class ExecutionTraits(ContractModel):
    timeout_ms: int = Field(default=30_000, ge=1, le=86_400_000)
    cancellable: bool = False


class ProgressSpec(ContractModel):
    mode: ProgressMode = ProgressMode.NONE
    source: ProgressSource | None = None

    @model_validator(mode="after")
    def source_matches_mode(self) -> "ProgressSpec":
        if self.mode is ProgressMode.PERCENT and self.source is None:
            raise ValueError("percent progress must declare native or estimated provenance")
        if self.mode is not ProgressMode.PERCENT and self.source is not None:
            raise ValueError("progress source is only valid for percent progress")
        return self


class CapabilityManifest(ContractModel):
    """Stable product-level behavior exposed by an adapter."""

    manifest_schema_version: Literal[1] = 1
    id: Identifier
    version: int = Field(ge=1)
    title: str = Field(min_length=1, max_length=120)
    category: str = Field(min_length=1, max_length=120)
    description: str | None = Field(default=None, max_length=2000)
    inputs: dict[str, ValueSpec] = Field(default_factory=dict)
    outputs: dict[str, ValueSpec] = Field(default_factory=dict)
    execution: ExecutionTraits = Field(default_factory=ExecutionTraits)
    progress: ProgressSpec = Field(default_factory=ProgressSpec)
    resources: tuple[ResourceName, ...] = ()

    @field_validator("inputs", "outputs")
    @classmethod
    def field_names_are_valid(cls, value: dict[str, ValueSpec]) -> dict[str, ValueSpec]:
        for name in value:
            validate_identifier(name, "capability field name")
        return value

    @field_validator("resources")
    @classmethod
    def resources_are_unique(cls, value: tuple[str, ...]) -> tuple[str, ...]:
        return ensure_unique(value, "resources")

    @property
    def ref(self) -> CapabilityRef:
        return CapabilityRef(id=self.id, version=self.version)


class RobotProfile(ContractModel):
    """Capabilities available through one adapter/configuration."""

    profile_schema_version: Literal[1] = 1
    id: Identifier
    title: str = Field(min_length=1, max_length=120)
    adapter: Identifier
    capabilities: tuple[CapabilityRef, ...]

    @field_validator("capabilities")
    @classmethod
    def capabilities_are_unique(
        cls, value: tuple[CapabilityRef, ...]
    ) -> tuple[CapabilityRef, ...]:
        keys = [(item.id, item.version) for item in value]
        if len(keys) != len(set(keys)):
            raise ValueError("capabilities must not contain duplicate id/version pairs")
        return value

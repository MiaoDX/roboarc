"""Shared contract primitives and validation helpers."""

from __future__ import annotations

import math
import re
from typing import Annotated, Any

from pydantic import BaseModel, ConfigDict, StringConstraints

IDENTIFIER_PATTERN = r"^[A-Za-z][A-Za-z0-9._-]{0,127}$"
FIELD_NAME_PATTERN = r"^[A-Za-z_][A-Za-z0-9_]{0,63}$"
RESOURCE_PATTERN = r"^[a-z][a-z0-9_.-]{0,127}$"

Identifier = Annotated[str, StringConstraints(pattern=IDENTIFIER_PATTERN)]
FieldName = Annotated[str, StringConstraints(pattern=FIELD_NAME_PATTERN)]
ResourceName = Annotated[str, StringConstraints(pattern=RESOURCE_PATTERN)]


class ContractModel(BaseModel):
    """Base class for externally visible, immutable contracts."""

    model_config = ConfigDict(extra="forbid", frozen=True, validate_default=True)


def ensure_unique(values: tuple[str, ...], field_name: str) -> tuple[str, ...]:
    """Reject duplicate identifiers while preserving declaration order."""

    if len(values) != len(set(values)):
        raise ValueError(f"{field_name} must not contain duplicates")
    return values


def is_json_value(value: Any) -> bool:
    """Return whether a value is representable as strict JSON data."""

    if isinstance(value, float):
        return math.isfinite(value)
    if value is None or isinstance(value, (str, bool, int)):
        return True
    if isinstance(value, list):
        return all(is_json_value(item) for item in value)
    if isinstance(value, dict):
        return all(isinstance(key, str) and is_json_value(item) for key, item in value.items())
    return False


def validate_identifier(value: str, label: str) -> str:
    """Validate dynamically keyed identifiers such as manifest field names."""

    if not re.fullmatch(FIELD_NAME_PATTERN, value):
        raise ValueError(f"invalid {label}: {value!r}")
    return value

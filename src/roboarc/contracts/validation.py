"""Static validation report contracts."""

from __future__ import annotations

from enum import StrEnum

from pydantic import Field

from roboarc.contracts.common import ContractModel, Identifier


class ValidationSeverity(StrEnum):
    ERROR = "error"
    WARNING = "warning"


class ValidationIssue(ContractModel):
    code: str = Field(min_length=1, max_length=120)
    message: str = Field(min_length=1, max_length=2000)
    severity: ValidationSeverity = ValidationSeverity.ERROR
    node_id: Identifier | None = None
    path: str | None = None


class ValidationReport(ContractModel):
    valid: bool
    issues: tuple[ValidationIssue, ...] = ()

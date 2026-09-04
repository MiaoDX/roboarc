"""Deterministic workflow compatibility report contracts."""

from __future__ import annotations

from enum import StrEnum

from roboarc.contracts.capability import CapabilityRef
from roboarc.contracts.common import ContractModel, Identifier


class CompatibilityStatus(StrEnum):
    COMPATIBLE = "compatible"
    MISSING = "missing"
    INCOMPATIBLE = "incompatible"
    UNKNOWN = "unknown"


class CompatibilityReason(StrEnum):
    EXACT_CAPABILITY_MATCH = "exact_capability_match"
    DECLARED_PROFILE_COMPATIBILITY = "declared_profile_compatibility"
    CAPABILITY_MISSING = "capability_missing"
    CAPABILITY_VERSION_MISMATCH = "capability_version_mismatch"
    PROFILE_COMPATIBILITY_UNKNOWN = "profile_compatibility_unknown"


class NodeCompatibility(ContractModel):
    status: CompatibilityStatus
    capability: CapabilityRef
    reason: CompatibilityReason


class CompatibilityReport(ContractModel):
    active_profile_id: Identifier
    source_profile_id: Identifier | None = None
    compatible: bool
    nodes: dict[Identifier, NodeCompatibility]

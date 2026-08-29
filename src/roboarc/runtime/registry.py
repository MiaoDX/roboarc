"""Capability manifest registry and adapter conformance checks."""

from __future__ import annotations

from collections.abc import Iterable

from roboarc.contracts import CapabilityManifest, CapabilityRef, RobotProfile
from roboarc.runtime.adapter import CapabilityAdapter

CapabilityKey = tuple[str, int]


class RegistryError(ValueError):
    """Raised when an adapter's profile and manifests do not form a valid registry."""


class CapabilityRegistry:
    def __init__(self, profile: RobotProfile, manifests: Iterable[CapabilityManifest]) -> None:
        mapping: dict[CapabilityKey, CapabilityManifest] = {}
        for manifest in manifests:
            key = (manifest.id, manifest.version)
            if key in mapping:
                raise RegistryError(
                    f"duplicate capability manifest: {manifest.id}@{manifest.version}"
                )
            mapping[key] = manifest

        declared = {(ref.id, ref.version) for ref in profile.capabilities}
        implemented = set(mapping)
        missing = declared - implemented
        extra = implemented - declared
        if missing:
            formatted = ", ".join(f"{item[0]}@{item[1]}" for item in sorted(missing))
            raise RegistryError(f"profile references missing manifests: {formatted}")
        if extra:
            formatted = ", ".join(f"{item[0]}@{item[1]}" for item in sorted(extra))
            raise RegistryError(f"adapter exposes manifests absent from profile: {formatted}")

        self._profile = profile
        self._manifests = mapping

    @classmethod
    def from_adapter(cls, adapter: CapabilityAdapter) -> "CapabilityRegistry":
        return cls(adapter.profile, adapter.manifests)

    @property
    def profile(self) -> RobotProfile:
        return self._profile

    @property
    def manifests(self) -> tuple[CapabilityManifest, ...]:
        return tuple(self._manifests.values())

    def get(self, ref: CapabilityRef) -> CapabilityManifest | None:
        return self._manifests.get((ref.id, ref.version))

    def require(self, ref: CapabilityRef) -> CapabilityManifest:
        manifest = self.get(ref)
        if manifest is None:
            raise KeyError(f"unknown capability: {ref.id}@{ref.version}")
        return manifest

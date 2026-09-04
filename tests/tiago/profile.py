"""TIAGo capability contracts kept independent from ROS imports."""

from __future__ import annotations

from dataclasses import dataclass

from roboarc.contracts import (
    CapabilityManifest,
    ExecutionTraits,
    ProgressMode,
    ProgressSpec,
    RobotProfile,
    ValueSpec,
    ValueType,
)

GOTO_LOCATION = CapabilityManifest(
    id="navigation.goto_location",
    version=1,
    title="Go to location",
    category="Navigation",
    inputs={"target": ValueSpec(type=ValueType.MAP_LOCATION, required=True)},
    outputs={"target": ValueSpec(type=ValueType.MAP_LOCATION, required=True)},
    execution=ExecutionTraits(timeout_ms=120_000, cancellable=True),
    progress=ProgressSpec(mode=ProgressMode.STAGE),
    resources=("base_motion",),
)

STOP_NAVIGATION = CapabilityManifest(
    id="navigation.stop",
    version=1,
    title="Stop navigation",
    category="Navigation",
    execution=ExecutionTraits(timeout_ms=5_000, cancellable=False),
    resources=("base_motion",),
)

LOOK_AT = CapabilityManifest(
    id="head.look_at",
    version=1,
    title="Look at point",
    category="Head",
    inputs={
        "frame": ValueSpec(type=ValueType.STRING, default="base_footprint"),
        "x": ValueSpec(type=ValueType.NUMBER, required=True),
        "y": ValueSpec(type=ValueType.NUMBER, required=True),
        "z": ValueSpec(type=ValueType.NUMBER, required=True),
    },
    execution=ExecutionTraits(timeout_ms=15_000, cancellable=True),
    progress=ProgressSpec(mode=ProgressMode.STAGE),
    resources=("head",),
)

SAY = CapabilityManifest(
    id="speech.say",
    version=1,
    title="Say text",
    category="Speech",
    inputs={"text": ValueSpec(type=ValueType.STRING, required=True)},
    execution=ExecutionTraits(timeout_ms=10_000, cancellable=False),
    resources=("speech",),
)

TIAGO_MANIFESTS = (GOTO_LOCATION, STOP_NAVIGATION, LOOK_AT, SAY)

TIAGO_PROFILE = RobotProfile(
    id="tiago-sim",
    title="TIAGo Gazebo",
    adapter="tiago-ros2",
    capabilities=tuple(manifest.ref for manifest in TIAGO_MANIFESTS),
)


@dataclass(frozen=True, slots=True)
class NamedLocation:
    """A map-frame planar Nav2 goal."""

    x: float
    y: float
    yaw: float = 0.0


DEFAULT_LOCATIONS = {
    "reception": NamedLocation(1.0, 0.0),
    "home": NamedLocation(0.0, 0.0),
}

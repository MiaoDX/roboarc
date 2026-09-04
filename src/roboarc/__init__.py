"""RoboArc core package."""

from roboarc.contracts import (
    CapabilityManifest,
    CapabilityNode,
    CapabilityRef,
    ProjectDocument,
    RobotProfile,
    RuntimeEvent,
    SequenceNode,
    WaitNode,
    WorkflowDocument,
)

__all__ = [
    "CapabilityManifest",
    "CapabilityNode",
    "CapabilityRef",
    "ProjectDocument",
    "RobotProfile",
    "RuntimeEvent",
    "SequenceNode",
    "WaitNode",
    "WorkflowDocument",
]

__version__ = "0.1.0.dev0"

from roboarc.telemetry import Observation, observations, write_trace

__all__ += ["Observation", "observations", "write_trace"]

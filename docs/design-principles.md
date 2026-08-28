# Design Principles

These principles are intended to keep RoboArc small while preserving the architectural boundaries needed for real robots.

## 1. Capabilities over robot APIs

Visual workflows should use stable behaviors such as `navigation.goto`, not raw topic names, REST endpoints, or vendor method signatures.

Native interfaces belong behind adapters.

## 2. Workflow IR over editor state

Blockly serialization preserves the editing experience. The typed Workflow IR defines program semantics.

This separation allows other authoring surfaces to be added without changing the runtime contract.

## 3. Adapters over platform coupling

The runtime core should not depend on ROS 2 or a particular robot. ROS 2, Python SDKs, REST, gRPC, and other transports are implementation choices of robot adapters.

## 4. Progressive enhancement over mandatory features

A capability must return a result. Richer execution traits are optional.

For example, a robot API may initially expose only start/end semantics. An adapter can later add stages, percent progress, or cancellation without changing the workflow model.

## 5. Observable execution over fire-and-forget

A visual programming system needs to explain what the robot is doing. Execution state, progress, duration, errors, results, and cancellation are first-class runtime concepts.

## 6. Portability where semantics permit

Shared capability IDs are useful only when the semantics are genuinely compatible. Coordinate frames, units, constraints, preconditions, and result definitions matter as much as names.

RoboArc should make incompatibility visible rather than hiding it behind an overly broad abstraction.

## 7. Small core over framework complexity

v0.1 should prove one complete path:

```text
Blockly -> Workflow IR -> Runtime -> MockAdapter -> live execution feedback
```

New primitives, plugin systems, durable schedulers, cloud services, and AI features should be added only after a concrete use case demonstrates the need.

## 8. Declarative workflows over arbitrary code

The core workflow format should remain declarative and statically inspectable. Arbitrary Python or shell execution would undermine validation, portability, resource analysis, and security.

Advanced escape hatches can be considered later as explicitly privileged capabilities rather than as the default programming model.

## 9. Explicit semantics over clever inference

When progress is estimated, mark it as estimated. When cancellation is unsupported, expose that fact. When a capability is robot-specific, name or namespace it accordingly.

The runtime should prefer an honest partial contract over a misleading universal abstraction.

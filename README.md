# RoboArc

**Robot Action Representation & Composition**

Visual programming for robot behaviors.

RoboArc is an early-stage, robot-agnostic framework for composing robot capabilities visually and executing them through a small, observable runtime. The editor is only one view of a program: the canonical representation is a typed workflow IR that can target different robots through capability adapters.

<p align="center">
  <img src="docs/assets/architecture.svg" alt="RoboArc architecture" width="900" />
</p>

## Principles

- **Capabilities over robot APIs** — expose stable robot behaviors instead of leaking ROS, SDK, or transport details into workflows.
- **Workflow IR over editor state** — Blockly is an authoring surface; a typed, editor-neutral IR is the program.
- **Adapters over platform coupling** — capabilities may be backed by ROS 2, vendor SDKs, REST, gRPC, or other interfaces.
- **Observable execution** — progress, results, cancellation, errors, and logs are part of the runtime contract.
- **Portability where semantics permit** — compose against shared capabilities and run on compatible robot profiles.
- **Small core** — keep RoboArc useful without becoming a robotics platform monolith.

## Direction

The initial vertical slice is intentionally small:

**Blockly → Workflow IR → Python runtime → Mock robot**

It will validate authoring, capability discovery, execution, cancellation, and live runtime feedback before adding a real robot simulation. TIAGo is the leading reference simulation candidate; Reachy 2 is a strong follow-up showcase for cross-robot portability.

## Documentation

- [Architecture](docs/architecture.md)
- [Design principles](docs/design-principles.md)
- [Capability model](docs/capability-model.md)
- [Workflow IR](docs/workflow-ir.md)
- [Runtime](docs/runtime.md)
- [Demo strategy](docs/demo-strategy.md)
- [Development plan](docs/development-plan.md)
- [Architecture review](docs/research/deep-review.md)
- [Ecosystem landscape](docs/research/ecosystem-landscape.md)

## Status

RoboArc is currently in the **design / prototype** stage. APIs and schemas are not stable yet.

## License

MIT

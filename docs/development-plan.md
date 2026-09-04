# Development Plan

This file is the roadmap entry point. Each active milestone owns its detailed
scope, decisions, phases, and verification in one flat `docs/plans/*.md` file;
completed implementation truth belongs in `STATUS.md` and the linked docs.

## Roadmap

| Milestone | Outcome | State | Detailed plan |
| --- | --- | --- | --- |
| v0.0 | Versioned contracts and generated schemas | Implemented | Historical summary below |
| v0.1a | Observable runtime and deterministic MockAdapter | Implemented | Historical summary below |
| v0.1b | React/Blockly authoring and runtime workbench | Implemented | Historical summary below |
| v0.1c | First real ROS 2 Action lifecycle proof | Implemented | [v0.1c plan](plans/v0.1c-ros2-action.md) |
| v0.2 | TIAGo simulation with a narrow useful capability set | Planned | Create after v0.1c evidence |
| v0.3 | Portability proof through a second native interface | Planned | Create after v0.2 evidence |
| v0.4 | Programming-model hardening driven by real workflows | Deferred | Create only when concrete demand exists |
| v1.0 | Stable contracts and compatibility policy | Deferred | Requires evidence from prior milestones |

## Implemented Foundation

RoboArc currently has:

- strict, versioned Workflow IR, project, capability, profile, result, and event contracts;
- generated JSON Schemas and cross-language validation;
- `sequence`, `wait`, and `capability` nodes;
- an observable `asyncio` runtime with deadlines and truthful cancellation;
- a deterministic MockAdapter, CLI, and FastAPI HTTP/WebSocket service;
- a React/TypeScript/Blockly workbench with project round trips and runtime observation;
- Python and Web static checks, unit tests, schema drift gates, and Chromium workflows in CI.

See [STATUS.md](../STATUS.md) for current proof and
[implementation status](implementation-status.md) for the implemented surface.

## Future Milestone Intent

- **v0.2:** start with `navigation.goto_location`, `navigation.stop`,
  `head.look_at`, and `speech.say`; prefer named map locations; defer manipulation.
- **v0.3:** add profile selection and compatibility reporting, then run at least
  three semantically shared capabilities through a non-ROS-facing adapter such
  as the Reachy SDK/MuJoCo path.
- **v0.4:** consider typed references, conditions, bounded repeat, parallelism,
  retry/fallback, subflows, resource arbitration, and replay only when concrete
  workflows justify their semantics.
- **v1.0:** publish compatibility and migration policy for every external contract.

## Standing Boundaries

- Workflow IR stays declarative and editor-neutral.
- ROS/vendor imports stay outside `roboarc.contracts` and `roboarc.runtime`.
- Capability IDs become shared standards only after compatible real adapters prove them.
- Cancellation request acceptance never implies terminal cancellation.
- Authentication, persistence, collaboration, scheduling, arbitrary code
  execution, fleet orchestration, and a Rust rewrite are not v0.x core goals.
- Simulator and hardware tests remain separate from always-on core CI.

## Quality Floor

Every milestone retains contract/schema tests, runtime state-machine tests,
cancellation and timeout coverage, adapter conformance, deterministic mock
scenarios, relevant static checks, and the nearest integration proof for the
behavior it introduces.

# Architecture Overview

RoboArc separates workflow authoring, canonical behavior semantics, execution,
and robot-native integration.

```text
React workbench -> Blockly editor -> Workflow IR -> Runtime -> Capability adapter -> Robot
       |               |                  |             |
 project/runtime UI   editor state       JSON Schemas  ordered events
```

The React application is the workbench shell. It owns project controls,
manifest-driven argument editing, validation, run/stop actions, runtime state,
logs, progress, and results. Blockly is the embedded visual editor for the
supported `sequence`, `wait`, and `capability` nodes. Its workspace/XML is
editor state and is never executed directly; the compiler produces the
validated Workflow IR, which remains the only executable source of truth.

The implemented core is under `src/roboarc`:

- `contracts/` owns strict, versioned external data contracts.
- `runtime/` validates and executes Workflow IR without ROS/vendor imports.
- `api/` exposes discovery, validation, run control, replay, and live events.
- `cli.py` provides local validation, execution, and server commands.
- `web/src/` contains the React shell, Blockly blocks, compiler, API client,
  runtime event reducer, and tokenized workbench styling.

Adapters translate capability invocations and lifecycle semantics into native
operations. A cancellation request never proves that the native operation has
stopped; terminal results must report that distinction truthfully.

See [docs/architecture.md](docs/architecture.md) for subsystem boundaries,
security and portability constraints, and planned extension points. Runtime and
IR semantics live in [docs/runtime.md](docs/runtime.md) and
[docs/workflow-ir.md](docs/workflow-ir.md).

# Development Plan

The plan is organized around vertical slices. Each milestone should leave RoboArc usable and understandable rather than creating a large set of partially connected subsystems.

## v0.1 — End-to-end vertical slice

**Goal:** compose a small workflow in Blockly, compile it to Workflow IR, execute it against a MockAdapter, and see live execution state in the browser.

### Web

- React + TypeScript + Vite.
- Blockly 12 as the first editor.
- Capability-driven toolbox/palette.
- Minimal inspector for capability arguments.
- Save/load project JSON.
- Run and Stop controls.
- Current block highlighting and runtime event panel.

### Workflow IR

Implement only:

- `sequence`;
- `if`;
- `loop`;
- `wait`;
- `parallel`;
- `capability`.

Requirements:

- explicit `schema_version`;
- stable node IDs;
- deterministic validation;
- editor state separated from canonical IR.

### Runtime

- Python + FastAPI + Pydantic + asyncio.
- HTTP endpoints for discovery/validation/run control.
- WebSocket execution events.
- in-memory run state;
- capability result normalization;
- cooperative cancellation;
- capability default timeout handling;
- structured logs/events.

### Adapter

Implement `MockAdapter` with roughly 8–12 representative capabilities and configurable stage/progress behavior.

### Exit criteria

A fresh clone can run a demo without ROS or robot hardware:

```text
Blockly -> IR -> validate -> Run -> MockAdapter -> live block highlighting -> result
```

## v0.2 — Real robot simulation

**Goal:** prove that the adapter boundary works with a nontrivial ROS robot stack.

Leading target: TIAGo simulation.

Start with a narrow capability set:

- `navigation.goto`;
- `navigation.stop`;
- `head.look_at` or equivalent head motion;
- `speech.say` (runtime/browser TTS is acceptable initially).

Then add manipulation only after navigation/interaction is reliable:

- gripper open/close;
- arm pose;
- pick/place if the upstream simulation supports a robust demo path.

### Exit criteria

At least one useful visual workflow runs end-to-end in simulation with live runtime feedback and cancellation.

## v0.3 — Portability proof

**Goal:** execute a semantically shared workflow on a second robot profile.

Leading target: Reachy 2 + MuJoCo/SDK.

Add:

- robot profile selection;
- capability compatibility reporting;
- second adapter using a different native interface style;
- clearer distinction between standard and robot-specific capabilities.

### Exit criteria

One workflow containing only shared capabilities can run on both reference profiles without changing the Workflow IR.

## v0.4 — Programming model hardening

Only after real workflows expose the need, consider:

- explicit `timeout` node/policy;
- `retry` with retry-safety semantics;
- `fallback`;
- reusable subflows;
- stronger typed values;
- resource arbitration;
- preconditions/postconditions;
- execution timeline and replay metadata;
- schema migration tooling.

## v1.0 — Stable core contracts

A 1.0 release should mean the following are intentionally stable:

- Workflow IR compatibility policy;
- Capability manifest contract;
- adapter/handler interface;
- runtime event protocol;
- project file format.

Potential later features, not 1.0 requirements:

- Flow/graph authoring view;
- AI/LLM -> Workflow IR generation;
- durable/restartable workflows;
- collaboration/cloud accounts;
- plugin marketplace;
- fleet orchestration;
- hardened Rust edge runtime.

## v0.1 non-goals

Do not add these merely because they are common in larger workflow products:

- authentication or user accounts;
- database/Redis infrastructure;
- cloud synchronization;
- mobile app;
- cron/scheduler;
- arbitrary Python/JavaScript execution;
- Git integration;
- multi-robot fleet management;
- pause/resume;
- automatic retries;
- plugin marketplace;
- full Behavior Tree compatibility;
- LLM integration.

## Engineering quality from day one

Even while the feature set stays small, v0.1 should establish:

- schema/IR unit tests;
- runtime state-machine tests;
- cancellation tests;
- adapter conformance tests;
- deterministic MockAdapter scenarios;
- Web compile/validation tests;
- formatting/linting/type checking;
- a small set of end-to-end browser/runtime tests.

The target is a small codebase, not a prototype that can only be understood by its original authors.

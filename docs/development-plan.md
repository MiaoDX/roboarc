# Development Plan

The plan is organized around executable vertical slices. Each milestone must leave RoboArc usable, testable, and understandable; it should not create several partially connected subsystems.

## v0.0 — Contract skeleton — implemented

**Goal:** freeze the smallest external contracts before editor or robot integration work.

Delivered:

- versioned Workflow IR and project documents;
- capability manifests and exact capability references;
- robot profiles;
- execution result and runtime event contracts;
- generated JSON Schemas;
- deterministic contract tests.

The first IR deliberately contains only:

```text
sequence
wait
capability
```

`if`, variables, general loops, and parallelism remain deferred until their data, scope, cancellation, and result-propagation semantics are defined.

## v0.1a — Observable mock runtime — implemented

**Goal:** execute validated Workflow IR against a deterministic MockAdapter and expose truthful runtime state.

Delivered:

- Python, Pydantic, and `asyncio` runtime;
- capability/profile preflight validation;
- fail-fast sequence execution;
- ordered event history and subscriptions;
- per-capability default timeout handling;
- explicit cancellation request and cleanup phases;
- adapter result/output normalization and validation;
- six deterministic mock capability scenarios;
- CLI validation and execution;
- FastAPI HTTP/WebSocket service;
- in-memory run state and event replay;
- unit and integration tests across supported Python versions.

Exit path:

```text
Workflow JSON
-> validate
-> Runtime
-> MockAdapter
-> ordered events
-> terminal result
```

## v0.1b — Blockly authoring and runtime UI — next local milestone

**Goal:** create and execute the supported Workflow IR from a browser without making editor state canonical.

### Web

- React + TypeScript + Vite;
- Blockly 12;
- capability-driven toolbox from runtime discovery;
- `sequence`, `wait`, and capability blocks;
- manifest-driven argument inspector;
- separate Blockly editor state and canonical Workflow IR in saved projects;
- deterministic compiler from workspace to Workflow IR;
- local schema validation before API submission;
- Run and Stop controls;
- current block highlighting using stable node IDs;
- progress, logs, errors, duration, and terminal result panel;
- WebSocket reconnect and replay using `after_seq`.

### Exit criteria

A fresh clone can create, save, reload, validate, and execute a mock workflow from the browser. Success, failure, progress, timeout, supported cancellation, and incomplete cancellation are visible and covered by browser/runtime tests.

## v0.1c — First real-interface spike

**Goal:** validate the adapter lifecycle against a genuine asynchronous robot interface before depending on a full simulator.

Implement a narrow ROS 2 Action test server and adapter package outside the runtime core. Exercise:

- action goal dispatch;
- native feedback to RoboArc progress;
- success/failure result mapping;
- cancel acceptance and completion;
- unavailable action server;
- timeout with incomplete cleanup;
- adapter conformance tests.

### Exit criteria

The same Workflow IR/runtime code used by MockAdapter drives the ROS 2 Action test adapter, and the core packages contain no ROS-specific imports.

## v0.2 — TIAGo simulation

**Goal:** prove the adapter boundary with a nontrivial ROS robot stack.

Start with a narrow capability set:

```text
navigation.goto_location
navigation.stop
head.look_at
speech.say
```

Prefer named map locations before attempting a portable cross-robot pose contract. Add manipulation only after navigation, interaction, feedback, and cancellation are reliable.

### Exit criteria

At least one useful visual workflow runs end-to-end in TIAGo simulation with live runtime feedback and truthful cancellation behavior. Simulator setup is containerized and does not become a dependency of the core test suite.

## v0.3 — Portability proof

**Goal:** execute a semantically shared workflow through a second native interface style.

Leading showcase candidate: Reachy 2 through its SDK/MuJoCo path.

Add:

- robot profile selection;
- capability compatibility reporting;
- a second adapter that is not ROS-facing at the capability-handler boundary;
- explicit distinction between shared and robot-specific capabilities;
- reusable adapter conformance scenarios.

### Exit criteria

At least three meaningful shared capabilities run with unchanged Workflow IR on both reference profiles. Portability claims must document frames, units, preconditions, cancellation, and result semantics.

## v0.4 — Programming-model hardening

Only after concrete workflows expose the need, consider:

- typed outputs and references;
- limited declarative conditions;
- bounded repeat;
- `parallel_all` with fully specified join and sibling-cancellation semantics;
- explicit timeout policies;
- retry with retry-safety metadata;
- fallback;
- reusable subflows;
- resource arbitration;
- preconditions and postconditions;
- execution timeline and replay metadata;
- deterministic schema migration tooling.

Each new primitive requires written semantics and state-machine tests before editor work begins.

## v1.0 — Stable core contracts

A 1.0 release means the following are intentionally stable and have a published compatibility policy:

- Workflow IR;
- project file format;
- capability manifest and profile contracts;
- adapter/invocation lifecycle;
- runtime result and event protocols;
- migration and deprecation rules.

## Non-goals for v0.x core

Do not add these merely because they are common in general workflow products:

- authentication or user accounts;
- database/Redis infrastructure;
- cloud synchronization or collaboration;
- scheduler/cron;
- arbitrary Python, JavaScript, or shell execution;
- plugin marketplace;
- fleet orchestration;
- pause/resume;
- automatic retries;
- full Behavior Tree compatibility;
- LLM authoring;
- durable restart/reconciliation;
- Rust runtime rewrite.

## Engineering quality gates

Every milestone must retain:

- contract/schema tests;
- runtime state-machine tests;
- cancellation and timeout tests;
- adapter conformance tests;
- deterministic mock scenarios;
- cross-language compile/validation tests once the Web package exists;
- formatting, linting, and type checking in the relevant language toolchains;
- a small set of end-to-end browser/runtime tests;
- simulator and hardware tests separated from always-on core CI.

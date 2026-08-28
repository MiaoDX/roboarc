# Architecture

RoboArc is a small visual-programming framework for composing robot behaviors from reusable capabilities. Its primary architectural goal is to separate **how a workflow is authored** from **what the workflow means** and **how a robot executes it**.

![RoboArc architecture](assets/architecture.svg)

## Goals

- Provide a friendly Web authoring experience, starting with Blockly.
- Keep a typed, editor-neutral Workflow IR as the canonical program representation.
- Expose robot functionality through stable capabilities rather than transport-specific APIs.
- Support heterogeneous robot interfaces: ROS 2, SDKs, REST, gRPC, WebSocket, and others.
- Make execution observable: state, progress, result, errors, logs, and cancellation.
- Allow the same workflow to run on different robots when their capability semantics are compatible.
- Keep the core small enough to understand, test, and embed.

## Non-goals

RoboArc v0.x is not intended to be:

- a replacement for ROS 2, Nav2, MoveIt 2, or vendor SDKs;
- a hard real-time or safety-certified controller;
- a general-purpose Python/JavaScript execution sandbox;
- a fleet-management, cloud-account, collaboration, or marketplace platform;
- a promise that every capability is portable across every robot.

## System boundaries

```text
Authoring
  Blockly       Flow UI (later)       AI/LLM (later)
      \              |                   /
       +-------------+------------------+
                     |
                     v
                Workflow IR
                     |
              validate / execute
                     |
                     v
               RoboArc Runtime
                     |
              Capability Contract
                     |
          +----------+----------+
          |          |          |
        ROS 2       SDK        REST / gRPC / ...
          |          |          |
          +----------+----------+
                     |
                   Robot
```

### Authoring layer

Blockly is the first authoring surface. Its workspace serialization is UI state, not the executable source of truth. A future node-graph editor or AI authoring path should compile to the same IR.

### Workflow IR

The Workflow IR captures behavior semantics without depending on Blockly, ROS, or a specific robot. v0.1 deliberately starts with a small set of primitives: sequence, condition, loop, wait, parallel, and capability invocation.

### Capability layer

A capability is a product-level robot behavior such as `navigation.goto`, `head.look_at`, or `speech.say`. A manifest describes its inputs, outputs, execution traits, and resource requirements. A robot adapter binds that contract to the robot's native interface.

### Runtime

The runtime validates and executes the IR, dispatches capability calls, propagates cancellation, and emits structured execution events. The first implementation is expected to use Python, `asyncio`, Pydantic, FastAPI, and WebSocket communication.

The runtime core should not import ROS-specific types. ROS integration belongs in an adapter package.

### Robot adapters

An adapter translates a RoboArc capability into a native robot operation. A single robot profile may mix transports; for example, navigation may use a ROS 2 Action while speech uses REST and manipulation uses a vendor SDK.

Adapters are also responsible for translating native feedback and errors into RoboArc execution semantics.

## Communication

For v0.1, keep the Web/runtime protocol simple:

- HTTP for capability discovery, workflow validation, and run control;
- WebSocket for execution events and live status.

This is intentionally simpler than introducing gRPC into the browser-facing boundary. Adapters remain free to use gRPC internally.

## Security boundary

RoboArc workflows are declarative. v0.1 should not execute arbitrary user-provided Python, shell commands, or JavaScript. Capability handlers are trusted code installed with the runtime; workflows can only invoke capabilities exposed by the active robot profile.

Authentication, multi-user authorization, and hostile multi-tenant workflow execution are explicitly deferred, but the architecture should not make them impossible later.

## Portability boundary

Capability names alone do not guarantee semantic equivalence. Portability depends on compatible contracts for coordinate frames, units, preconditions, payload/workspace constraints, timing, cancellation, and result semantics.

RoboArc therefore aims for:

> Compose against shared capabilities; run where compatible.

rather than "write once, run everywhere."

## Future extensions

The architecture leaves room for, but does not require in v0.1:

- React Flow or another graph-oriented editor;
- subflows and reusable workflow packages;
- retry, timeout, fallback, guards, and event primitives;
- resource arbitration and capability pre/postconditions;
- durable execution and restart recovery;
- execution replay and provenance;
- natural-language / LLM generation of Workflow IR followed by visual review;
- a hardened Rust edge runtime if deployment requirements justify it.

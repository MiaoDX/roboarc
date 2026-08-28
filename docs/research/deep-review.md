# Architecture Review

**Date:** 2026-08-28  
**Scope:** product, architecture, runtime semantics, robotics integration, simulation, security, open-source strategy, and future AI authoring.

This memo consolidates the design review and targeted research that led to the current RoboArc direction. It separates evidence-backed observations from engineering recommendations where useful.

## Executive verdict

The core direction is sound:

> **Web visual authoring + editor-neutral typed Workflow IR + capability contracts + robot adapters + observable runtime**

is a better long-term boundary than directly generating and executing Python from Blockly.

The strongest decisions to preserve are:

1. Blockly is an editor, not the program representation.
2. Robot capabilities are product-level contracts, not raw ROS topics/services.
3. ROS 2 and vendor transports live behind adapters.
4. Runtime feedback/cancellation are first-class concepts.
5. A MockAdapter is required so the core project remains small and approachable.

The largest risk is not technology selection. It is **over-generalizing robot capabilities before enough real robot integrations exist**. RoboArc should validate abstractions against concrete TIAGo/Reachy workflows and allow robot-specific capabilities rather than forcing universal semantics.

## Key risks, ordered by severity

### 1. False portability across robots — high

A shared name such as `navigation.goto` can hide important differences in frames, maps, units, localization assumptions, obstacle behavior, velocity constraints, cancellation, and result semantics. Manipulation is even less portable because workspace, payload, end-effector, perception, and grasp semantics differ substantially.

**Recommendation:** standardize only capabilities demonstrated across real adapters. Make compatibility explicit and allow vendor-specific namespaces.

### 2. Runtime semantics becoming underspecified — high

Visual programming looks simple until parallelism, cancellation, timeout, retries, and physical side effects interact. A workflow engine cannot assume that timing out or canceling a coroutine means the robot stopped.

**Recommendation:** make result and cancellation semantics precise in v0.1; defer retry, pause/resume, and durable recovery until their contracts can be defined against real hardware/simulation.

### 3. Overbuilding the DSL before product validation — high

Behavior-tree systems demonstrate the value of fallback, retry, reactive conditions, decorators, and subtrees, but importing all of these into v0.1 would work against the small-repo goal.

**Recommendation:** start with sequence/if/loop/wait/parallel/capability. Preserve extensibility without implementing every future primitive.

### 4. Editor/runtime coupling — medium/high

If Blockly block serialization or generated Python becomes the executable source of truth, schema migration, alternative editors, static validation, and AI authoring become difficult.

**Recommendation:** preserve the canonical IR boundary from the first saved project.

### 5. Security drift toward remote code execution — medium/high

A tempting shortcut is a "Python block" or shell capability. This quickly undermines validation and turns a browser-connected robot runtime into a remote execution surface.

**Recommendation:** v0.x workflows remain declarative; capability handlers are trusted installed code. Privileged escape hatches, if ever added, must be explicit and isolated.

### 6. Simulation complexity swallowing product work — medium

A full Nav2 + MoveIt + perception manipulation demo can consume more engineering effort than the visual programming product itself.

**Recommendation:** MockAdapter first; then a narrow TIAGo navigation/head/interaction slice; manipulation later. Use Reachy 2 as a second portability/showcase target.

### 7. Progress UI creating false precision — medium

Many robot APIs do not expose meaningful percent completion. Estimating progress can mislead users.

**Recommendation:** support `none`, `stage`, and `percent`, and label percent provenance as native or estimated.

## Product review

### Target user

Blockly is strongest for users who think in procedural composition: "go there, then look, then speak, repeat this." A node graph is often stronger for event-driven, data-flow, or highly branching workflows.

RoboArc should therefore avoid claiming that blocks are the final universal interaction model. The editor-neutral IR keeps a future Flow view possible without forcing two editors into v0.1.

### Product differentiation

The project should not position itself as "Blockly for ROS." That space already has educational and ROS-node-generation tools. The stronger positioning is:

> Visual composition of robot capabilities with a portable, observable execution model.

The runtime view is as important as the editor: current-node highlighting, progress/stage, result, duration, cancellation, and logs make physical robot behavior understandable.

## Architecture red-team

### Workflow IR

**Good:** editor-neutral representation enables validation, migration, multiple editors, and AI generation.

**Risk:** creating a general workflow language too early.

**Decision:** keep v0.1 primitives small and JSON-native; add `schema_version` and stable node IDs immediately.

### Capability manifests

**Good:** one declaration can drive palette, inspector, validation, docs, and discovery.

**Risk:** manifest complexity grows into a second robotics middleware.

**Decision:** start with ID/version/inputs/execution/progress/resources. Add frames, pre/postconditions, richer type systems, and permissions only when real adapters require them.

### Adapters

**Good:** heterogeneous ROS/SDK/REST/gRPC interfaces can map to a uniform upper-level contract.

**Risk:** transport abstraction is easier than semantic abstraction.

**Decision:** adapters translate both calls and semantics; robot profiles expose only genuinely supported capabilities.

### Python runtime

**Good:** excellent robotics/ML integration, low implementation cost, natural async model, strong Pydantic/FastAPI ecosystem.

**Risk:** a future edge daemon may need stronger isolation, resource control, or packaging.

**Decision:** Python is the right MVP tradeoff. Rust remains an optimization/hardening option, not a prerequisite.

### Web/runtime protocol

**Good:** HTTP + WebSocket is sufficient for discovery, run control, and streaming events.

**Risk:** reconnect semantics become complicated if runs later become durable.

**Decision:** v0.1 runs are in-memory and non-resumable. Durable execution is a separate future design problem.

## Runtime semantics review

### Concurrency

Parallel robot actions need resource awareness. Declared logical resources such as `base_motion` or `left_arm` are a useful first guardrail. A full priority/preemption scheduler is unnecessary for v0.1.

### Cancellation

Cancellation must be cooperative and truthful. If the native robot action cannot be stopped, RoboArc must not simply cancel the local coroutine and report success.

### Retry

Automatic retry is dangerous for non-idempotent physical actions. `pick`, `move_relative`, or `open_door` can change the world on the first attempt. Retry should eventually depend on capability semantics, not be a universal wrapper.

### Durability

Persisting a program counter is not enough to safely resume a physical workflow after a crash. Recovery requires reconciliation with robot/world state. Defer this rather than shipping misleading restart semantics.

## Security review

The initial deployment is expected to be local/developer-oriented, but several boundaries should be established early:

- no arbitrary workflow code execution;
- explicit capability allowlist through robot profiles;
- validate every workflow before execution;
- bound input sizes and numeric ranges;
- do not construct shell commands from workflow fields;
- keep Web/runtime communication local by default during early development;
- treat physical safety as the responsibility of robot controllers/safety systems, not the visual workflow layer.

Authentication, TLS, user roles, and multi-tenant isolation can be added when network deployment requirements become concrete.

## Community validation

Several active projects validate individual parts of the design:

- **Blockly** recommends its JSON serialization system for new projects, supporting the decision to treat editor state as structured data rather than legacy XML.
- **Scratch Blocks 2.0** now builds on Blockly 12 instead of maintaining an independent long-lived fork, making Scratch-style UX worth evaluating without abandoning Blockly's core.
- **Node-RED 5.0** substantially refreshed its editor UX in 2026; its palette/workspace/inspector/debug information architecture remains a useful product reference.
- **FlexBE WebUI** combines a graphical ROS 2 behavior editor with runtime supervision and operator intervention, validating the importance of execution UX.
- **BehaviorTree.CPP** remains a mature robotics behavior runtime with active 2026 releases; it is a strong semantic reference for future fallback/retry/reactivity without needing to be RoboArc's v0.1 runtime.
- **Open Roberta Lab** demonstrates long-lived browser-based graphical programming across many robot families, but its scale also illustrates why RoboArc should keep its first core much smaller.
- **ROS Blocky** demonstrates current interest in Blockly-based ROS 2 authoring, but focuses primarily on generating ROS nodes/packages rather than a robot-agnostic capability runtime.

See [Ecosystem Landscape](ecosystem-landscape.md) for details and links.

## Simulation review

### TIAGo

Strong first integration target because the public ROS 2 simulation documents Gazebo together with Nav2, SLAM, and MoveIt 2. This covers navigation plus manipulation without RoboArc owning the robot stack.

### Reachy 2

Strong second target because its Python SDK, ROS 2/gRPC server, MuJoCo support, and manipulation-oriented scenes exercise a different adapter style. Reachy tutorials explicitly support MuJoCo and real-robot usage through the SDK ecosystem.

### Strategy

Do not make either simulator a core dependency. Core CI runs against MockAdapter; simulator tests are separate integration layers.

## AI / LLM review

The current architecture is compatible with future AI authoring because the model can propose declarative Workflow IR rather than robot code:

```text
Prompt -> proposed IR -> schema/capability validation -> visual review -> execution
```

This is preferable to allowing an LLM to emit arbitrary Python against robot APIs. AI should not be part of v0.1; the important decision is preserving the typed IR boundary now.

## What must be right in v0.1

- canonical IR separate from Blockly state;
- stable node IDs and schema version;
- capability/adapter boundary;
- truthful result and cancellation semantics;
- structured runtime events;
- MockAdapter and deterministic tests;
- no arbitrary code execution.

## What should be simplified

- small IR node set;
- minimal manifest fields;
- in-memory runs;
- HTTP + WebSocket;
- one editor;
- one mock profile before robotics simulation.

## What should be delayed

- pause/resume;
- automatic retry/fallback;
- durable execution/restart;
- sophisticated resource scheduler;
- plugin marketplace;
- cloud accounts/collaboration;
- Flow editor;
- AI authoring;
- Rust runtime rewrite.

## Evidence vs. engineering judgment

**Strong external evidence:** upstream project capabilities and maintenance status; Blockly JSON serialization guidance; TIAGo simulation integration; Reachy 2 SDK/MuJoCo support; FlexBE runtime-supervision model; BehaviorTree.CPP maturity.

**Engineering judgment:** the exact RoboArc IR shape, v0.1 feature cuts, Python-vs-Rust sequencing, capability naming policy, and the recommendation to use TIAGo first and Reachy 2 second. These are design choices informed by the evidence, not industry standards.

## Primary sources

- Blockly serialization: https://developers.google.com/blockly/guides/configure/web/serialization
- Scratch Blocks: https://github.com/scratchfoundation/scratch-blocks
- Node-RED 5.0: https://nodered.org/blog/2026/06/09/version-5-0-released
- BehaviorTree.CPP: https://github.com/BehaviorTree/BehaviorTree.CPP
- FlexBE WebUI: https://github.com/FlexBE/flexbe_webui
- Open Roberta Lab: https://github.com/OpenRoberta/openroberta-lab
- ROS Blocky: https://github.com/ros-blocky/ros-blocky
- CyberDog VP: https://github.com/MiRoboticsLab/interaction/tree/rolling/cyberdog_vp
- TIAGo simulation: https://github.com/pal-robotics/tiago_simulation
- Reachy 2 SDK: https://github.com/pollen-robotics/reachy2-sdk
- Reachy 2 core: https://github.com/pollen-robotics/reachy2_core
- Reachy 2 MuJoCo assets: https://github.com/pollen-robotics/reachy2_mujoco_assets
- Reachy 2 tutorials: https://github.com/pollen-robotics/reachy2-tutorials

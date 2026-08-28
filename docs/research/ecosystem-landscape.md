# Ecosystem Landscape

RoboArc is intentionally not trying to replace every existing visual-programming or robot behavior tool. This document records the projects that most directly inform its design and what should — and should not — be borrowed from each.

Status notes reflect research performed in August 2026 and should be revisited periodically.

## Blockly

**Role:** block-based editor foundation.  
**Reference:** https://developers.google.com/blockly/

Blockly remains a strong foundation for a browser-first, extensible block editor. Its documentation recommends JSON serialization for new projects and treats XML as the legacy format.

**Borrow:**

- block authoring and toolbox ecosystem;
- JSON workspace serialization;
- custom fields/mutators/plugins where needed.

**Do not inherit:**

- the assumption that generated source code must be the canonical program.

RoboArc keeps Blockly state as editor state and compiles it to Workflow IR.

## Scratch Blocks 2.0

**Role:** friendlier block interaction/rendering reference.  
**Reference:** https://github.com/scratchfoundation/scratch-blocks

Scratch Blocks 2.0 depends on Blockly 12 rather than remaining an independent Blockly fork. This makes Scratch-style interaction worth prototyping while retaining the Blockly ecosystem.

**Borrow:** approachable visual language and interaction patterns.

**Decision:** evaluate as a UI layer/renderer; do not make it a v0.1 dependency until a small UX comparison is complete.

## React Flow

**Role:** future graph-oriented editor candidate.  
**Reference:** https://reactflow.dev/

React Flow provides a mature React foundation for node/edge editors, selection, pan/zoom, custom nodes, and accessible graph interaction.

**Borrow:** graph UX if RoboArc later needs a Flow view for branching, events, dataflow, or complex behaviors.

**Decision:** do not ship two editors in v0.1. Preserve an editor-neutral IR so a Flow view can be added later.

## Node-RED

**Role:** workflow product UX benchmark.  
**Reference:** https://nodered.org/

Node-RED 5.0, released in June 2026, delivered a major editor UX refresh. Its long-lived palette + canvas + inspector/debug model is particularly relevant.

**Borrow:**

- capability palette information architecture;
- canvas/inspector balance;
- debug/runtime feedback patterns;
- discoverability and documentation UX.

**Do not use as:** the core robot behavior runtime. RoboArc needs robot-specific cancellation, resource, and physical-action semantics.

## BehaviorTree.CPP

**Role:** production robotics behavior-semantics reference.  
**Reference:** https://github.com/BehaviorTree/BehaviorTree.CPP  
**Docs:** https://www.behaviortree.dev/

BehaviorTree.CPP is a mature robotics behavior-tree library with active releases, including 4.9.0 in 2026. Its semantics around asynchronous actions, fallback, decorators, halting, and subtree composition are highly relevant as RoboArc grows.

**Borrow:** semantic lessons for future fallback, retry, reactive conditions, cancellation, and hierarchical composition.

**Decision:** do not force v0.1 Workflow IR to be BehaviorTree XML. A compiler/backend could be explored later.

## Groot2

**Role:** behavior-tree authoring/debugging UX reference.  
**Reference:** https://github.com/BehaviorTree/Groot2

**Borrow:** runtime visualization, hierarchy inspection, graph validation, and debugging concepts.

**Caution:** some advanced functionality belongs to Groot2's product/licensing model; RoboArc should use it as a design reference rather than assume feature parity.

## FlexBE

**Role:** ROS 2 visual behavior + runtime supervision reference.  
**Reference:** https://github.com/FlexBE/flexbe_webui

FlexBE WebUI provides a graphical editor for hierarchical state machines and runtime supervision, including operator input/control. Its current WebUI uses Python/FastAPI with a browser interface.

**Borrow:**

- execution supervision as a first-class product surface;
- concurrent/nested behavior visualization;
- operator-aware runtime controls;
- diagnostics/security/testing documentation discipline.

**Difference:** RoboArc starts robot-agnostic and capability-driven rather than ROS/HFSM-first.

## Open Roberta Lab

**Role:** long-running multi-robot graphical-programming reference.  
**Reference:** https://github.com/OpenRoberta/openroberta-lab

Open Roberta demonstrates browser-based block programming across many robot families and a plugin-oriented robot ecosystem.

**Borrow:** lessons in robot capability presentation and multi-hardware support.

**Caution:** its mature repository is large and includes server/database/cross-compilation concerns. RoboArc intentionally starts much smaller.

## ROS Blocky

**Role:** contemporary Blockly + ROS 2 reference.  
**Reference:** https://github.com/ros-blocky/ros-blocky

ROS Blocky is an Electron/Blockly IDE that visually creates ROS 2 nodes and URDFs, generates Python packages, builds them, and runs ROS processes.

**Borrow:** examples of mapping ROS concepts into blocks and current Blockly-based robotics UX.

**Difference:** RoboArc is not primarily a ROS node generator. It composes higher-level robot capabilities and executes a typed workflow through adapters.

## CyberDog VP

**Role:** capability abstraction and robot-local visual-programming runtime reference.  
**Reference:** https://github.com/MiRoboticsLab/interaction/tree/rolling/cyberdog_vp

CyberDog VP's strongest idea is its AbilitySet: a product-facing capability API sits between visual programs and lower-level ROS robot modules. Its robot-side engine also models task lifecycle and robot-mode constraints.

**Borrow:**

- capability/AbilitySet abstraction;
- local robot execution;
- task lifecycle and robot-state awareness;
- reusable task/module thinking.

**Avoid:** treating generated Python/shell files as the primary safe execution model for untrusted workflows. RoboArc instead keeps a typed declarative IR and explicit adapter boundary.

## TIAGo

**Role:** first real simulation integration candidate.  
**Reference:** https://github.com/pal-robotics/tiago_simulation

The public ROS 2 simulation documents Gazebo with Nav2, SLAM, MoveIt 2, and combined navigation/manipulation launch paths.

**Why useful:** broad capability surface with an existing robot stack, allowing RoboArc to focus on visual programming rather than building navigation/manipulation infrastructure.

## Reachy 2

**Role:** second robot / portability showcase.  
**References:**

- https://github.com/pollen-robotics/reachy2-sdk
- https://github.com/pollen-robotics/reachy2_core
- https://github.com/pollen-robotics/reachy2_sdk_server
- https://github.com/pollen-robotics/reachy2_mujoco
- https://github.com/pollen-robotics/reachy2_mujoco_assets
- https://github.com/pollen-robotics/reachy2-tutorials

Reachy 2 provides a Python SDK, ROS 2/gRPC server architecture, Gazebo components, and a MuJoCo path. Its tutorials support both real and MuJoCo-backed use, and the MuJoCo assets include manipulation-oriented table, fruit, and kitchen scenes.

**Why useful:** exercises an SDK-oriented adapter and makes a compelling interaction/manipulation demo.

## What RoboArc is combining

The intended combination is deliberately narrower than any single mature platform:

```text
Blockly / Scratch-style UX        -> approachable authoring
Node-RED                           -> workflow product UX
CyberDog AbilitySet                -> capability abstraction
FlexBE / Groot2                    -> observable runtime UX
BehaviorTree.CPP                   -> future behavior semantics reference
TIAGo / Reachy 2                   -> concrete adapter validation
                 |
                 v
              RoboArc
```

The project's differentiation should come from the boundaries between these ideas, not from reimplementing all of their features.

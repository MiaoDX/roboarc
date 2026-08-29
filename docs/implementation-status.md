# Implementation Status and Local Handoff

## Completed in the current core slice

### Contracts

- Separate version fields for project format, Workflow IR, editor state, capability manifests, robot profiles, and runtime events.
- Exact `{id, version}` capability references in both workflows and profiles.
- Stable node IDs with duplicate, depth, and node-count validation.
- Strict JSON-compatible payload checks, including rejection of non-finite numbers.
- Generated Draft 2020-12 JSON Schemas checked into `schemas/`.

### Runtime

- Preflight capability and argument validation against the active profile.
- `sequence`, `wait`, and `capability` execution.
- Fail-fast sequence behavior.
- Per-capability default deadlines.
- Explicit `CANCELING` state and bounded cancellation cleanup.
- Truthful handling of unsupported or incomplete native cancellation.
- Adapter output validation against declared manifest outputs.
- Ordered, replayable runtime events using `event_protocol_version`, `event_id`, and monotonic `seq`.

### MockAdapter

The mock profile exercises six distinct execution traits:

```text
demo.instant_success
demo.staged_action
demo.percent_action
demo.fail
demo.cancellable_action
demo.uncancellable_action
```

These names are intentionally demo-specific. They test the framework without prematurely declaring robot capability standards.

### Transport

The FastAPI service supports capability discovery, validation, start/cancel control, run snapshots, HTTP event replay, and live WebSocket events. Runs and event histories are in-memory and process-local by design.

### Quality gates

The test suite covers contract strictness, generated schema drift, registry conformance, argument validation, ordered events, fail-fast behavior, cancellation acknowledgement, cancellation incompleteness, timeout cleanup, adapter output violations, CLI execution, and HTTP/WebSocket behavior.

GitHub Actions runs the suite on Python 3.11, 3.12, and 3.13.

## Deliberately not implemented

- `if`, general expressions, variables, and output references;
- `loop`, retry, fallback, timeout nodes, subflows, or events;
- parallel execution and resource arbitration;
- pause/resume;
- persistent or restartable runs;
- authentication, multi-user authorization, databases, or cloud services;
- arbitrary code execution;
- Blockly/React Web authoring;
- ROS 2, TIAGo, Reachy 2, simulator, or hardware adapters.

## Recommended local continuation

The next slice is better performed in a local Codex/devcontainer environment because it needs Node package installation, interactive browser testing, and then ROS/simulator dependencies.

### 1. Web authoring slice

Create a React + TypeScript + Vite application with Blockly 12. Use `/api/v1/capabilities` to generate the palette and inspector; compile Blockly state to the checked-in Workflow IR contract rather than generated Python.

Minimum UI scope:

- capability-driven toolbox;
- `sequence`, `wait`, and capability blocks only;
- project save/load preserving editor state separately from canonical IR;
- validate, Run, and Stop controls;
- block highlighting by stable `node_id`;
- event/log panel with reconnect using `after_seq`.

### 2. Cross-language contract tests

Validate the same golden Workflow IR fixtures in Python and TypeScript. The browser must reject unsupported schema versions and must never treat Blockly workspace serialization as executable source of truth.

### 3. Thin ROS 2 Action spike

Before installing the full TIAGo stack, implement a small ROS 2 Action test server and adapter. It should prove:

- goal dispatch and native feedback translation;
- exact terminal result mapping;
- cancel request versus cancel completion;
- timeout cleanup;
- no ROS imports in `roboarc.contracts` or `roboarc.runtime`.

### 4. TIAGo integration

Only after the thin Action spike passes should the adapter target TIAGo navigation/head behavior. Keep simulator tests outside the always-on core CI suite.

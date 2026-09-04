# Implementation Status

## Completed through v0.3

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

### Web workbench

- React/TypeScript/Vite application shell with an embedded Blockly 12 editor.
- Capability toolbox and manifest-driven argument inspector from runtime discovery.
- Supported `sequence` and `wait` blocks, semantic Reachy/TIAGo action blocks,
  and generic capability fallback with stable node IDs.
- TIAGo `Go to`, spatial `Look` (`ahead`, `left`, or `right`), `Say`, and `Stop
  navigation` blocks compile to the existing exact v1 capability contracts;
  non-representable canonical payloads remain generic and lossless.
- Deterministic compilation to Workflow IR and local schema validation.
- Atomic project save/load with Blockly editor state kept separate from canonical IR.
- Backend validation, run/stop controls, block highlighting, progress, logs,
  errors, duration, and terminal results.
- Reconnecting WebSocket consumption with `after_seq` replay and duplicate-event filtering.

### Quality gates

The test suite covers contract strictness, generated schema drift, registry conformance, argument validation, ordered events, fail-fast behavior, cancellation acknowledgement, cancellation incompleteness, timeout cleanup, adapter output violations, CLI execution, and HTTP/WebSocket behavior.

GitHub Actions runs the Python suite on 3.11, 3.12, and 3.13. The Web job runs
Prettier, ESLint, TypeScript, 40 unit tests, schema drift checks, a production
build, nine Chromium workflows, and the dependency audit.

### ROS 2 Action lifecycle proof

A repository-local ROS 2 Jazzy harness uses `example_interfaces/action/Fibonacci`
to prove real Action dispatch, native progress, validated output, abort,
rejection, unavailable-server and transport failures, accepted cancellation,
terminal cancellation, bounded timeout cleanup, and incomplete cancellation.
The harness and its dedicated CI workflow are optional; core package metadata
and always-on Python/Web checks remain ROS-free.

### Observable simulation and TIAGo proof

The telemetry vocabulary covers pose, trajectory, action state, capability
progress, timestamps, and run/node/invocation identity. The deterministic
simulation adapter exports correlated JSONL and optional native Rerun
recordings without ROS or simulator dependencies.

The separate TIAGo manual lane builds a pinned ROS 2 Jazzy/Gazebo Harmonic
overlay and maps `navigation.goto_location`, `navigation.stop`, `head.look_at`,
and `speech.say` onto Nav2, controllers, and a speech transport seam. Its
four-node workflow completed successfully with correlated TF-derived pose and
trajectory telemetry; the native Rerun recording passed verification.

### Reachy 2 portability proof

The minimal Reachy 2 lane self-builds Pollen Robotics' open-source MuJoCo fake
SDK and keeps vendor details outside the core contracts/runtime packages. The
completed review artifact uses the `reachy2-sim` profile and a succeeded
`reachy-observable` workflow with 968 trace observations and an 852x480 H.264
MuJoCo recording cropped to the actual rendered viewport. Its image digest,
base image, upstream commits, and MuJoCo version are recorded in the manifest.
Validate the complete artifact set with:

```bash
python scripts/validate_review_artifacts.py artifacts/reachy-proof-final
```

`--check-media` additionally requires host `ffprobe`; `--check-rerun` requires
the `rerun` CLI. The corresponding TIAGo proof artifact validates through the
same command and remains a recorded manual ROS/Gazebo proof, not a production
hardware adapter.

## Deliberately not implemented

- `if`, general expressions, variables, and output references;
- `loop`, retry, fallback, timeout nodes, subflows, or events;
- parallel execution and resource arbitration;
- pause/resume;
- persistent or restartable runs;
- authentication, multi-user authorization, databases, or cloud services;
- arbitrary code execution;
- physical production hardware adapters. Deterministic simulation, the Reachy
  2 SDK/MuJoCo portability lane, and a proven TIAGo ROS/Gazebo manual adapter
  exist; these remain simulator/manual integrations rather than supported
  production hardware adapters.

## Future work

### Community task composition

The completed TIAGo-first
[Community Task Composition plan](plans/community-task-composition.md). It uses
the existing `sequence`, `wait`, and `capability` nodes to prove that a
developer can create, run, save, import, and review a task that is not a canned
fixture. Simulator proofs remain outside always-on core CI.

Additional control-flow nodes, persistence, authentication, perception,
manipulation, and hardware support require separate workflow-driven proposals;
they are not implied by this slice.

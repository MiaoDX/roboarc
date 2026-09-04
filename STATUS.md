# Status

## Current

RoboArc has completed v0.2a: the observable simulation loop and the separate
TIAGo ROS 2 Jazzy/Gazebo Harmonic proof. The Python package, typed contracts,
generated schemas, asyncio runtime, deterministic adapters, CLI, FastAPI
HTTP/WebSocket transport, and React/Blockly workbench are implemented. Blockly
remains editor state; compiled Workflow IR remains the executable source of
truth.

The workbench supports capability discovery, sequence/wait/capability blocks,
manifest-driven arguments, project download/upload, local and backend
validation, run/stop controls, stable block highlighting, progress, logs,
errors, duration, terminal results, and WebSocket reconnect/replay.

The TIAGo review route loads a same-run manifest, renders its canonical
Workflow IR as read-only Blockly, and presents the correlated runtime metadata,
JSONL, Rerun, and Gazebo video artifacts. Its reusable Execution Timeline maps
video time to node.started/node.finished events from the same trace, so playback
and seeking highlight the active leaf Blockly node. The desktop review layout
prioritizes the sticky Gazebo recording beside a smaller Workflow panel, so the
robot behavior and synchronized node remain visible together. This is
recorded-playback synchronization; live Gazebo control remains out of scope.
Its capture starts only after Nav2 and the TIAGo controllers report ready,
avoiding simulator startup footage.
The manifest renderer recursively supports sequence, wait, and capability nodes
and verifies run/workflow identity before presenting a result.

The deterministic simulation produces correlated Runtime events, pose,
trajectory, action state, and capability progress as JSONL and native Rerun
recordings. The pinned TIAGo lane runs the same observation vocabulary through
Nav2, controllers, TF, and Gazebo while keeping ROS and simulator dependencies
outside the core package.

## Verification

The required local checks pass:

```text
44 core Python tests passed with 2 optional ROS/TIAGo tests skipped; 29 Web unit
tests and 8 Chromium browser workflows passed. The deterministic proof produced
47 correlated records. The latest live GPU TIAGo review run
(`run-28dfba79cff240b0a8e729fa855a41e6`) succeeded across all four capability
nodes, produced 1,419 observations, and emitted a 10.628-second H.264 1600x900
Gazebo recording plus a native Rerun recording. Browser review confirmed the
same-run manifest, cache-isolated MP4/trace URLs, active-leaf Blockly
highlighting, run metadata, artifact links, and video render. The native Rerun
proof passed `rerun rrd verify`.
The ROS-enabled image also served the explicit TIAGo API with the `tiago-sim`
profile and four exact-version capabilities, then shut down cleanly.
ruff check .
mypy src/roboarc
python -m compileall -q src scripts
schema regeneration has no diff
```

CI runs Python checks on 3.11, 3.12, and 3.13, plus Web format, lint,
typecheck, unit tests, schema drift, production build, Chromium workflows, and
high-severity dependency audit.

## Next

v0.3 is the next roadmap milestone: select profiles, report capability
compatibility, and prove shared semantics through a second native interface.
An executable draft exists at
[`docs/plans/v0.3-portability.md`](docs/plans/v0.3-portability.md) and is
approved for implementation. Reachy 2 is the sole second robot: the required
manual/scheduled product proof uses the official SDK-facing MuJoCo simulation
and produces synchronized video/Blockly evidence; Gazebo/RViz are diagnostic
only and physical hardware remains out of scope. Each service starts with one
selected robot profile, and the Workbench exposes only that profile's registered
capabilities; TIAGo and Reachy 2 are not required to share a demo workflow.
The embedded viewer remains optional and should be reconsidered only if the
standalone observation workflow demonstrates a concrete product need.

## Deferred

General expressions, variables, loops, parallelism, persistence, auth,
databases, embedded visualization, and production hardware adapters remain outside
the current core slice. See [docs/development-plan.md](docs/development-plan.md)
for the staged roadmap.

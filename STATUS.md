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

The deterministic simulation produces correlated Runtime events, pose,
trajectory, action state, and capability progress as JSONL and native Rerun
recordings. The pinned TIAGo lane runs the same observation vocabulary through
Nav2, controllers, TF, and Gazebo while keeping ROS and simulator dependencies
outside the core package.

## Verification

The required local checks pass:

```text
49 isolated core Python tests passed with 3 optional ROS/TIAGo/Rerun tests
skipped; 9 TIAGo tests passed in the Jazzy container; 24 Web unit tests and 7
Chromium browser workflows passed. The deterministic proof produced 47 correlated
records. The live TIAGo workflow succeeded across all four capability nodes,
produced 1,259 records, moved the robot approximately 0.759 m, and emitted a
native Rerun recording verified with pose and trajectory spatial entities.
ruff check .
mypy src/roboarc
python -m compileall -q src scripts
schema regeneration has no diff
```

CI runs Python checks on 3.11, 3.12, and 3.13, plus Web format, lint,
typecheck, unit tests, schema drift, production build, Chromium workflows, and
high-severity dependency audit.

## Next

v0.3 is the next planned milestone: select profiles, report capability
compatibility, and prove shared semantics through a second native interface.
The embedded viewer remains optional and should be reconsidered only if the
standalone observation workflow demonstrates a concrete product need.

## Deferred

General expressions, variables, loops, parallelism, persistence, auth,
databases, embedded visualization, and production hardware adapters remain outside
the current core slice. See [docs/development-plan.md](docs/development-plan.md)
for the staged roadmap.

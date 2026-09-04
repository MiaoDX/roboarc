# Status

## Current

RoboArc is at the v0.1b visual authoring stage. The Python package, typed
contracts, generated schemas, asyncio runtime, deterministic MockAdapter, CLI,
FastAPI HTTP/WebSocket transport, and React/Blockly workbench are implemented.
Blockly remains editor state; compiled Workflow IR remains the executable
source of truth.

The workbench supports capability discovery, sequence/wait/capability blocks,
manifest-driven arguments, project download/upload, local and backend
validation, run/stop controls, stable block highlighting, progress, logs,
errors, duration, terminal results, and WebSocket reconnect/replay.

## Verification

The required local checks pass:

```text
28 Python tests passed; 23 Web unit tests passed; 7 Chromium browser workflows
passed, including success, failure, progress, timeout, supported cancellation,
incomplete cancellation, and 320/375/414/768px overflow checks.
ruff check .
mypy src/roboarc
schema regeneration has no diff
```

CI runs Python checks on 3.11, 3.12, and 3.13, plus Web format, lint,
typecheck, unit tests, schema drift, production build, Chromium workflows, and
high-severity dependency audit.

## Next

The next planned slice is a thin ROS 2 Action adapter spike to prove native
feedback, results, cancellation, and timeout cleanup before TIAGo simulation
work.

## Deferred

General expressions, variables, loops, parallelism, persistence, auth,
databases, and real robot/simulator adapters remain outside
the current core slice. See [docs/development-plan.md](docs/development-plan.md)
for the staged roadmap.

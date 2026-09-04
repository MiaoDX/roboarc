# Status

## Current

RoboArc has completed the v0.1c ROS 2 Action lifecycle proof. The Python package, typed
contracts, generated schemas, asyncio runtime, deterministic MockAdapter, CLI,
FastAPI HTTP/WebSocket transport, and React/Blockly workbench are implemented.
Blockly remains editor state; compiled Workflow IR remains the executable
source of truth.

The workbench supports capability discovery, sequence/wait/capability blocks,
manifest-driven arguments, project download/upload, local and backend
validation, run/stop controls, stable block highlighting, progress, logs,
errors, duration, terminal results, and WebSocket reconnect/replay.

The optional ROS 2 Jazzy harness proves that unchanged Workflow IR and runtime
contracts drive a genuine Action with native feedback, success, abort,
rejection, unavailable-server and transport failures, cancellation, timeout,
and incomplete-cancellation behavior. ROS remains outside the core package.

## Verification

The required local checks pass:

```text
28 core Python tests passed; 8 ROS Jazzy integration tests passed; 23 Web unit tests passed; 7 Chromium browser workflows
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

The next planned milestone is a narrow TIAGo simulation integration, using the
v0.1c lifecycle evidence before introducing robot-specific capabilities.

## Deferred

General expressions, variables, loops, parallelism, persistence, auth,
databases, and real robot/simulator adapters remain outside
the current core slice. See [docs/development-plan.md](docs/development-plan.md)
for the staged roadmap.

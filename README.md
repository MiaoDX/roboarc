# RoboArc

**Robot Action Representation & Composition**

Visual programming for robot behaviors, backed by a small observable runtime and editor-neutral contracts.

RoboArc composes product-level robot capabilities instead of exposing ROS topics, vendor SDK calls, or transport details directly in workflows. The React workbench embeds Blockly for authoring, but the canonical program is a typed Workflow IR that can target different robots through capability adapters.

<p align="center">
  <img src="docs/assets/architecture.svg" alt="RoboArc architecture" width="900" />
</p>

## Current status

The repository has completed the **v0.2a observable simulation loop**, including
the separate TIAGo ROS 2 Jazzy/Gazebo Harmonic proof lane. It contains:

- strict, versioned Pydantic contracts for Workflow IR, project files, capability manifests, robot profiles, validation reports, execution results, and runtime events;
- checked-in JSON Schemas generated from those contracts;
- a deliberately small IR with `sequence`, `wait`, and `capability` nodes;
- a Python `asyncio` runtime with deterministic validation, ordered event history, deadlines, cooperative cancellation, and truthful cancellation failure reporting;
- a deterministic `MockAdapter` covering success, staged progress, percentage progress, failure, cancellable work, and uncancellable work;
- a FastAPI service for discovery, validation, run control, event replay, and live WebSocket events;
- a React/TypeScript/Vite workbench with embedded Blockly authoring, manifest-driven arguments, project save/load, validation, run controls, and runtime telemetry;
- backend-neutral pose, trajectory, action-state, and progress observations
  exported as JSONL and optional native Rerun recordings;
- a deterministic simulation adapter and observable workflow that require no
  ROS or simulator installation;
- tests for contracts, runtime state transitions, adapter conformance, cancellation, timeout, CLI behavior, and HTTP/WebSocket integration;
- an optional ROS 2 Jazzy/Python 3.12 proof harness that drives an unchanged
  Workflow IR through the runtime and a genuine ROS Action; and
- a pinned TIAGo Jazzy/Gazebo Harmonic overlay and four-capability manual lane
  that runs the same observation contract against a live simulator stack.

The ROS and TIAGo lanes remain outside the core package and always-on CI. They
are integration proofs, not supported production robot adapters.

## Quick start

RoboArc currently requires Python 3.11 or newer.

```bash
python -m venv .venv
source .venv/bin/activate
python -m pip install -e ".[dev]"
python -m pytest
```

### Optional ROS 2 Action proof

The ROS integration is outside the core package. With Docker installed, run the CI acceptance lane locally:

```bash
docker build -f docker/ros-jazzy/Dockerfile -t roboarc-ros-jazzy .
docker run --rm roboarc-ros-jazzy
```

Validate and run the included workflow against the mock robot:

```bash
roboarc validate examples/workflows/mock-demo.json
roboarc run examples/workflows/mock-demo.json
```

Run the deterministic observable simulation and produce a native Rerun recording:

```bash
python -m pip install -e ".[rerun]"
roboarc simulate examples/workflows/simulation-observable.json \
  --trace simulation.jsonl --rerun simulation.rrd
roboarc view simulation.rrd
```

The separate TIAGo/Gazebo manual lane is documented in
[`docker/tiago-jazzy/README.md`](docker/tiago-jazzy/README.md). The repository
builds its pinned Jazzy/Harmonic overlay and runs the four-capability workflow
to correlated JSONL and Rerun artifacts.

Start the local runtime API:

```bash
roboarc serve --host 127.0.0.1 --port 8000
```

Start the Web workbench in another terminal:

```bash
cd web
npm ci
npm run dev
```

The workbench opens at `http://127.0.0.1:5173` and proxies the API to
`http://127.0.0.1:8000`. Set `ROBOARC_API_TARGET` when the API uses another
local port. Run the browser workflow gate with `npm run test:e2e`.

For a user-facing view of the recorded TIAGo workflow, open
`http://127.0.0.1:5173/?review=tiago`. This review view shows the four Workflow
IR steps, the completed run summary, the Gazebo MP4, and links to the JSONL and
Rerun artifacts. When the manifest includes Execution Timeline metadata, video
playback and seeking highlight the active Workflow IR node from the same run.
The timeline is recorded-playback synchronization, not live Gazebo control.
Serve the artifact directory on port 8080 as documented below;
Vite proxies it through `/artifacts`, so the browser uses one origin. When
sharing on a LAN, start Vite with `--host 0.0.0.0`. Set
`ROBOARC_ARTIFACT_TARGET` when the artifact server uses another local port.
The route is driven by `review.json`, not by the TIAGo workflow name: another
run can reuse it by serving its own schema-valid manifest and artifacts.

The OpenAPI UI is available at `/docs`. Core endpoints are under `/api/v1`:

```text
GET  /health
GET  /profile
GET  /capabilities
POST /workflows/validate
POST /runs
GET  /runs/{run_id}
POST /runs/{run_id}/cancel
GET  /runs/{run_id}/events
WS   /runs/{run_id}/events
```

Runtime events contain a per-run monotonic `seq`, so clients can reconnect with `after_seq` and replay missed events before consuming live updates.

## Principles

- **Capabilities over robot APIs** — workflows invoke stable robot behaviors rather than transport-specific APIs.
- **Workflow IR over editor state** — the editor is an authoring surface; typed IR defines execution semantics.
- **Adapters over platform coupling** — ROS 2, SDK, REST, gRPC, and other native interfaces remain outside the runtime core.
- **Observable execution** — progress, results, cancellation, errors, and logs are runtime contracts.
- **Portability where semantics permit** — shared IDs require compatible semantics, not merely matching names.
- **Small core** — new control-flow and platform features must be justified by concrete workflows.

## Repository layout

```text
src/roboarc/contracts/   Versioned external contracts
src/roboarc/runtime/     Validation, execution, events, MockAdapter, and deterministic simulation
src/roboarc/telemetry.py Backend-neutral pose, trajectory, action, and progress observations
src/roboarc/api/         FastAPI HTTP/WebSocket transport
src/roboarc_tiago/       Optional TIAGo ROS 2 integration package
schemas/                 Generated JSON Schemas
examples/workflows/      Executable Workflow IR examples
scripts/                 Schema generation tooling
tests/                   Contract, runtime, adapter, CLI, and API tests
web/src/                 React shell, Blockly editor, compiler, and runtime UI
web/e2e/                 Browser workflow and responsive-layout tests
```

## Documentation

- [Current status](STATUS.md)
- [Architecture overview](ARCHITECTURE.md)
- [Architecture](docs/architecture.md)
- [Design principles](docs/design-principles.md)
- [Capability model](docs/capability-model.md)
- [Workflow IR](docs/workflow-ir.md)
- [Runtime](docs/runtime.md)
- [Implementation status and handoff](docs/implementation-status.md)
- [Demo strategy](docs/demo-strategy.md)
- [Development plan](docs/development-plan.md)
- [Architecture review](docs/research/deep-review.md)
- [Ecosystem landscape](docs/research/ecosystem-landscape.md)

## License

MIT

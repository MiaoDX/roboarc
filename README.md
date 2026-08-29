# RoboArc

**Robot Action Representation & Composition**

Visual programming for robot behaviors, backed by a small observable runtime and editor-neutral contracts.

RoboArc composes product-level robot capabilities instead of exposing ROS topics, vendor SDK calls, or transport details directly in workflows. Blockly is the first planned authoring surface, but the canonical program is a typed Workflow IR that can target different robots through capability adapters.

<p align="center">
  <img src="docs/assets/architecture.svg" alt="RoboArc architecture" width="900" />
</p>

## Current status

The repository is in the **v0.1 core implementation** stage. The current branch contains:

- strict, versioned Pydantic contracts for Workflow IR, project files, capability manifests, robot profiles, validation reports, execution results, and runtime events;
- checked-in JSON Schemas generated from those contracts;
- a deliberately small IR with `sequence`, `wait`, and `capability` nodes;
- a Python `asyncio` runtime with deterministic validation, ordered event history, deadlines, cooperative cancellation, and truthful cancellation failure reporting;
- a deterministic `MockAdapter` covering success, staged progress, percentage progress, failure, cancellable work, and uncancellable work;
- a FastAPI service for discovery, validation, run control, event replay, and live WebSocket events;
- tests for contracts, runtime state transitions, adapter conformance, cancellation, timeout, CLI behavior, and HTTP/WebSocket integration.

The Blockly Web editor and real robot adapters are intentionally not included yet. The next implementation slice is the browser authoring/runtime UI, followed by a thin ROS 2 Action adapter test before TIAGo integration.

## Quick start

RoboArc currently requires Python 3.11 or newer.

```bash
python -m venv .venv
source .venv/bin/activate
python -m pip install -e ".[dev]"
python -m pytest
```

Validate and run the included workflow against the mock robot:

```bash
roboarc validate examples/workflows/mock-demo.json
roboarc run examples/workflows/mock-demo.json
```

Start the local runtime API:

```bash
roboarc serve --host 127.0.0.1 --port 8000
```

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
src/roboarc/runtime/     Validation, execution, events, and MockAdapter
src/roboarc/api/         FastAPI HTTP/WebSocket transport
schemas/                 Generated JSON Schemas
examples/workflows/      Executable Workflow IR examples
scripts/                 Schema generation tooling
tests/                   Contract, runtime, adapter, CLI, and API tests
```

## Documentation

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

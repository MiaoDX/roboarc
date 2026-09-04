# RoboArc User Guide

This guide covers the practical paths exposed by the repository. For the
shortest orientation, start with the [project README](../../README.md).

## Live demo catalog

Open the [RoboArc demo catalog](https://miaodx.com/roboarc/?review) to browse
recorded Mock, deterministic simulation, TIAGo, and Reachy runs. Select a demo
to inspect its canonical Workflow IR, Blockly rendering, completed result,
trace, and video recording.

The Pages site is rebuilt from the checked-in artifacts when `main` changes.
The same bundle is uploaded by CI as `roboarc-review-site-*` and can be served
offline with any static HTTP server.

## Local setup

RoboArc supports Python 3.11, 3.12, and 3.13.

```bash
python -m venv .venv
source .venv/bin/activate
python -m pip install -e ".[dev]"
python -m pytest
ruff check .
mypy src/roboarc
python -m compileall -q src scripts
```

## Run the workbench

Start the API:

```bash
roboarc serve --host 127.0.0.1 --port 8000
```

Start the Web app in another terminal:

```bash
cd web
npm ci
npm run dev
```

Open `http://127.0.0.1:5173`. The Web app uses the API at port 8000 by
default. Set `ROBOARC_API_TARGET` when the API is on another port.

Run the browser workflow suite with:

```bash
cd web
npm run test:e2e
```

## Run a workflow from the CLI

Validate and run the included mock workflow:

```bash
roboarc validate examples/workflows/mock-demo.json
roboarc run examples/workflows/mock-demo.json
```

Run the deterministic observable simulation and export trace artifacts:

```bash
python -m pip install -e ".[rerun]"
roboarc simulate examples/workflows/simulation-observable.json \
  --trace simulation.jsonl --rerun simulation.rrd
roboarc view simulation.rrd
```

## Serve recorded demos locally

The review server builds a catalog from valid manifests under `artifacts/` and
the workflow fixtures under `examples/workflows/`:

```bash
./scripts/serve_review.sh --host 0.0.0.0 --artifacts artifacts
```

Open `http://127.0.0.1:5173/?review`. Use
`ROBOARC_ARTIFACT_TARGET` when the artifact server is on another port. The
static review bundle can also be served after CI downloads it:

```bash
python -m http.server 8000 --directory review-site
```

Then open `http://127.0.0.1:8000/?review`.

## Robot integration proofs

These lanes are integration proofs outside the always-on core package:

- [ROS 2 Jazzy action proof](../plans/v0.1c-ros2-action.md) — builds and runs
  the action lifecycle harness in Docker.
- [TIAGo Jazzy/Gazebo lane](../../docker/tiago-jazzy/README.md) — builds the
  pinned simulator overlay and records the observable workflow.
- [Reachy 2 portability lane](../plans/v0.3-portability.md) — runs the SDK and
  MuJoCo proof using the same profile and capability contracts.

The proof artifacts are consumed by the Review catalog; they are not claims
that every robot is a drop-in production adapter.

## Where to read next

- [Workflow IR](../workflow-ir.md) for document structure and schema evolution.
- [Runtime semantics](../runtime.md) for execution, events, timeout, and
  cancellation behavior.
- [Architecture](../architecture.md) for the separation between authoring,
  contracts, runtime, and robot adapters.

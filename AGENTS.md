# RoboArc Agent Guide

RoboArc is a contract-first Python runtime for composing robot capabilities.
The canonical program is the typed Workflow IR; editor state and robot-native
transport details stay outside the runtime core.

## Start Here

- Current state and next work: [STATUS.md](STATUS.md)
- Project orientation: [README.md](README.md)
- Layer boundaries: [docs/architecture.md](docs/architecture.md)
- Runtime semantics: [docs/runtime.md](docs/runtime.md)

Read deeper docs only when the task touches that area. This file is already
startup context when injected by Codex; do not reread it as a prerequisite.

## Setup And Checks

```bash
python -m venv .venv
source .venv/bin/activate
python -m pip install -e ".[dev]"
python -m pytest
ruff check .
mypy src/roboarc
python -m compileall -q src scripts
python scripts/generate_schemas.py
git diff --exit-code -- schemas
```

The supported Python versions are 3.11, 3.12, and 3.13. Use the repository
`.venv`; do not install project dependencies into the system interpreter.
Enable automatic per-worktree setup with
`git config core.hooksPath .githooks` when desired.

## Boundaries

- Keep ROS/vendor imports out of `roboarc.contracts` and `roboarc.runtime`.
- Workflows remain declarative; do not add arbitrary code execution.
- Capability references include exact `{id, version}` pairs.
- A cancellation request is not a terminal cancellation result.
- New control-flow nodes need explicit success, failure, timeout, cancellation,
  and result-propagation semantics plus tests.

Use `docs/agents/` for durable agent-only runbooks if procedures grow beyond
this entrypoint. Human project truth belongs in `README.md`, `STATUS.md`,
`docs/architecture.md`, and linked documentation.

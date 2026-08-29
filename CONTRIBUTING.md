# Contributing to RoboArc

RoboArc is intentionally contract-first. Changes should preserve the boundary between authoring, Workflow IR, runtime semantics, and robot-native adapters.

## Development setup

```bash
python -m venv .venv
source .venv/bin/activate
python -m pip install -e ".[dev]"
python -m pytest
```

The supported Python versions are 3.11, 3.12, and 3.13.

## Required checks

Before opening a pull request, run:

```bash
python -m compileall -q src scripts
python -m pytest
python scripts/generate_schemas.py
git diff --exit-code -- schemas
```

Generated schemas are checked in so TypeScript and other consumers can use the same contracts without importing Python. Any contract change must regenerate the affected files and include migration or compatibility notes when semantics change.

## Architectural rules

1. The runtime core must not import ROS-specific or vendor-specific types.
2. Workflow documents remain declarative; arbitrary Python, JavaScript, shell, or code-evaluation nodes are out of scope.
3. A cancellation request is not a terminal result. Adapters must only return `canceled` after the native operation has actually stopped.
4. Capability IDs include an exact contract version at invocation sites.
5. New control-flow nodes require defined success, failure, timeout, cancellation, and result-propagation semantics before implementation.
6. Mock scenarios must be deterministic and suitable for always-on CI.

## Commit structure

Prefer small semantic commits that keep tests green. Contract changes, runtime behavior, transports, UI work, robot integrations, and documentation should normally remain independently reviewable.

"""Headless RoboArc command-line interface."""

from __future__ import annotations

import argparse
import asyncio
import sys
from collections.abc import Sequence
from pathlib import Path
from typing import Any

from pydantic import ValidationError

from roboarc.contracts import RunState, WorkflowDocument
from roboarc.runtime import (
    DeterministicSimulationAdapter,
    MockAdapter,
    Runtime,
    WorkflowValidationError,
)
from roboarc.telemetry import Observation, observation_from_event, write_trace


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(prog="roboarc")
    subparsers = parser.add_subparsers(dest="command", required=True)

    validate_parser = subparsers.add_parser(
        "validate", help="validate a workflow against MockAdapter"
    )
    validate_parser.add_argument("workflow", type=Path)

    run_parser = subparsers.add_parser("run", help="run a workflow against MockAdapter")
    run_parser.add_argument("workflow", type=Path)
    run_parser.add_argument(
        "--cancel-after-ms",
        type=int,
        default=None,
        help="request cancellation after a deterministic delay",
    )
    run_parser.add_argument(
        "--trace", type=Path, default=None, help="write JSONL observation trace"
    )
    run_parser.add_argument(
        "--rerun", type=Path, default=None, help="write an optional Rerun .rrd recording"
    )

    view_parser = subparsers.add_parser("view", help="open a Rerun .rrd recording")
    view_parser.add_argument("recording", type=Path)
    view_parser.add_argument("--web", action="store_true", help="open the Rerun Web Viewer")

    simulate_parser = subparsers.add_parser(
        "simulate", help="run a workflow against the deterministic simulation adapter"
    )
    simulate_parser.add_argument("workflow", type=Path)
    simulate_parser.add_argument("--trace", type=Path, default=None)
    simulate_parser.add_argument("--rerun", type=Path, default=None)

    serve_parser = subparsers.add_parser("serve", help="start the local HTTP/WebSocket runtime")
    serve_parser.add_argument("--host", default="127.0.0.1")
    serve_parser.add_argument("--port", type=int, default=8000)
    profile_group = serve_parser.add_mutually_exclusive_group()
    profile_group.add_argument(
        "--profile",
        choices=("mock", "deterministic-simulation", "tiago-sim", "reachy2-sim"),
        default="mock",
        help="select the single adapter profile for this process",
    )
    profile_group.add_argument(
        "--tiago", action="store_true", help="serve the explicit TIAGo ROS adapter"
    )
    return parser


def load_workflow(path: Path) -> WorkflowDocument:
    return WorkflowDocument.model_validate_json(path.read_text(encoding="utf-8"))


async def _validate(path: Path) -> int:
    adapter = MockAdapter()
    runtime = Runtime(adapter)
    workflow = load_workflow(path)
    report = runtime.validate(workflow)
    print(report.model_dump_json(indent=2))
    return 0 if report.valid else 2


async def _run(
    path: Path,
    cancel_after_ms: int | None,
    trace: Path | None = None,
    rerun: Path | None = None,
) -> int:
    adapter = MockAdapter()
    runtime = Runtime(adapter)
    workflow = load_workflow(path)
    handle = await runtime.start(workflow)

    async def request_cancel() -> None:
        if cancel_after_ms is None:
            return
        await asyncio.sleep(cancel_after_ms / 1000)
        await handle.cancel()

    cancel_task = asyncio.create_task(request_cancel())
    try:
        async for event in handle.stream.subscribe():
            print(event.model_dump_json())
        result = await handle.result()
    finally:
        if not cancel_task.done():
            cancel_task.cancel()
        await asyncio.gather(cancel_task, return_exceptions=True)
        await adapter.wait_for_idle()

    if trace is not None:
        write_trace(trace, handle.stream.history)
    if rerun is not None:
        from roboarc.rerun import write_rrd

        write_rrd(rerun, handle.stream.history)
    return 0 if result.state is RunState.SUCCEEDED else 1


async def _simulate(path: Path, trace: Path | None, rerun: Path | None) -> int:
    adapter = DeterministicSimulationAdapter()
    handle = await Runtime(adapter).start(load_workflow(path))
    result = await handle.result()
    records: tuple[Observation, ...] = tuple(
        sorted(
            (*map(observation_from_event, handle.stream.history), *adapter.telemetry),
            key=lambda item: item.timestamp,
        )
    )
    if trace is not None:
        write_trace(trace, records)
    if rerun is not None:
        from roboarc.rerun import write_rrd

        write_rrd(rerun, records)
    return 0 if result.state is RunState.SUCCEEDED else 1


def main(argv: Sequence[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    try:
        if args.command == "validate":
            return asyncio.run(_validate(args.workflow))
        if args.command == "run":
            if args.cancel_after_ms is not None and args.cancel_after_ms < 0:
                raise ValueError("--cancel-after-ms must be non-negative")
            return asyncio.run(_run(args.workflow, args.cancel_after_ms, args.trace, args.rerun))
        if args.command == "view":
            from roboarc.rerun import open_rrd

            return open_rrd(args.recording, web=args.web)
        if args.command == "simulate":
            return asyncio.run(_simulate(args.workflow, args.trace, args.rerun))
        if args.command == "serve":
            if not 1 <= args.port <= 65535:
                raise ValueError("--port must be between 1 and 65535")
            import uvicorn

            profile_id = "tiago-sim" if args.tiago else args.profile
            app = _app_for_profile(profile_id)
            uvicorn.run(app, host=args.host, port=args.port, reload=False)
            return 0
    except FileNotFoundError as exc:
        print(f"error: {exc}", file=sys.stderr)
        return 2
    except (ValidationError, WorkflowValidationError, ValueError, RuntimeError) as exc:
        if isinstance(exc, WorkflowValidationError):
            print(exc.report.model_dump_json(indent=2), file=sys.stderr)
        else:
            print(f"error: {exc}", file=sys.stderr)
        return 2
    return 2


def _app_for_profile(profile_id: str) -> Any:
    if profile_id == "mock":
        return "roboarc.api.app:app"
    if profile_id == "tiago-sim":
        return "roboarc_tiago.api_app:app"
    if profile_id == "reachy2-sim":
        return "roboarc_reachy.api_app:app"
    if profile_id == "deterministic-simulation":
        from roboarc.api import create_app

        return create_app(DeterministicSimulationAdapter())
    raise ValueError(f"unknown profile: {profile_id}")


if __name__ == "__main__":
    raise SystemExit(main())

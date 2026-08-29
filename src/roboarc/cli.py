"""Headless RoboArc command-line interface."""

from __future__ import annotations

import argparse
import asyncio
import json
import sys
from pathlib import Path
from typing import Sequence

from pydantic import ValidationError

from roboarc.contracts import RunState, WorkflowDocument
from roboarc.runtime import MockAdapter, Runtime, WorkflowValidationError


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


async def _run(path: Path, cancel_after_ms: int | None) -> int:
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

    return 0 if result.state is RunState.SUCCEEDED else 1


def main(argv: Sequence[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    try:
        if args.command == "validate":
            return asyncio.run(_validate(args.workflow))
        if args.command == "run":
            if args.cancel_after_ms is not None and args.cancel_after_ms < 0:
                raise ValueError("--cancel-after-ms must be non-negative")
            return asyncio.run(_run(args.workflow, args.cancel_after_ms))
    except FileNotFoundError as exc:
        print(f"error: {exc}", file=sys.stderr)
        return 2
    except (ValidationError, WorkflowValidationError, ValueError) as exc:
        if isinstance(exc, WorkflowValidationError):
            print(exc.report.model_dump_json(indent=2), file=sys.stderr)
        else:
            print(f"error: {exc}", file=sys.stderr)
        return 2
    return 2


if __name__ == "__main__":
    raise SystemExit(main())

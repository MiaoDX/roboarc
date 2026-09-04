"""Run the TIAGo observable workflow against an already running Gazebo stack."""

from __future__ import annotations

import argparse
import asyncio
import json
from pathlib import Path

from roboarc.contracts import WorkflowDocument
from roboarc.runtime import Runtime
from roboarc.telemetry import write_trace

from .adapter import TiagoRosAdapter


async def run(workflow_path: Path, trace_path: Path, rerun_path: Path | None) -> int:
    workflow = WorkflowDocument.model_validate_json(workflow_path.read_text(encoding="utf-8"))
    adapter = TiagoRosAdapter()
    try:
        handle = await Runtime(adapter).start(workflow)
        result = await handle.result()
        records = (*handle.stream.snapshot(), *adapter.telemetry)
        write_trace(trace_path, records)
        if rerun_path is not None:
            from roboarc.rerun import write_rrd

            write_rrd(rerun_path, records)
        print(json.dumps(result.model_dump(mode="json"), indent=2))
        print(f"wrote {len(records)} observations to {trace_path}")
        return 0 if result.state.value == "succeeded" else 1
    finally:
        await adapter.close()


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "--workflow",
        type=Path,
        default=Path("examples/workflows/tiago-observable.json"),
    )
    parser.add_argument("--trace", type=Path, default=Path("tiago-observable.jsonl"))
    parser.add_argument("--rerun", type=Path, default=Path("tiago-observable.rrd"))
    args = parser.parse_args()
    return asyncio.run(run(args.workflow, args.trace, args.rerun))


if __name__ == "__main__":
    raise SystemExit(main())

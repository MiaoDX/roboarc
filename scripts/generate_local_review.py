#!/usr/bin/env python3
"""Generate complete review artifacts for non-GUI local demo workflows."""

from __future__ import annotations

import argparse
import asyncio
import json
import subprocess
from datetime import UTC
from pathlib import Path

from roboarc.contracts import RunState, WorkflowDocument
from roboarc.rerun import write_rrd
from roboarc.runtime import DeterministicSimulationAdapter, MockAdapter, Runtime
from roboarc.telemetry import Observation, observation_from_event, write_trace


async def generate(workflow_path: Path, output_root: Path, adapter_name: str) -> Path:
    workflow = WorkflowDocument.model_validate_json(workflow_path.read_text(encoding="utf-8"))
    adapter = MockAdapter() if adapter_name == "mock" else DeterministicSimulationAdapter()
    runtime = Runtime(adapter)
    handle = await runtime.start(workflow)
    result = await handle.result()
    await getattr(adapter, "wait_for_idle", lambda: asyncio.sleep(0))()

    output = output_root / workflow.id
    output.mkdir(parents=True, exist_ok=True)
    trace_records: tuple[Observation, ...]
    if adapter_name == "mock":
        trace_records = tuple(observation_from_event(event) for event in handle.stream.history)
    else:
        trace_records = tuple(
            sorted(
                (*map(observation_from_event, handle.stream.history), *adapter.telemetry),
                key=lambda item: item.timestamp,
            )
        )
    trace_path = output / "trace.jsonl"
    rerun_path = output / "trace.rrd"
    video_path = output / "runtime-replay.mp4"
    write_trace(trace_path, trace_records)
    write_rrd(rerun_path, trace_records)
    origin = result.started_at.astimezone(UTC)
    duration = max(3.0, (result.finished_at - result.started_at).total_seconds() + 2.0)
    _write_video(video_path, workflow.name, adapter.profile.title, handle.run_id, duration)
    manifest = {
        "review_schema_version": 1,
        "workflow": workflow.model_dump(mode="json"),
        "result": result.model_dump(mode="json"),
        "profile_id": adapter.profile.id,
        "observation_count": len(trace_records),
        "artifacts": {"trace": trace_path.name, "rerun": rerun_path.name, "video": video_path.name},
        "timeline": {
            "timebase": "utc",
            "media": [
                {
                    "id": "runtime-replay",
                    "artifact": video_path.name,
                    "origin": origin.isoformat(),
                }
            ],
        },
    }
    (output / "review.json").write_text(json.dumps(manifest, indent=2), encoding="utf-8")
    if result.state is not RunState.SUCCEEDED:
        raise RuntimeError(f"{workflow.id} finished as {result.state}")
    return output


def _write_video(path: Path, title: str, profile: str, run_id: str, duration: float) -> None:
    safe_title = title.replace("'", "\\'").replace(":", "\\:")
    safe_profile = profile.replace("'", "\\'").replace(":", "\\:")
    safe_run = run_id.replace("'", "\\'").replace(":", "\\:")
    drawtext = (
        "drawtext=fontcolor=white:fontsize=44:x=80:y=150:"
        f"text='{safe_title}',"
        "drawtext=fontcolor=white:fontsize=28:x=80:y=240:"
        f"text='Profile: {safe_profile}',"
        "drawtext=fontcolor=#9bd3ff:fontsize=25:x=80:y=320:"
        "text='Runtime trace replay',"
        "drawtext=fontcolor=#b9c6d1:fontsize=20:x=80:y=390:"
        f"text='Run: {safe_run}'"
    )
    subprocess.run(
        [
            "ffmpeg", "-y", "-f", "lavfi", "-i", "color=c=0x15202a:s=1280x720:r=30",
            "-t", f"{duration:.3f}", "-vf", drawtext, "-c:v", "libx264", "-pix_fmt", "yuv420p",
            "-movflags", "+faststart", str(path),
        ],
        check=True,
        capture_output=True,
        text=True,
    )


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("workflow", type=Path)
    parser.add_argument("--adapter", choices=("mock", "simulation"), required=True)
    parser.add_argument("--output-root", type=Path, default=Path("artifacts"))
    args = parser.parse_args()
    output = asyncio.run(generate(args.workflow, args.output_root, args.adapter))
    print(output)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

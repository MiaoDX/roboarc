"""Run the Reachy workflow against an already running SDK-facing MuJoCo server."""

from __future__ import annotations

import argparse
import asyncio
import json
from pathlib import Path

from roboarc.contracts import WorkflowDocument
from roboarc.rerun import write_rrd
from roboarc.runtime import Runtime
from roboarc.telemetry import write_trace
from roboarc_reachy import ReachyAdapter, connect_reachy


async def run(
    *,
    workflow_path: Path,
    output_dir: Path,
    host: str,
    port: int,
    video_name: str,
    video_origin: str,
) -> int:
    workflow = WorkflowDocument.model_validate_json(
        workflow_path.read_text(encoding="utf-8")
    )
    output_dir.mkdir(parents=True, exist_ok=True)
    adapter = ReachyAdapter(connect_reachy(host, port))
    handle = await Runtime(adapter).start(workflow)
    result = await handle.result()
    events = handle.stream.history

    workflow_output = output_dir / "reachy-observable.json"
    result_output = output_dir / "result.json"
    trace_output = output_dir / "reachy-observable.jsonl"
    rerun_output = output_dir / "reachy-observable.rrd"
    manifest_output = output_dir / "review.json"
    workflow_output.write_text(
        workflow.model_dump_json(indent=2), encoding="utf-8"
    )
    result_output.write_text(result.model_dump_json(indent=2), encoding="utf-8")
    write_trace(trace_output, events)
    write_rrd(rerun_output, events)
    manifest_output.write_text(
        json.dumps(
            {
                "review_schema_version": 1,
                "workflow": workflow.model_dump(mode="json"),
                "result": result.model_dump(mode="json"),
                "profile_id": adapter.profile.id,
                "observation_count": len(events),
                "provenance": {
                    "image": "roboarc-reachy2-proof",
                    "image_digest": (
                        "sha256:b6cf0b7ddc5c16ef018203949985a75f8899619cb9f9e8c9300b2516093a908f"
                    ),
                    "base_image": (
                        "python:3.11-slim@sha256:9534e5a8e315485d4061ed659af0fd78a284c015f9b73661b41d6bab25604534"
                    ),
                    "platform": "linux/amd64",
                    "reachy2_mujoco_commit": "f6d8284e812d3b96b557e2e844d55bd09d6e3ee6",
                    "reachy2_symbolic_ik_commit": "31e6a2375f83d09e19af16dadb7f70bb96fbbd65",
                    "mujoco_version": "3.2.6",
                    "launch_args": ["reachy2-mujoco"],
                    "display": ":99",
                    "rendering": "egl",
                },
                "media": {
                    "codec": "h264",
                    "width": 1280,
                    "height": 720,
                    "fps": 30,
                    "duration_seconds": round(
                        (result.finished_at - result.started_at).total_seconds(), 6
                    ),
                },
                "artifacts": {
                    "trace": trace_output.name,
                    "rerun": rerun_output.name,
                    "video": video_name,
                },
                "timeline": {
                    "timebase": "utc",
                    "media": [
                        {
                            "id": "mujoco-viewer",
                            "artifact": video_name,
                            "origin": video_origin,
                        }
                    ],
                },
            },
            indent=2,
        ),
        encoding="utf-8",
    )
    print(result.model_dump_json(indent=2))
    print(f"wrote {len(events)} events to {output_dir}")
    return 0 if result.state.value == "succeeded" else 1


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "--workflow",
        type=Path,
        default=Path("examples/workflows/reachy-observable.json"),
    )
    parser.add_argument("--output-dir", type=Path, required=True)
    parser.add_argument("--host", default="127.0.0.1")
    parser.add_argument("--port", type=int, default=18861)
    parser.add_argument("--video", default="mujoco-review.mp4")
    parser.add_argument("--video-origin", required=True)
    args = parser.parse_args()
    return asyncio.run(
        run(
            workflow_path=args.workflow,
            output_dir=args.output_dir,
            host=args.host,
            port=args.port,
            video_name=args.video,
            video_origin=args.video_origin,
        )
    )


if __name__ == "__main__":
    raise SystemExit(main())

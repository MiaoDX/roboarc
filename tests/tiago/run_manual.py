"""Run the TIAGo observable workflow against an already running Gazebo stack."""

from __future__ import annotations

import argparse
import asyncio
import json
from pathlib import Path

from roboarc.contracts import WorkflowDocument
from roboarc.runtime import Runtime
from roboarc.telemetry import write_trace
from roboarc_tiago.adapter import TiagoRosAdapter


async def run(
    workflow_path: Path,
    trace_path: Path,
    rerun_path: Path | None,
    manifest_path: Path | None,
    video_name: str,
    video_origin: str | None,
) -> int:
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
        if manifest_path is not None:
            manifest_path.write_text(
                json.dumps(
                    {
                        "review_schema_version": 1,
                        "workflow": workflow.model_dump(mode="json"),
                        "result": result.model_dump(mode="json"),
                        "profile_id": adapter.profile.id,
                        "observation_count": len(records),
                        "artifacts": {
                            "trace": trace_path.name,
                            "rerun": rerun_path.name if rerun_path else None,
                            "video": video_name,
                        },
                    },
                    indent=2,
                ),
                encoding="utf-8",
            )
            if video_origin:
                manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
                manifest["timeline"] = {
                    "timebase": "utc",
                    "media": [
                        {
                            "id": "gazebo-camera",
                            "artifact": video_name,
                            "origin": video_origin,
                        }
                    ],
                }
                manifest_path.write_text(
                    json.dumps(manifest, indent=2), encoding="utf-8"
                )
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
    parser.add_argument("--manifest", type=Path, default=Path("review.json"))
    parser.add_argument("--video", default="gazebo-review.mp4")
    parser.add_argument("--video-origin", default=None)
    args = parser.parse_args()
    return asyncio.run(
        run(args.workflow, args.trace, args.rerun, args.manifest, args.video, args.video_origin)
    )


if __name__ == "__main__":
    raise SystemExit(main())

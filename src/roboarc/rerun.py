"""Optional Rerun export and viewer integration.

The Rerun SDK is imported only when an ``.rrd`` recording is requested, so
RoboArc's runtime and JSONL trace path do not depend on it.
"""

from __future__ import annotations

import importlib
import json
import shutil
import subprocess
from collections.abc import Iterable
from pathlib import Path
from typing import Any

from roboarc.telemetry import Observation, observations


class RerunUnavailableError(RuntimeError):
    """Raised when the optional Rerun SDK or viewer is unavailable."""


def write_rrd(path: Path, events: Iterable[Any]) -> int:
    """Write runtime events and telemetry to a native Rerun recording."""

    rr = _load_sdk()
    records = observations(events)
    recording_id = records[0].run_id if records else "empty"
    recording = rr.RecordingStream("roboarc", recording_id=recording_id)
    recording.save(path)
    try:
        for sequence, record in enumerate(records, start=1):
            recording.set_time("event_seq", sequence=sequence)
            recording.set_time("wall_clock", timestamp=record.timestamp)
            _log_record(rr, recording, record)
        recording.flush()
    finally:
        recording.disconnect()
    return len(records)


def open_rrd(path: Path, *, web: bool = False) -> int:
    """Open an existing recording in the installed Rerun viewer."""

    executable = shutil.which("rerun")
    if executable is None:
        raise RerunUnavailableError(
            "Rerun viewer is not installed; install RoboArc with the 'rerun' extra"
        )
    command = [executable, str(path)]
    if web:
        command.append("--web-viewer")
    return subprocess.run(command, check=False).returncode


def _load_sdk() -> Any:
    try:
        return importlib.import_module("rerun")
    except ImportError as exc:
        raise RerunUnavailableError(
            "Rerun SDK is not installed; install RoboArc with the 'rerun' extra"
        ) from exc


def _log_record(rr: Any, recording: Any, record: Observation) -> None:
    entity = _entity_path(record)
    level = "ERROR" if record.kind == "error" else "INFO"
    recording.log(
        f"{entity}/events",
        rr.TextLog(json.dumps(record.as_dict(), sort_keys=True), level=level),
    )

    if record.kind == "capability.progress" and isinstance(
        record.data.get("percent"), (int, float)
    ):
        recording.log(f"{entity}/progress", rr.Scalars(float(record.data["percent"])))

    if record.kind == "robot.pose":
        position = record.data.get("position")
        if _is_vec3(position):
            recording.log(f"{entity}/pose", rr.Points3D([position]))

    if record.kind == "robot.trajectory":
        points = record.data.get("points")
        positions = _trajectory_positions(points)
        if positions:
            recording.log(f"{entity}/trajectory", rr.LineStrips3D([positions]))


def _entity_path(record: Observation) -> str:
    parts = ["runs", record.run_id]
    if record.node_id is not None:
        parts.extend(("nodes", record.node_id))
    if record.invocation_id is not None:
        parts.extend(("invocations", record.invocation_id))
    return "/".join(_safe_entity_part(part) for part in parts)


def _safe_entity_part(value: str) -> str:
    return value.replace("/", "_")


def _is_vec3(value: object) -> bool:
    return (
        isinstance(value, (list, tuple))
        and len(value) == 3
        and all(isinstance(component, (int, float)) for component in value)
    )


def _trajectory_positions(value: object) -> list[list[float]]:
    """Extract positions from the typed trajectory JSON representation."""
    if not isinstance(value, list):
        return []
    result: list[list[float]] = []
    for point in value:
        if not isinstance(point, dict):
            return []
        pose = point.get("pose")
        if not isinstance(pose, dict) or not _is_vec3(pose.get("position")):
            return []
        result.append([float(component) for component in pose["position"]])
    return result

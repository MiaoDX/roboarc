from __future__ import annotations

import importlib.util
import shutil
import subprocess
from datetime import UTC, datetime, timedelta
from pathlib import Path
from typing import Any

import pytest

from roboarc.cli import load_workflow, main
from roboarc.rerun import write_rrd
from roboarc.runtime import MockAdapter, Runtime
from roboarc.telemetry import Observation, Pose, Trajectory, TrajectoryPoint


def test_run_command_writes_rerun_recording(monkeypatch, tmp_path: Path) -> None:
    output = tmp_path / "run.rrd"
    calls: list[tuple[Path, tuple[Any, ...]]] = []

    def capture(path: Path, events: tuple[Any, ...]) -> int:
        calls.append((path, tuple(events)))
        return len(events)

    monkeypatch.setattr("roboarc.rerun.write_rrd", capture)
    exit_code = main(["run", "examples/workflows/mock-demo.json", "--rerun", str(output)])

    assert exit_code == 0
    assert calls[0][0] == output
    assert calls[0][1][0].type.value == "run.started"
    assert calls[0][1][-1].type.value == "run.finished"


def test_view_command_invokes_rerun(monkeypatch, tmp_path: Path) -> None:
    recording = tmp_path / "run.rrd"
    monkeypatch.setattr("roboarc.rerun.shutil.which", lambda name: "/usr/bin/rerun")
    commands: list[list[str]] = []

    def run(command: list[str], *, check: bool) -> Any:
        commands.append(command)
        return subprocess.CompletedProcess(command, 0)

    monkeypatch.setattr("roboarc.rerun.subprocess.run", run)

    assert main(["view", str(recording), "--web"]) == 0
    assert commands == [["/usr/bin/rerun", str(recording), "--web-viewer"]]


@pytest.mark.asyncio
async def test_native_rrd_is_replayable_when_rerun_is_installed(tmp_path: Path) -> None:
    if importlib.util.find_spec("rerun") is None or shutil.which("rerun") is None:
        pytest.skip("optional Rerun SDK and CLI are not installed")

    runtime = Runtime(MockAdapter())
    workflow = load_workflow(Path("examples/workflows/mock-demo.json"))
    handle = await runtime.start(workflow)
    await handle.result()

    timestamp = datetime(2020, 1, 1, tzinfo=UTC)
    start = Pose("map", (0.0, 0.0, 0.0), (0.0, 0.0, 0.0, 1.0))
    finish = Pose("map", (1.0, 2.0, 0.0), (0.0, 0.0, 0.0, 1.0))
    spatial = (
        Observation.pose(timestamp=timestamp, run_id=handle.run_id, pose=finish),
        Observation.trajectory(
            timestamp=timestamp,
            run_id=handle.run_id,
            trajectory=Trajectory(
                (
                    TrajectoryPoint(timestamp, start),
                    TrajectoryPoint(timestamp + timedelta(seconds=1), finish),
                ),
                frame_id="map",
            ),
        ),
    )

    output = tmp_path / "run.rrd"
    records = (*handle.stream.history, *spatial)
    assert write_rrd(output, records) == len(records)
    assert output.stat().st_size > 0
    verification = subprocess.run(
        ["rerun", "rrd", "verify", str(output)],
        check=False,
        capture_output=True,
        text=True,
    )
    assert verification.returncode == 0, verification.stderr
    printed = subprocess.run(
        ["rerun", "rrd", "print", str(output)],
        check=False,
        capture_output=True,
        text=True,
    )
    assert printed.returncode == 0, printed.stderr
    assert "/pose" in printed.stdout
    assert "/trajectory" in printed.stdout

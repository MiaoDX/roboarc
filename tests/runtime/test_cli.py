from __future__ import annotations

from roboarc.cli import main
from roboarc.telemetry import TelemetryKind


def test_validate_command(capsys) -> None:
    exit_code = main(["validate", "examples/workflows/mock-demo.json"])
    captured = capsys.readouterr()
    assert exit_code == 0
    assert '"valid": true' in captured.out


def test_run_command_emits_json_lines(capsys) -> None:
    exit_code = main(["run", "examples/workflows/mock-demo.json"])
    captured = capsys.readouterr()
    assert exit_code == 0
    assert '"type":"run.started"' in captured.out
    assert '"type":"run.finished"' in captured.out


def test_simulate_command_writes_correlated_robot_trace(tmp_path) -> None:
    trace = tmp_path / "simulation.jsonl"
    exit_code = main(
        ["simulate", "examples/workflows/simulation-observable.json", "--trace", str(trace)]
    )
    records = [__import__("json").loads(line) for line in trace.read_text().splitlines()]

    assert exit_code == 0
    kinds = {record["kind"] for record in records}
    assert TelemetryKind.POSE in kinds
    assert TelemetryKind.TRAJECTORY in kinds
    assert TelemetryKind.PROGRESS in kinds
    telemetry_kinds = {kind.value for kind in TelemetryKind}
    correlated = [record for record in records if record["kind"] in telemetry_kinds]
    assert {record["node_id"] for record in correlated} == {"navigate"}
    assert len({record["invocation_id"] for record in correlated}) == 1

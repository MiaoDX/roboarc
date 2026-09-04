from __future__ import annotations

from roboarc.cli import main
from roboarc.telemetry import TelemetryKind


def test_serve_tiago_selects_explicit_app(monkeypatch) -> None:
    invoked: dict[str, object] = {}

    def fake_run(app: str, **kwargs: object) -> None:
        invoked.update(app=app, **kwargs)

    monkeypatch.setattr("uvicorn.run", fake_run)

    assert main(["serve", "--tiago", "--host", "0.0.0.0", "--port", "8765"]) == 0
    assert invoked == {
        "app": "roboarc_tiago.api_app:app",
        "host": "0.0.0.0",
        "port": 8765,
        "reload": False,
    }


def test_serve_selects_one_startup_profile(monkeypatch) -> None:
    invoked: dict[str, object] = {}

    def fake_run(app: object, **kwargs: object) -> None:
        invoked.update(app=app, **kwargs)

    monkeypatch.setattr("uvicorn.run", fake_run)

    assert main(["serve", "--profile", "deterministic-simulation"]) == 0
    assert invoked["app"].state.runtime.registry.profile.id == "deterministic-simulation"


def test_serve_selects_reachy_sdk_app(monkeypatch) -> None:
    invoked = {}
    monkeypatch.setattr("uvicorn.run", lambda app, **kwargs: invoked.update(app=app, **kwargs))
    assert main(["serve", "--profile", "reachy2-sim"]) == 0
    assert invoked["app"] == "roboarc_reachy.api_app:app"


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

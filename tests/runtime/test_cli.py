from __future__ import annotations

from roboarc.cli import main


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

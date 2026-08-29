from __future__ import annotations

from pathlib import Path

from scripts.generate_schemas import SCHEMA_MODELS, generate


def test_checked_in_schemas_are_current(tmp_path: Path) -> None:
    generate(tmp_path)
    for filename in SCHEMA_MODELS:
        expected = (tmp_path / filename).read_text(encoding="utf-8")
        actual = (Path("schemas") / filename).read_text(encoding="utf-8")
        assert actual == expected, f"schema is stale: {filename}"

"""Generate checked-in JSON Schemas for cross-language consumers."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from pydantic import BaseModel

from roboarc.contracts import (
    CapabilityManifest,
    ProjectDocument,
    RobotProfile,
    RuntimeEvent,
    ValidationReport,
    WorkflowDocument,
)

SCHEMA_MODELS: dict[str, type[BaseModel]] = {
    "capability-manifest.schema.json": CapabilityManifest,
    "project.schema.json": ProjectDocument,
    "robot-profile.schema.json": RobotProfile,
    "runtime-event.schema.json": RuntimeEvent,
    "validation-report.schema.json": ValidationReport,
    "workflow.schema.json": WorkflowDocument,
}


def render_schema(model: type[BaseModel]) -> str:
    schema: dict[str, Any] = model.model_json_schema()
    schema["$schema"] = "https://json-schema.org/draft/2020-12/schema"
    return json.dumps(schema, indent=2, sort_keys=True) + "\n"


def generate(output_dir: Path) -> None:
    output_dir.mkdir(parents=True, exist_ok=True)
    for filename, model in SCHEMA_MODELS.items():
        (output_dir / filename).write_text(render_schema(model), encoding="utf-8")


if __name__ == "__main__":
    generate(Path(__file__).resolve().parents[1] / "schemas")

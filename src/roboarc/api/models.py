"""HTTP API response contracts."""

from __future__ import annotations

from typing import Literal

from pydantic import Field

from roboarc.contracts import RunResult, RunState
from roboarc.contracts.common import ContractModel


class HealthResponse(ContractModel):
    status: Literal["ok"] = "ok"
    service: Literal["roboarc-runtime"] = "roboarc-runtime"
    api_version: Literal[1] = 1


class StartRunResponse(ContractModel):
    run_id: str = Field(pattern=r"^[A-Za-z][A-Za-z0-9._-]{0,127}$")
    profile_id: str
    state: RunState


class CancelRunResponse(ContractModel):
    run_id: str
    accepted: bool
    state: RunState


class RunSnapshot(ContractModel):
    run_id: str
    profile_id: str
    state: RunState
    done: bool
    last_seq: int = Field(ge=0)
    result: RunResult | None = None

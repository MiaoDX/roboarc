"""FastAPI transport for discovery, validation, run control, and events."""

from __future__ import annotations

from collections.abc import AsyncIterator
from contextlib import asynccontextmanager

from fastapi import FastAPI, HTTPException, Query, WebSocket, WebSocketDisconnect, status

from roboarc.api.models import (
    CancelRunResponse,
    HealthResponse,
    RunSnapshot,
    StartRunResponse,
)
from roboarc.contracts import (
    CapabilityManifest,
    RobotProfile,
    RuntimeEvent,
    ValidationReport,
    WorkflowDocument,
)
from roboarc.runtime import (
    CapabilityAdapter,
    MockAdapter,
    RunHandle,
    Runtime,
    RuntimeConfig,
    WorkflowValidationError,
)

API_PREFIX = "/api/v1"


def create_app(
    adapter: CapabilityAdapter | None = None,
    *,
    runtime_config: RuntimeConfig | None = None,
) -> FastAPI:
    active_adapter = adapter or MockAdapter()
    runtime = Runtime(active_adapter, config=runtime_config)

    @asynccontextmanager
    async def lifespan(_: FastAPI) -> AsyncIterator[None]:
        yield
        await runtime.shutdown()
        close = getattr(active_adapter, "close", None)
        if close is not None:
            await close()
        else:
            wait_for_idle = getattr(active_adapter, "wait_for_idle", None)
            if wait_for_idle is not None:
                await wait_for_idle()

    app = FastAPI(
        title="RoboArc Runtime API",
        version="0.1.0-dev",
        description="Local-first API for validated, observable robot workflows.",
        lifespan=lifespan,
    )
    app.state.runtime = runtime
    app.state.adapter = active_adapter

    @app.get(f"{API_PREFIX}/health", response_model=HealthResponse)
    async def health() -> HealthResponse:
        return HealthResponse()

    @app.get(f"{API_PREFIX}/profile", response_model=RobotProfile)
    async def profile() -> RobotProfile:
        return runtime.registry.profile

    @app.get(f"{API_PREFIX}/capabilities", response_model=list[CapabilityManifest])
    async def capabilities() -> list[CapabilityManifest]:
        return list(runtime.registry.manifests)

    @app.post(f"{API_PREFIX}/workflows/validate", response_model=ValidationReport)
    async def validate_workflow_endpoint(workflow: WorkflowDocument) -> ValidationReport:
        return runtime.validate(workflow)

    @app.post(
        f"{API_PREFIX}/runs",
        response_model=StartRunResponse,
        status_code=status.HTTP_201_CREATED,
    )
    async def start_run(workflow: WorkflowDocument) -> StartRunResponse:
        try:
            handle = await runtime.start(workflow)
        except WorkflowValidationError as exc:
            raise HTTPException(
                status_code=422,
                detail=exc.report.model_dump(mode="json"),
            ) from exc
        return StartRunResponse(run_id=handle.run_id, state=handle.state)

    @app.get(f"{API_PREFIX}/runs/{{run_id}}", response_model=RunSnapshot)
    async def get_run(run_id: str) -> RunSnapshot:
        handle = _require_run(runtime, run_id)
        return RunSnapshot(
            run_id=run_id,
            state=handle.state,
            done=handle.done,
            last_seq=handle.stream.last_seq,
            result=handle.result_if_done(),
        )

    @app.post(f"{API_PREFIX}/runs/{{run_id}}/cancel", response_model=CancelRunResponse)
    async def cancel_run(run_id: str) -> CancelRunResponse:
        handle = _require_run(runtime, run_id)
        accepted = await handle.cancel()
        return CancelRunResponse(run_id=run_id, accepted=accepted, state=handle.state)

    @app.get(f"{API_PREFIX}/runs/{{run_id}}/events", response_model=list[RuntimeEvent])
    async def get_events(
        run_id: str,
        after_seq: int = Query(default=0, ge=0),
    ) -> list[RuntimeEvent]:
        handle = _require_run(runtime, run_id)
        return list(handle.stream.snapshot(after_seq=after_seq))

    @app.websocket(f"{API_PREFIX}/runs/{{run_id}}/events")
    async def event_websocket(websocket: WebSocket, run_id: str) -> None:
        handle = runtime.get_run(run_id)
        if handle is None:
            await websocket.close(code=4404, reason="run not found")
            return
        try:
            after_seq = int(websocket.query_params.get("after_seq", "0"))
            if after_seq < 0:
                raise ValueError
        except ValueError:
            await websocket.close(code=4400, reason="after_seq must be a non-negative integer")
            return

        await websocket.accept()
        try:
            async for event in handle.stream.subscribe(after_seq=after_seq):
                await websocket.send_json(event.model_dump(mode="json"))
        except WebSocketDisconnect:
            return

    return app


def _require_run(runtime: Runtime, run_id: str) -> RunHandle:
    handle = runtime.get_run(run_id)
    if handle is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="run not found")
    return handle


app = create_app()

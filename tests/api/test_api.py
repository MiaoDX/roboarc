from __future__ import annotations

from fastapi.testclient import TestClient

from roboarc.api import create_app
from roboarc.runtime import MockAdapter, RuntimeConfig


def capability_workflow(
    capability: str = "demo.instant_success",
    args: dict[str, object] | None = None,
) -> dict[str, object]:
    return {
        "workflow_schema_version": 1,
        "id": "api-test",
        "name": "API test",
        "workflow": {
            "id": "root",
            "type": "capability",
            "capability": {"id": capability, "version": 1},
            "args": args or {},
        },
    }


def test_health_and_discovery() -> None:
    with TestClient(create_app(MockAdapter())) as client:
        assert client.get("/api/v1/health").json()["status"] == "ok"
        assert client.get("/api/v1/profile").json()["id"] == "mock"
        capabilities = client.get("/api/v1/capabilities").json()
        assert {item["id"] for item in capabilities} >= {
            "demo.instant_success",
            "demo.cancellable_action",
        }


def test_validation_and_invalid_start_are_deterministic() -> None:
    payload = capability_workflow("missing.action")
    with TestClient(create_app(MockAdapter())) as client:
        report = client.post("/api/v1/workflows/validate", json=payload)
        assert report.status_code == 200
        assert report.json()["valid"] is False
        assert report.json()["issues"][0]["code"] == "capability_missing"

        start = client.post("/api/v1/runs", json=payload)
        assert start.status_code == 422
        assert start.json()["detail"]["valid"] is False


def test_compatibility_and_run_metadata_report_active_profile() -> None:
    payload = capability_workflow()
    with TestClient(create_app(MockAdapter())) as client:
        report = client.post("/api/v1/workflows/compatibility", json=payload).json()
        assert report["active_profile_id"] == "mock"
        assert report["compatible"] is True
        assert report["nodes"]["root"]["reason"] == "exact_capability_match"

        started = client.post("/api/v1/runs", json=payload).json()
        assert started["profile_id"] == "mock"
        with client.websocket_connect(
            f"/api/v1/runs/{started['run_id']}/events"
        ) as websocket:
            while websocket.receive_json()["type"] != "run.finished":
                pass
        snapshot = client.get(f"/api/v1/runs/{started['run_id']}").json()
        assert snapshot["profile_id"] == "mock"
        assert snapshot["result"]["profile_id"] == "mock"


def test_run_events_are_replayable_over_websocket_and_http() -> None:
    with TestClient(create_app(MockAdapter())) as client:
        response = client.post("/api/v1/runs", json=capability_workflow())
        assert response.status_code == 201
        run_id = response.json()["run_id"]

        events = []
        with client.websocket_connect(f"/api/v1/runs/{run_id}/events?after_seq=0") as websocket:
            while True:
                event = websocket.receive_json()
                events.append(event)
                if event["type"] == "run.finished":
                    break

        assert [event["seq"] for event in events] == list(range(1, len(events) + 1))
        assert events[0]["type"] == "run.started"
        assert events[-1]["data"]["state"] == "succeeded"

        snapshot = client.get(f"/api/v1/runs/{run_id}").json()
        assert snapshot["done"] is True
        assert snapshot["result"]["state"] == "succeeded"

        replay = client.get(f"/api/v1/runs/{run_id}/events?after_seq=1").json()
        assert replay[0]["seq"] == 2


def test_cancel_endpoint_waits_for_truthful_terminal_result() -> None:
    app = create_app(MockAdapter(), runtime_config=RuntimeConfig(cancel_grace_ms=100))
    payload = capability_workflow(
        "demo.cancellable_action",
        {"duration_ms": 500, "tick_ms": 5, "cleanup_ms": 5},
    )
    with TestClient(app) as client:
        run_id = client.post("/api/v1/runs", json=payload).json()["run_id"]
        cancel = client.post(f"/api/v1/runs/{run_id}/cancel")
        assert cancel.status_code == 200
        assert cancel.json()["accepted"] is True

        with client.websocket_connect(f"/api/v1/runs/{run_id}/events") as websocket:
            while True:
                event = websocket.receive_json()
                if event["type"] == "run.finished":
                    assert event["data"]["state"] == "canceled"
                    break

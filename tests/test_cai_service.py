from datetime import datetime

import pytest
from fastapi.testclient import TestClient

from caiengine.service import CAIService


@pytest.fixture()
def service_client():
    service = CAIService()
    with TestClient(service.app) as client:
        yield client


def test_context_ingestion_round_trip(service_client: TestClient):
    response = service_client.post(
        "/context",
        json={
            "payload": {"message": "hello"},
            "metadata": {"roles": ["user"]},
            "timestamp": datetime.utcnow().isoformat(),
        },
    )
    assert response.status_code == 200
    context_id = response.json()["id"]
    assert isinstance(context_id, str)

    fetch = service_client.get("/context")
    assert fetch.status_code == 200
    items = fetch.json()["items"]
    assert any(item["context"].get("message") == "hello" for item in items)


def test_context_ingestion_validation_error(service_client: TestClient):
    response = service_client.post("/context", json={})
    assert response.status_code == 422


def test_goal_suggestion_endpoint_returns_actions(service_client: TestClient):
    payload = {
        "history": [{"progress": 0.3}],
        "current_actions": [{"progress": 0.3}],
        "goal_state": {"progress": 1.0},
    }
    response = service_client.post("/suggest", json=payload)
    assert response.status_code == 200
    body = response.json()
    assert "suggestions" in body
    assert isinstance(body["suggestions"], list)

    usage = service_client.get("/usage")
    assert usage.status_code == 200
    usage_payload = usage.json()
    assert set(usage_payload.keys()) == {"prompt_tokens", "completion_tokens", "total_tokens"}


def test_rate_limiting_blocks_repeated_requests():
    service = CAIService(rate_limit_per_minute=1, rate_limit_window_seconds=60)
    with TestClient(service.app) as client:
        first = client.get("/usage")
        assert first.status_code == 200
        second = client.get("/usage")
        assert second.status_code == 429

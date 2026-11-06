"""Regression coverage for opt-in, synthetic CAIEngine showcase endpoints."""

import pytest
from fastapi.testclient import TestClient

from caiengine.experimental.workbench import (
    preview_agent_network,
    preview_goal_graph,
    preview_goal_loop,
)
from caiengine.service import CAIService


def test_goal_loop_uses_real_strategy_but_does_not_persist_history():
    request = {
        "goal_state": {"progress": 1.0},
        "history": [{"progress": 0.2}, {"progress": 0.4}],
        "current_actions": [{"progress": 0.4}],
    }
    first = preview_goal_loop(request)
    again = preview_goal_loop(request)
    assert first["suggestions"] == again["suggestions"]
    assert first["analysis"]["progress"]["gap"] == pytest.approx(0.6)
    assert first["debug"]["persistent"] is False


def test_goal_graph_reachable_subgraph_and_debug_counts():
    result = preview_goal_graph({
        "nodes": [
            {"id": "goal", "type": "GOAL", "label": "Prepare report"},
            {"id": "tool", "type": "TOOL", "label": "Generate report"},
            {"id": "unused", "type": "EXPERT", "label": "Not selected"},
        ],
        "edges": [{"source": "goal", "target": "tool", "label": "uses"}],
        "root_goal": "goal",
    })
    assert result["debug"]["nodes"] == 3
    assert result["debug"]["reachable_nodes"] == 2
    assert {node["id"] for node in result["reachable"]["nodes"]} == {"goal", "tool"}


def test_network_uses_canonical_registry_and_mock_dispatch():
    result = preview_agent_network({
        "nodes": [
            {"id": "actor-a", "capabilities": ["render"], "drivers": [], "apps": []},
            {"id": "actor-b", "capabilities": ["translate"], "drivers": [], "apps": []},
        ],
        "edges": [{"source": "actor-a", "target": "actor-b", "weight": 0.8}],
        "requirements": {"capabilities": ["render"]},
    })
    assert result["matching_nodes"] == ["actor-a"]
    assert result["dispatch"]["status"] == "dispatched"
    assert result["dispatch"]["target"] == "actor-a"
    assert result["transport"]["delivered_to"] == "demo:actor-a"
    assert result["debug"]["neighbors"]["actor-a"] == ["actor-b"]
    assert result["debug"]["real_dispatch"] is False


def test_experiment_rejects_unsafe_graph_and_nonfinite_weight():
    with pytest.raises(ValueError, match="existing nodes"):
        preview_goal_graph({
            "nodes": [{"id": "a", "label": "A", "type": "GOAL"}],
            "edges": [{"source": "a", "target": "foreign"}],
        })
    with pytest.raises(ValueError, match="weight"):
        preview_agent_network({
            "nodes": [{"id": "actor-a"}],
            "edges": [{"source": "actor-a", "target": "actor-a", "weight": float("inf")}],
        })


def test_experimental_http_routes_are_not_registered_by_default(monkeypatch):
    monkeypatch.delenv("CAI_EXPERIMENTS_ENABLED", raising=False)
    monkeypatch.delenv("CAI_EXPERIMENTS_TOKEN", raising=False)
    with TestClient(CAIService().app) as client:
        assert client.get("/experimental/capabilities").status_code == 404


def test_experimental_http_requires_token_and_is_limited_to_previews(monkeypatch):
    monkeypatch.setenv("CAI_EXPERIMENTS_ENABLED", "true")
    monkeypatch.setenv("CAI_EXPERIMENTS_TOKEN", "local-test-secret")
    with TestClient(CAIService().app) as client:
        assert client.get("/experimental/capabilities").status_code == 403
        headers = {"X-Cai-Experiments-Token": "local-test-secret"}
        capabilities = client.get("/experimental/capabilities", headers=headers)
        assert capabilities.status_code == 200
        assert capabilities.json()["live_dispatch"] is False

        response = client.post("/experimental/goal-loop/preview", headers=headers, json={
            "goal_state": {"progress": 10},
            "history": [{"progress": 2}],
            "current_actions": [{"progress": 2}],
        })
        assert response.status_code == 200
        assert response.json()["analysis"]["progress"]["gap"] == 8

        graph = client.post("/experimental/goal-graph/preview", headers=headers, json={
            "nodes": [{"id": "goal", "type": "GOAL", "label": "Goal"}], "edges": [],
        })
        assert graph.status_code == 200

        network = client.post("/experimental/network/preview", headers=headers, json={
            "nodes": [{"id": "worker", "capabilities": ["render"]}],
            "requirements": {"capabilities": ["render"]},
        })
        assert network.status_code == 200
        assert network.json()["dispatch"]["status"] == "dispatched"

        oversized = client.post("/experimental/goal-loop/preview", headers=headers,
                                content='{"padding":"' + "a" * 33000 + '"}')
        assert oversized.status_code == 413

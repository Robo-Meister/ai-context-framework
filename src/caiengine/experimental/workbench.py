"""Bounded, isolated experiments using canonical CAIEngine building blocks.

These helpers never persist contexts, update registries, or dispatch to real nodes.
They intentionally create new in-memory instances for every preview request.
"""

from __future__ import annotations

import math
from typing import Any

from caiengine.core.goal_feedback_loop import GoalDrivenFeedbackLoop
from caiengine.core.goal_strategies import SimpleGoalFeedbackStrategy
from caiengine.network.agent_network import AgentNetwork
from caiengine.network.capability_registry import CapabilityRegistry
from caiengine.network.dispatcher import MeshDispatcher
from caiengine.network.node_manager import NodeManager
from caiengine.network.node_registry import NodeRegistry
from caiengine.network.simple_network import SimpleNetworkMock
from caiengine.orchestration.goal_graph import GoalGraph, NodeType


def _list(payload: dict[str, Any], key: str, maximum: int) -> list[Any]:
    value = payload.get(key, [])
    if not isinstance(value, list) or len(value) > maximum:
        raise ValueError(f"{key} must be a list of at most {maximum} items")
    return value


def _name(value: Any, label: str) -> str:
    if not isinstance(value, str) or not value or len(value) > 100:
        raise ValueError(f"{label} must be a non-empty string (max 100 characters)")
    return value


def _strings(value: Any, label: str, maximum: int = 12) -> list[str]:
    if not isinstance(value, list) or len(value) > maximum:
        raise ValueError(f"{label} must be a list of at most {maximum} strings")
    return [_name(item, label) for item in value]


def preview_goal_loop(payload: dict[str, Any]) -> dict[str, Any]:
    """Run the actual feedback strategy on a fresh, non-persisted loop."""
    goal_state = payload.get("goal_state", {})
    if not isinstance(goal_state, dict) or len(goal_state) > 12:
        raise ValueError("goal_state must be an object with at most 12 metrics")
    for name, target in goal_state.items():
        _name(name, "goal metric")
        if not isinstance(target, (int, float)) or isinstance(target, bool) or not math.isfinite(target):
            raise ValueError("goal_state targets must be finite numbers")

    history = _list(payload, "history", 30)
    actions = _list(payload, "current_actions", 20)
    if any(not isinstance(item, dict) for item in history + actions):
        raise ValueError("history and current_actions must contain objects")

    loop = GoalDrivenFeedbackLoop(SimpleGoalFeedbackStrategy(), goal_state=goal_state)
    suggestions = loop.suggest(history, actions)
    return {
        "mode": "isolated_preview",
        "suggestions": suggestions,
        "analysis": loop.last_analysis,
        "history_size": len(loop.history),
        "debug": {
            "engine": "GoalDrivenFeedbackLoop",
            "strategy": "SimpleGoalFeedbackStrategy",
            "persistent": False,
            "supplied_actions": len(actions),
            "supplied_history": len(history),
        },
    }


def preview_goal_graph(payload: dict[str, Any]) -> dict[str, Any]:
    """Validate, construct and explore an actual GoalGraph."""
    nodes = _list(payload, "nodes", 60)
    edges = _list(payload, "edges", 120)
    ids: set[str] = set()
    for node in nodes:
        if not isinstance(node, dict):
            raise ValueError("nodes must be objects")
        node_id = _name(node.get("id"), "node.id")
        if node_id in ids:
            raise ValueError("duplicate goal graph node id")
        ids.add(node_id)
        if node.get("type") not in {item.value for item in NodeType}:
            raise ValueError("invalid goal graph node type")
        _name(node.get("label"), "node.label")
        if not isinstance(node.get("metadata", {}), dict):
            raise ValueError("node.metadata must be an object")
    for edge in edges:
        if not isinstance(edge, dict) or edge.get("source") not in ids or edge.get("target") not in ids:
            raise ValueError("edges must reference existing nodes")
        if not isinstance(edge.get("metadata", {}), dict):
            raise ValueError("edge.metadata must be an object")
    graph = GoalGraph.from_dict({"nodes": nodes, "edges": edges})
    root = payload.get("root_goal")
    if root is not None:
        root = _name(root, "root_goal")
        if root not in ids:
            raise ValueError("root_goal is not a node")
    elif nodes:
        root = next((node["id"] for node in nodes if node["type"] == "GOAL"), nodes[0]["id"])
    selected = graph.subgraph_for(root) if root else graph
    return {
        "mode": "isolated_preview",
        "graph": graph.to_dict(),
        "reachable": selected.to_dict(),
        "debug": {
            "engine": "GoalGraph",
            "nodes": len(nodes),
            "edges": len(edges),
            "root_goal": root,
            "reachable_nodes": len(selected.nodes),
            "reachable_edges": len(selected.edges),
            "persistent": False,
        },
    }


class _EphemeralRedisHash:
    """The minimum Redis hash protocol required by canonical NodeRegistry."""

    def __init__(self) -> None:
        self._hashes: dict[str, dict[str, str]] = {}

    def hset(self, name: str, key: str, value: str) -> int:
        self._hashes.setdefault(name, {})[key] = value
        return 1

    def hget(self, name: str, key: str) -> str | None:
        return self._hashes.get(name, {}).get(key)

    def hgetall(self, name: str) -> dict[str, str]:
        return dict(self._hashes.get(name, {}))

    def hdel(self, name: str, key: str) -> int:
        return int(self._hashes.get(name, {}).pop(key, None) is not None)


def preview_agent_network(payload: dict[str, Any]) -> dict[str, Any]:
    """Explore an in-memory graph, capability match and safe mock dispatch."""
    nodes = _list(payload, "nodes", 30)
    edges = _list(payload, "edges", 80)
    requirements = payload.get("requirements", {})
    if not isinstance(requirements, dict):
        raise ValueError("requirements must be an object")
    required = {
        field: _strings(requirements.get(field, []), "requirements." + field)
        for field in ("capabilities", "drivers", "apps")
    }

    graph = AgentNetwork()
    registry = CapabilityRegistry(NodeManager(NodeRegistry(_EphemeralRedisHash())))
    known: set[str] = set()
    public_nodes = []
    for node in nodes:
        if not isinstance(node, dict):
            raise ValueError("nodes must be objects")
        node_id = _name(node.get("id"), "node.id")
        if node_id in known:
            raise ValueError("duplicate network node id")
        known.add(node_id)
        capabilities = _strings(node.get("capabilities", []), "node.capabilities")
        drivers = _strings(node.get("drivers", []), "node.drivers")
        apps = _strings(node.get("apps", []), "node.apps")
        graph.add_agent(node_id)
        # Use an in-memory address, never a URL or external recipient.
        registry.register(node_id, "demo:" + node_id, capabilities=capabilities, drivers=drivers, apps=apps)
        public_nodes.append({"id": node_id, "capabilities": capabilities, "drivers": drivers, "apps": apps})

    public_edges = []
    for edge in edges:
        if not isinstance(edge, dict) or edge.get("source") not in known or edge.get("target") not in known:
            raise ValueError("network edges must connect existing nodes")
        weight = edge.get("weight", 1.0)
        if not isinstance(weight, (int, float)) or isinstance(weight, bool) or not math.isfinite(weight) or weight < 0:
            raise ValueError("edge.weight must be a non-negative finite number")
        graph.connect(edge["source"], edge["target"], float(weight))
        public_edges.append({"source": edge["source"], "target": edge["target"], "weight": float(weight)})

    eligible = registry.find(**required)
    transport = SimpleNetworkMock(max_queue=32)
    outcome = MeshDispatcher(registry, transport, retry_attempts=1, retry_backoff=0).dispatch(
        {"id": "workbench-preview", "kind": "synthetic_preview"}, requirements=required
    )
    delivered = transport.receive() if outcome.dispatched else None
    return {
        "mode": "isolated_preview",
        "graph": {"nodes": public_nodes, "edges": public_edges},
        "matching_nodes": sorted(eligible),
        "dispatch": {
            "status": outcome.status,
            "target": outcome.target,
            "attempted_targets": outcome.attempted_targets,
            "missing_drivers": outcome.missing_drivers,
            "reason": outcome.reason,
        },
        "transport": {
            "delivered_to": delivered[0] if delivered else None,
            "metrics": transport.stats(),
        },
        "debug": {
            "engines": ["AgentNetwork", "NodeManager", "CapabilityRegistry", "MeshDispatcher", "SimpleNetworkMock"],
            "neighbors": {node_id: sorted(graph.neighbors(node_id)) for node_id in known},
            "persistent": False,
            "real_dispatch": False,
        },
    }

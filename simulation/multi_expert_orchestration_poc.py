"""Runnable PoC for budgeted multi-expert orchestration in CAIEngine.

Run with:
    python simulation/multi_expert_orchestration_poc.py
"""

from __future__ import annotations

import json
from dataclasses import dataclass
from pprint import pprint
from typing import Any

from caiengine.orchestration.goal_graph import Edge, GoalGraph, Node, NodeType
from caiengine.orchestration import EpsilonGreedyRoutingPolicy, ExpertRegistry, ExpertResult, ExpertRouter
from caiengine.pipelines.orchestrated_pipeline import OrchestratedPipeline
from caiengine.providers.memory_context_provider import MemoryContextProvider


@dataclass
class DemoExpert:
    """Small deterministic expert used by this PoC."""

    expert_id: str
    confidence: float
    specialization: str

    def run(self, input: dict[str, Any], context: dict[str, Any]) -> ExpertResult:
        packet = context.get("context_packet", {})
        return ExpertResult(
            output={
                "expert": self.expert_id,
                "specialization": self.specialization,
                "selected_layers": sorted(packet.keys()),
                "request_category": input.get("category"),
            },
            confidence=self.confidence,
            debug={"expert": self.expert_id},
            used_layers=list(packet.keys()),
            model_id=self.expert_id,
            model_version="poc",
        )


def _build_provider() -> MemoryContextProvider:
    provider = MemoryContextProvider()
    provider.ingest_context(
        payload={
            "ticket": "A-17",
            "summary": "customer asks for fast refund",
            "sentiment": "negative",
            "pantry": ["rice", "eggs", "spinach"],
            "country": "PL",
            "weekday": "Wednesday",
        },
        metadata={"roles": ["support"], "content": "support case + pantry hints"},
    )
    provider.ingest_context(
        payload={"account": "A-17", "amount": 1920, "currency": "USD", "calendar": "Wednesday"},
        metadata={"roles": ["finance"], "content": "billing facts + calendar hint"},
    )
    return provider


def _build_registry() -> ExpertRegistry:
    registry = ExpertRegistry()
    registry.register(
        DemoExpert("support_expert", confidence=0.82, specialization="customer_support"),
        capabilities={
            "category": "support",
            "scope": "customer",
            "tags": ["text", "urgent"],
            "layers": ["retrieved.items"],
        },
    )
    registry.register(
        DemoExpert("finance_expert", confidence=0.93, specialization="billing"),
        capabilities={
            "category": "finance",
            "scope": "customer",
            "tags": ["numeric"],
            "layers": ["retrieved.items", "request"],
        },
    )
    registry.register(
        DemoExpert("generalist_expert", confidence=0.55, specialization="fallback"),
        capabilities={
            "scope": "customer",
            "tags": ["text"],
            "layers": ["retrieved.items"],
        },
    )
    return registry


def criterion_1_metadata_changes_expert_selection() -> None:
    print("\n=== Criterion 1: request metadata changes selected experts ===")

    pipeline = OrchestratedPipeline(context_provider=_build_provider(), registry=_build_registry())

    support_request = {
        "category": "support",
        "scope": "customer",
        "tags": ["text", "urgent"],
        "required_layers": ["retrieved.items"],
        "optional_layers": ["goal", "request"],
    }
    finance_request = {
        "category": "finance",
        "scope": "customer",
        "tags": ["numeric"],
        "required_layers": ["retrieved.items"],
        "optional_layers": ["goal", "request"],
    }

    support_result = pipeline.run(support_request)
    finance_result = pipeline.run(finance_request)

    print("Support request chosen experts:", support_result["telemetry"]["chosen_experts"])
    print("Finance request chosen experts:", finance_result["telemetry"]["chosen_experts"])


def criterion_2_budget_changes_context_packet_layers() -> None:
    print("\n=== Criterion 2: budget changes selected context layers ===")

    pipeline = OrchestratedPipeline(context_provider=_build_provider(), registry=_build_registry())
    request = {
        "category": "support",
        "scope": "customer",
        "tags": ["text", "urgent"],
        "required_layers": ["retrieved.items"],
        "optional_layers": [
            "goal.meal",
            "goal.meal.constraints",
            "retrieved.items.pantry",
            "retrieved.items.calendar",
            "request",
        ],
    }

    tight_budget = {
        "required_layers": ["retrieved.items"],
        "optional_layers": ["goal.meal"],
        "budget": {"max_layers": 2, "max_chars": 220},
    }
    roomy_budget = {
        "required_layers": ["retrieved.items"],
        "optional_layers": [
            "goal.meal",
            "goal.meal.constraints",
            "retrieved.items.pantry",
            "retrieved.items.calendar",
            "request",
        ],
        "budget": {"max_layers": 6, "max_chars": 5_000},
    }

    tight = pipeline.run(request=request, goal_context=tight_budget)
    roomy = pipeline.run(request=request, goal_context=roomy_budget)

    print("Tight budget layers:", tight["telemetry"]["selected_layers"])
    print("Roomy budget layers:", roomy["telemetry"]["selected_layers"])


def criterion_4_goal_graph_json_round_trip() -> None:
    print("\n=== Criterion 4: workflow graph can be serialized as JSON ===")

    graph = GoalGraph()
    graph.add_node(
        Node(
            id="goal.meal",
            type=NodeType.GOAL,
            label="Generate Wednesday meal idea",
            metadata={"country": "PL"},
        )
    )
    graph.add_node(
        Node(
            id="goal.meal.constraints",
            type=NodeType.CONTEXT_LAYER,
            label="Meal constraints",
            metadata={"max_budget_pln": 40, "weekday": "Wednesday"},
        )
    )
    graph.add_node(
        Node(
            id="expert.meal_planner",
            type=NodeType.EXPERT,
            label="Meal planner expert",
            metadata={"uses_layers": ["goal.meal", "goal.meal.constraints", "retrieved.items"]},
        )
    )
    graph.add_edge(Edge("goal.meal", "goal.meal.constraints", label="constrained_by"))
    graph.add_edge(Edge("goal.meal.constraints", "expert.meal_planner", label="executed_by"))

    payload = graph.to_dict()
    rehydrated = GoalGraph.from_dict(payload)

    print("Serialized graph JSON:")
    print(json.dumps(payload, indent=2))
    print("Round-trip stable:", rehydrated.to_dict() == payload)


def criterion_3_adaptive_routing_improves_with_feedback() -> None:
    print("\n=== Criterion 3: adaptive policy improves with reward feedback ===")

    registry = ExpertRegistry()
    registry.register(
        DemoExpert("slow_but_safe", confidence=0.50, specialization="baseline"),
        capabilities={"category": "triage", "tags": ["safe"], "layers": ["retrieved.items"]},
    )
    registry.register(
        DemoExpert("fast_and_good", confidence=0.51, specialization="optimized"),
        capabilities={"category": "triage", "tags": ["safe"], "layers": ["retrieved.items"]},
    )

    policy = EpsilonGreedyRoutingPolicy(epsilon=0.0, random_seed=11)
    router = ExpertRouter(registry=registry, policy=policy)
    pipeline = OrchestratedPipeline(context_provider=_build_provider(), registry=registry, router=router)

    request = {
        "goal": "customer_satisfaction",
        "task": "triage",
        "category": "triage",
        "tags": ["safe"],
        "required_layers": ["retrieved.items"],
        "optional_layers": [],
    }

    before = pipeline.run(request=request)
    print("Before rewards selected expert:", before["response"]["selected_experts"])

    for _ in range(25):
        policy.record_outcome("slow_but_safe", reward=0.2, context_meta={"goal": "customer_satisfaction", "task": "triage"})
        policy.record_outcome("fast_and_good", reward=1.0, context_meta={"goal": "customer_satisfaction", "task": "triage"})

    after = pipeline.run(request=request)
    print("After rewards selected expert:", after["response"]["selected_experts"])
    pprint(after["response"]["output"])


if __name__ == "__main__":
    criterion_1_metadata_changes_expert_selection()
    criterion_2_budget_changes_context_packet_layers()
    criterion_3_adaptive_routing_improves_with_feedback()
    criterion_4_goal_graph_json_round_trip()

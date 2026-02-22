from __future__ import annotations

import sys
from dataclasses import dataclass
from datetime import datetime, timedelta
from pathlib import Path
from typing import Any

REPO_ROOT = Path(__file__).resolve().parents[1]
SRC_ROOT = REPO_ROOT / "src"
if str(SRC_ROOT) not in sys.path:
    sys.path.insert(0, str(SRC_ROOT))

from caiengine.orchestration import ExpertRegistry, ExpertResult, ExpertRouter
from caiengine.orchestration.bandit_policy import EpsilonGreedyRoutingPolicy
from caiengine.pipelines.orchestrated_pipeline import OrchestratedPipeline
from caiengine.providers.memory_context_provider import MemoryContextProvider


@dataclass
class StaticExpert:
    expert_id: str
    confidence: float
    label: str

    def run(self, input: dict[str, Any], context: dict[str, Any]) -> ExpertResult:
        packet = context.get("context_packet", {})
        return ExpertResult(
            output={
                "expert": self.expert_id,
                "label": self.label,
                "input": input,
                "packet_keys": sorted(packet.keys()),
            },
            confidence=float(self.confidence),
            debug={"expert": self.expert_id, "label": self.label},
            used_layers=sorted(packet.keys()),
            model_id=self.expert_id,
            model_version="1",
        )


def build_provider() -> MemoryContextProvider:
    provider = MemoryContextProvider()
    now = datetime.utcnow()

    provider.ingest_context(
        payload={"calendar": {"day": "Wednesday", "country": "PL"}},
        timestamp=now,
        metadata={"roles": ["user"], "content": "User locale/time context"},
    )
    provider.ingest_context(
        payload={"preferences": {"diet": "omnivore", "spice": "medium"}},
        timestamp=now + timedelta(seconds=1),
        metadata={"roles": ["user"], "content": "User preferences"},
    )
    provider.ingest_context(
        payload={"pantry": {"eggs": 6, "rice": "1kg", "onion": 2}},
        timestamp=now + timedelta(seconds=2),
        metadata={"roles": ["user"], "content": "Pantry snapshot"},
    )
    return provider


def build_registry() -> ExpertRegistry:
    registry = ExpertRegistry()

    # A "generalist" expert that works with minimal context
    registry.register(
        StaticExpert("expert_general", 0.55, "General meal planner"),
        capabilities={
            "category": "meal_planning",
            "scope": "PL",
            "tags": ["meal", "plan"],
            "layers": ["retrieved.items"],
        },
    )

    # A "specialist" that expects extra goal + request context (simulating deeper context)
    registry.register(
        StaticExpert("expert_specialist", 0.85, "Context-heavy specialist"),
        capabilities={
            "category": "meal_planning",
            "scope": "PL",
            "tags": ["meal", "plan"],
            "layers": ["retrieved.items", "goal", "request"],
        },
    )

    return registry


def run_rule_based_demo(provider: MemoryContextProvider, registry: ExpertRegistry) -> None:
    pipeline = OrchestratedPipeline(context_provider=provider, registry=registry)

    request = {
        "category": "meal_planning",
        "scope": "PL",
        "tags": ["meal", "plan"],
        # layers and budget for packet compilation
        "required_layers": ["retrieved.items"],
        "optional_layers": ["goal", "request"],
        "budget": {"max_layers": 2, "max_chars": 10_000},
    }

    goal_context = {
        "goal_id": "meal_pl_pl_wed",
        "roles": ["user"],
        "scope": "PL",
        "goal": {"meal_day": "Wednesday", "region": "PL"},
    }

    result = pipeline.run(request=request, goal_context=goal_context)
    print("\n=== Rule-based routing demo ===")
    print("Selected layers:", result["telemetry"]["selected_layers"])
    print("Omitted layers:", result["context_packet"].omitted_layers)
    print("Chosen experts:", result["telemetry"]["chosen_experts"])
    print("Confidence scores:", result["telemetry"]["confidences"])
    print("Final output:", result["response"]["output"])


def run_bandit_demo(provider: MemoryContextProvider, registry: ExpertRegistry) -> None:
    # Use epsilon-greedy policy to choose ONE expert (instead of all rule-based matches).
    policy = EpsilonGreedyRoutingPolicy(epsilon=0.2, database=":memory:", random_seed=7)
    router = ExpertRouter(registry=registry, policy=policy)

    pipeline = OrchestratedPipeline(context_provider=provider, registry=registry, router=router)

    request = {
        "category": "meal_planning",
        "scope": "PL",
        "tags": ["meal", "plan"],
        "required_layers": ["retrieved.items"],
        "optional_layers": ["goal", "request"],
        "budget": {"max_layers": 3, "max_chars": 10_000},
        "goal_id": "meal_pl_pl_wed",
        "task_id": "choose_menu",
    }

    goal_context = {
        "goal_id": "meal_pl_pl_wed",
        "task_id": "choose_menu",
        "scope": "PL",
        "goal": {"meal_day": "Wednesday", "region": "PL"},
    }

    print("\n=== Bandit routing demo (training) ===")
    for i in range(20):
        result = pipeline.run(request=request, goal_context=goal_context)
        chosen = result["telemetry"]["chosen_experts"][0] if result["telemetry"]["chosen_experts"] else None

        # Example reward: specialist is "better" in this toy demo.
        reward = 1.0 if chosen == "expert_specialist" else 0.0
        if chosen:
            policy.record_outcome(chosen, reward, context_meta={"goal_id": "meal_pl_pl_wed", "task_id": "choose_menu"})

        print(f"iter={i} chosen={chosen} reward={reward}")

    print("\nRe-run after training:")
    for i in range(3):
        result = pipeline.run(request=request, goal_context=goal_context)
        chosen = result["telemetry"]["chosen_experts"][0] if result["telemetry"]["chosen_experts"] else None
        print(f"iter={i} chosen={chosen}")


def main() -> None:
    provider = build_provider()
    registry = build_registry()
    run_rule_based_demo(provider, registry)
    run_bandit_demo(provider, registry)


if __name__ == "__main__":
    main()

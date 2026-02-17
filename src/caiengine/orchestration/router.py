"""Expert router tying registry, policies and aggregators together."""

from __future__ import annotations

from typing import Any

from .aggregators import Aggregator, SimpleConfidenceAggregator
from .expert_registry import ExpertRegistry
from .expert_types import ExpertResult
from .policies import RoutingPolicy, RuleBasedRoutingPolicy


class ExpertRouter:
    """Route requests to experts and aggregate their responses."""

    def __init__(
        self,
        registry: ExpertRegistry,
        policy: RoutingPolicy | None = None,
        aggregator: Aggregator | None = None,
    ) -> None:
        self.registry = registry
        self.policy = policy or RuleBasedRoutingPolicy()
        self.aggregator = aggregator or SimpleConfidenceAggregator()

    def route(
        self,
        request: dict[str, Any],
        goal_context: dict[str, Any] | None = None,
        context_layers: list[str] | None = None,
    ) -> dict[str, Any]:
        goal_context = goal_context or {}
        context_layers = context_layers or []

        selected_ids = self.policy.select(
            self.registry.list_experts(),
            request,
            goal_context,
            context_layers,
        )

        results: list[ExpertResult] = []
        for expert_id in selected_ids:
            expert = self.registry.get(expert_id)
            if expert is None:
                continue
            results.append(expert.run(request, goal_context))

        aggregated = self.aggregator.aggregate(results)
        aggregated["selected_experts"] = selected_ids
        return aggregated

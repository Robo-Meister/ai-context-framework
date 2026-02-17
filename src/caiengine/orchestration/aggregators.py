"""Result aggregation strategies for orchestration experts."""

from __future__ import annotations

from typing import Any, Protocol

from .expert_types import ExpertResult


class Aggregator(Protocol):
    """Combine multiple expert results into a final response."""

    def aggregate(self, results: list[ExpertResult]) -> dict[str, Any]:
        """Aggregate expert results into a single payload."""


class SimpleConfidenceAggregator:
    """Choose the highest confidence result and preserve peer diagnostics."""

    def aggregate(self, results: list[ExpertResult]) -> dict[str, Any]:
        if not results:
            return {
                "output": None,
                "confidence": 0.0,
                "debug": {"all_results": []},
                "used_layers": [],
                "model_id": "",
                "model_version": "",
            }

        best = max(results, key=lambda result: result.confidence)
        return {
            "output": best.output,
            "confidence": best.confidence,
            "debug": {
                "selected": best.debug,
                "all_results": [
                    {
                        "confidence": result.confidence,
                        "debug": result.debug,
                        "model_id": result.model_id,
                        "model_version": result.model_version,
                    }
                    for result in results
                ],
            },
            "used_layers": best.used_layers,
            "model_id": best.model_id,
            "model_version": best.model_version,
        }

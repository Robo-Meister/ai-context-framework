"""Context packet compilation helpers for orchestration routing."""

from __future__ import annotations

from dataclasses import dataclass
import json
from typing import Any


@dataclass(slots=True)
class ContextPacket:
    """Compiled context subset selected under a fixed budget."""

    selected_layers: dict[str, Any]
    omitted_layers: list[str]
    budget: dict[str, Any]
    stats: dict[str, int]


class ContextPacketCompiler:
    """Compile required and optional layered context into a budgeted packet."""

    def compile(
        self,
        context: dict[str, Any],
        required: list[str],
        optional: list[str],
        budget: dict[str, Any],
    ) -> ContextPacket:
        selected: dict[str, Any] = {}
        omitted: list[str] = []

        selected_size = 0
        max_layers = int(budget.get("max_layers", 10**9))
        max_chars = int(budget.get("max_chars", 10**9))

        def add_layer(path: str, value: Any) -> None:
            nonlocal selected_size
            selected[path] = value
            selected_size += self._estimate_size(value)

        # Required layers are always included when available.
        for path in required:
            found, value = self._get_layer(context, path)
            if found:
                add_layer(path, value)
            else:
                omitted.append(path)

        # Optional layers can be dropped by budget constraints.
        ranked_optional = self._rank_optional_layers(optional, budget)
        for path in ranked_optional:
            if path in selected:
                continue
            found, value = self._get_layer(context, path)
            if not found:
                omitted.append(path)
                continue

            value_size = self._estimate_size(value)
            next_layer_count = len(selected) + 1
            next_char_count = selected_size + value_size
            if next_layer_count > max_layers or next_char_count > max_chars:
                omitted.append(path)
                continue

            add_layer(path, value)

        total_layers = len(required) + len(optional)
        stats = {
            "selected_count": len(selected),
            "omitted_count": len(omitted),
            "total_candidates": total_layers,
            "selected_size": selected_size,
            "max_layers": max_layers,
            "max_chars": max_chars,
        }

        return ContextPacket(
            selected_layers=selected,
            omitted_layers=omitted,
            budget=dict(budget),
            stats=stats,
        )

    def _rank_optional_layers(self, optional: list[str], budget: dict[str, Any]) -> list[str]:
        weights = self._collect_weights(budget)
        scored = []
        for idx, layer in enumerate(optional):
            scored.append((weights.get(layer, 0.0), -idx, layer))
        scored.sort(reverse=True)
        return [layer for _, _, layer in scored]

    def _collect_weights(self, budget: dict[str, Any]) -> dict[str, float]:
        weights: dict[str, float] = {}

        trust_module = budget.get("trust_module")
        if trust_module is not None and hasattr(trust_module, "weights"):
            raw = getattr(trust_module, "weights")
            if isinstance(raw, dict):
                for key, value in self._flatten_weights(raw).items():
                    weights[key] = float(value)

        context_provider = budget.get("context_provider")
        if context_provider is not None:
            raw = getattr(context_provider, "context_weights", None)
            if isinstance(raw, dict):
                for key, value in self._flatten_weights(raw).items():
                    weights.setdefault(key, float(value))

        explicit = budget.get("weights")
        if isinstance(explicit, dict):
            for key, value in explicit.items():
                weights[key] = float(value)

        return weights

    def _flatten_weights(self, source: dict[str, Any], prefix: str = "") -> dict[str, float]:
        flat: dict[str, float] = {}
        for key, value in source.items():
            full_key = f"{prefix}.{key}" if prefix else key
            if isinstance(value, dict):
                flat.update(self._flatten_weights(value, prefix=full_key))
            else:
                flat[full_key] = float(value)
        return flat

    def _estimate_size(self, value: Any) -> int:
        try:
            return len(json.dumps(value, sort_keys=True, default=str))
        except TypeError:
            return len(str(value))

    def _get_layer(self, context: dict[str, Any], path: str) -> tuple[bool, Any]:
        if not path:
            return False, None

        current: Any = context
        for part in path.split("."):
            if not isinstance(current, dict) or part not in current:
                return False, None
            current = current[part]
        return True, current

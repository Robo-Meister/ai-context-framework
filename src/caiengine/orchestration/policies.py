"""Routing policies used by orchestration router."""

from __future__ import annotations

from typing import Any, Protocol

from .expert_registry import RegisteredExpert


class RoutingPolicy(Protocol):
    """Policy interface that selects expert ids for a request."""

    def select(
        self,
        experts: list[RegisteredExpert],
        request: dict[str, Any],
        goal_context: dict[str, Any],
        context_layers: list[str],
    ) -> list[str]:
        """Return selected expert ids in deterministic order."""


class RuleBasedRoutingPolicy:
    """Rule-based selector matching category/scope/tags and context layers."""

    def select(
        self,
        experts: list[RegisteredExpert],
        request: dict[str, Any],
        goal_context: dict[str, Any],
        context_layers: list[str],
    ) -> list[str]:
        request_category = request.get("category") or goal_context.get("category")
        request_scope = request.get("scope") or goal_context.get("scope")
        request_tags = set(request.get("tags") or [])
        available_layers = set(context_layers)

        selected: list[str] = []
        for entry in experts:
            capabilities = entry.capabilities

            category = capabilities.get("category")
            if category is not None and request_category is not None and category != request_category:
                continue

            scope = capabilities.get("scope")
            if scope is not None and request_scope is not None and scope != request_scope:
                continue

            tags = set(capabilities.get("tags") or [])
            if request_tags and not request_tags.issubset(tags):
                continue

            required_layers = set(capabilities.get("layers") or [])
            if required_layers and not required_layers.issubset(available_layers):
                continue

            selected.append(entry.expert_id)

        return selected

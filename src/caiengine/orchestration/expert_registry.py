"""Registry for orchestration experts."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any

from .expert_types import Expert


@dataclass(frozen=True, slots=True)
class RegisteredExpert:
    """Expert entry with metadata used for capability matching."""

    expert_id: str
    expert: Expert
    capabilities: dict[str, Any]


class ExpertRegistry:
    """Simple in-memory registry for expert instances."""

    def __init__(self) -> None:
        self._entries: dict[str, RegisteredExpert] = {}

    def register(
        self,
        expert: Expert,
        capabilities: dict[str, Any] | None = None,
        expert_id: str | None = None,
    ) -> str:
        """Register an expert and return its identifier."""
        capabilities = capabilities or {}
        resolved_id = expert_id or getattr(expert, "expert_id", expert.__class__.__name__)
        self._entries[resolved_id] = RegisteredExpert(
            expert_id=resolved_id,
            expert=expert,
            capabilities=dict(capabilities),
        )
        return resolved_id

    def list_experts(self) -> list[RegisteredExpert]:
        """Return all registered experts."""
        return list(self._entries.values())

    def get(self, expert_id: str) -> Expert | None:
        """Get an expert by identifier."""
        entry = self._entries.get(expert_id)
        return None if entry is None else entry.expert

    def match(self, criteria: dict[str, Any]) -> list[RegisteredExpert]:
        """Return experts whose capabilities satisfy task/tag/layer criteria."""
        required_task = criteria.get("task")
        required_tags = set(criteria.get("tags") or [])
        required_layers = set(criteria.get("layers") or [])

        matches: list[RegisteredExpert] = []
        for entry in self._entries.values():
            capabilities = entry.capabilities
            if required_task is not None and capabilities.get("task") != required_task:
                continue

            cap_tags = set(capabilities.get("tags") or [])
            if required_tags and not required_tags.issubset(cap_tags):
                continue

            cap_layers = set(capabilities.get("layers") or [])
            if required_layers and not required_layers.issubset(cap_layers):
                continue

            matches.append(entry)

        return matches

"""Types for orchestration experts."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Protocol, runtime_checkable


@dataclass(slots=True)
class ExpertResult:
    """Standard result payload returned by orchestration experts."""

    output: Any
    confidence: float = 0.0
    cost_ms: float = 0.0
    debug: dict[str, Any] = field(default_factory=dict)
    used_layers: list[str] = field(default_factory=list)
    model_id: str = ""
    model_version: str = ""


@runtime_checkable
class Expert(Protocol):
    """Contract for pluggable experts used by orchestration logic."""

    def run(self, input: dict[str, Any], context: dict[str, Any]) -> ExpertResult:
        """Execute an expert call with input payload and shared context."""

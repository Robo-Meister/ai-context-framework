from __future__ import annotations

from dataclasses import dataclass, field, asdict
from typing import Any, Dict, List, Optional
import json


@dataclass
class ContextLayer:
    """Represents a single layer of context information."""

    layer_id: str
    data: Dict[str, Any]
    weight: float = 1.0
    trust: float = 1.0
    scope: Optional[str] = None
    parent: Optional[str] = None


@dataclass
class ContextCategory:
    """Grouping for related context layers."""

    name: str
    layers: List[ContextLayer] = field(default_factory=list)


@dataclass
class Event:
    """Event record carrying payload and related context."""

    event_id: str
    timestamp: float
    source: str
    payload: Dict[str, Any]
    contexts: Dict[str, ContextCategory] = field(default_factory=dict)

    def to_dict(self) -> Dict[str, Any]:
        """Convert the event to a JSON-serializable dictionary."""
        return asdict(self)

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "Event":
        """Recreate an :class:`Event` from a dictionary."""
        contexts: Dict[str, ContextCategory] = {}
        for name, cat in data.get("contexts", {}).items():
            layers = [ContextLayer(**layer) for layer in cat.get("layers", [])]
            contexts[name] = ContextCategory(name=name, layers=layers)
        return cls(
            event_id=data["event_id"],
            timestamp=data["timestamp"],
            source=data["source"],
            payload=data.get("payload", {}),
            contexts=contexts,
        )

    def save(self, path: str) -> None:
        """Persist the event as JSON to ``path``."""
        with open(path, "w", encoding="utf-8") as f:
            json.dump(self.to_dict(), f, indent=2)

    @classmethod
    def load(cls, path: str) -> "Event":
        """Load an event from JSON stored at ``path``."""
        with open(path, "r", encoding="utf-8") as f:
            data = json.load(f)
        return cls.from_dict(data)

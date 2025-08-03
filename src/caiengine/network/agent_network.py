"""Simple in-memory graph to manage relationships between agents.

This provides a lightweight adjacency mapping that tracks bidirectional
relationships and optional weights between agents. It avoids introducing
external dependencies while offering enough features for unit tests and
simple orchestration logic.
"""
from __future__ import annotations

from typing import Dict, Iterable, Optional


class AgentNetwork:
    """Maintain an undirected weighted graph of agents."""

    def __init__(self) -> None:
        # Mapping from agent -> {neighbor: weight}
        self._edges: Dict[str, Dict[str, float]] = {}

    def add_agent(self, agent_id: str) -> None:
        """Ensure an agent exists in the graph."""
        self._edges.setdefault(agent_id, {})

    def connect(self, agent_a: str, agent_b: str, weight: float = 1.0) -> None:
        """Create a bidirectional relationship between two agents."""
        self.add_agent(agent_a)
        self.add_agent(agent_b)
        self._edges[agent_a][agent_b] = weight
        self._edges[agent_b][agent_a] = weight

    def disconnect(self, agent_a: str, agent_b: str) -> None:
        """Remove the relationship between two agents if present."""
        self._edges.get(agent_a, {}).pop(agent_b, None)
        self._edges.get(agent_b, {}).pop(agent_a, None)

    def relationship(self, agent_a: str, agent_b: str) -> Optional[float]:
        """Return the weight of the relationship or ``None`` if absent."""
        return self._edges.get(agent_a, {}).get(agent_b)

    def neighbors(self, agent_id: str) -> Iterable[str]:
        """Iterate over all directly connected agents."""
        return self._edges.get(agent_id, {}).keys()

    def remove_agent(self, agent_id: str) -> None:
        """Remove an agent and all of its relationships."""
        self._edges.pop(agent_id, None)
        for edges in self._edges.values():
            edges.pop(agent_id, None)

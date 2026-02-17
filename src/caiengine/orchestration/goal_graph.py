"""Goal graph data model for orchestration planning."""

from __future__ import annotations

from collections import deque
from copy import deepcopy
from dataclasses import dataclass, field
from enum import Enum
from typing import Any


class NodeType(str, Enum):
    """Supported orchestration node types."""

    GOAL = "GOAL"
    DECISION = "DECISION"
    TOOL = "TOOL"
    EXPERT = "EXPERT"
    CONTEXT_LAYER = "CONTEXT_LAYER"


@dataclass(slots=True)
class Node:
    """A typed node in a goal graph."""

    id: str
    type: NodeType
    label: str
    metadata: dict[str, Any] = field(default_factory=dict)


@dataclass(slots=True)
class Edge:
    """A directed relationship between two nodes."""

    source: str
    target: str
    label: str = ""
    metadata: dict[str, Any] = field(default_factory=dict)


@dataclass(slots=True)
class GoalGraph:
    """Directed graph connecting goals, decisions, tools, experts and context."""

    nodes: dict[str, Node] = field(default_factory=dict)
    edges: list[Edge] = field(default_factory=list)

    def add_node(self, node: Node) -> None:
        """Insert or replace a node by its identifier."""
        self.nodes[node.id] = node

    def add_edge(self, edge: Edge) -> None:
        """Insert a directed edge. Source and target nodes must exist."""
        if edge.source not in self.nodes:
            raise KeyError(f"Unknown source node: {edge.source}")
        if edge.target not in self.nodes:
            raise KeyError(f"Unknown target node: {edge.target}")
        self.edges.append(edge)

    def neighbors(self, node_id: str) -> list[Node]:
        """Return outbound neighbor nodes for ``node_id``."""
        if node_id not in self.nodes:
            return []

        return [self.nodes[edge.target] for edge in self.edges if edge.source == node_id]

    def subgraph_for(self, goal_id: str) -> GoalGraph:
        """Build a subgraph containing nodes reachable from ``goal_id``."""
        if goal_id not in self.nodes:
            raise KeyError(f"Unknown goal node: {goal_id}")

        reachable: set[str] = set()
        queue: deque[str] = deque([goal_id])

        while queue:
            current = queue.popleft()
            if current in reachable:
                continue

            reachable.add(current)
            for neighbor in self.neighbors(current):
                if neighbor.id not in reachable:
                    queue.append(neighbor.id)

        subgraph = GoalGraph()
        for node_id in reachable:
            node = self.nodes[node_id]
            subgraph.add_node(
                Node(
                    id=node.id,
                    type=node.type,
                    label=node.label,
                    metadata=deepcopy(node.metadata),
                )
            )

        for edge in self.edges:
            if edge.source in reachable and edge.target in reachable:
                subgraph.add_edge(
                    Edge(
                        source=edge.source,
                        target=edge.target,
                        label=edge.label,
                        metadata=deepcopy(edge.metadata),
                    )
                )

        return subgraph

    def to_dict(self) -> dict[str, Any]:
        """Serialize graph into a JSON-compatible dictionary."""
        return {
            "nodes": [
                {
                    "id": node.id,
                    "type": node.type.value,
                    "label": node.label,
                    "metadata": deepcopy(node.metadata),
                }
                for node in self.nodes.values()
            ],
            "edges": [
                {
                    "source": edge.source,
                    "target": edge.target,
                    "label": edge.label,
                    "metadata": deepcopy(edge.metadata),
                }
                for edge in self.edges
            ],
        }

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> GoalGraph:
        """Create a graph from a dictionary produced by :meth:`to_dict`."""
        graph = cls()
        for node_data in data.get("nodes", []):
            graph.add_node(
                Node(
                    id=node_data["id"],
                    type=NodeType(node_data["type"]),
                    label=node_data["label"],
                    metadata=dict(node_data.get("metadata", {})),
                )
            )

        for edge_data in data.get("edges", []):
            graph.add_edge(
                Edge(
                    source=edge_data["source"],
                    target=edge_data["target"],
                    label=edge_data.get("label", ""),
                    metadata=dict(edge_data.get("metadata", {})),
                )
            )

        return graph

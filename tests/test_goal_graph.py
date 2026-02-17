import json
from pathlib import Path

from caiengine.orchestration.goal_graph import Edge, GoalGraph, Node, NodeType


def _build_graph() -> GoalGraph:
    graph = GoalGraph()
    graph.add_node(Node(id="goal", type=NodeType.GOAL, label="Plan dinner"))
    graph.add_node(Node(id="decision", type=NodeType.DECISION, label="Choose recipe"))
    graph.add_node(Node(id="tool", type=NodeType.TOOL, label="Recipe finder"))
    graph.add_node(Node(id="expert", type=NodeType.EXPERT, label="Dietician"))

    graph.add_edge(Edge(source="goal", target="decision", label="requires"))
    graph.add_edge(Edge(source="decision", target="tool", label="uses"))
    graph.add_edge(Edge(source="decision", target="expert", label="asks"))
    return graph


def test_goal_graph_serialization_round_trip():
    graph = _build_graph()

    payload = graph.to_dict()
    round_trip = GoalGraph.from_dict(payload)

    assert round_trip.to_dict() == payload


def test_goal_graph_neighbors_and_subgraph():
    graph = _build_graph()

    neighbors = graph.neighbors("decision")
    assert {node.id for node in neighbors} == {"tool", "expert"}

    subgraph = graph.subgraph_for("goal")
    assert set(subgraph.nodes.keys()) == {"goal", "decision", "tool", "expert"}
    assert len(subgraph.edges) == 3


def test_goal_graph_to_dict_metadata_isolation():
    graph = GoalGraph()
    graph.add_node(
        Node(
            id="goal",
            type=NodeType.GOAL,
            label="Plan dinner",
            metadata={"nested": {"priority": "high"}},
        )
    )
    graph.add_node(Node(id="tool", type=NodeType.TOOL, label="Recipe finder"))
    graph.add_edge(
        Edge(
            source="goal",
            target="tool",
            metadata={"details": {"confidence": 0.9}},
        )
    )

    payload = graph.to_dict()
    payload["nodes"][0]["metadata"]["nested"]["priority"] = "low"
    payload["edges"][0]["metadata"]["details"]["confidence"] = 0.1

    assert graph.nodes["goal"].metadata["nested"]["priority"] == "high"
    assert graph.edges[0].metadata["details"]["confidence"] == 0.9


def test_goal_graph_subgraph_isolation():
    graph = GoalGraph()
    graph.add_node(
        Node(
            id="goal",
            type=NodeType.GOAL,
            label="Plan dinner",
            metadata={"nested": {"priority": "high"}},
        )
    )
    graph.add_node(
        Node(
            id="decision",
            type=NodeType.DECISION,
            label="Choose recipe",
            metadata={"options": ["A", "B"]},
        )
    )
    graph.add_edge(
        Edge(
            source="goal",
            target="decision",
            label="requires",
            metadata={"trace": {"step": 1}},
        )
    )

    subgraph = graph.subgraph_for("goal")

    subgraph.nodes["goal"].label = "Changed"
    subgraph.nodes["goal"].metadata["nested"]["priority"] = "low"
    subgraph.edges[0].metadata["trace"]["step"] = 2

    assert graph.nodes["goal"].label == "Plan dinner"
    assert graph.nodes["goal"].metadata["nested"]["priority"] == "high"
    assert graph.edges[0].metadata["trace"]["step"] == 1


def test_goal_graph_example_fixture_loads():
    fixture_path = Path("docs/examples/meal_prep_pl_wed.json")
    payload = json.loads(fixture_path.read_text())

    graph = GoalGraph.from_dict(payload)

    assert "goal_meal_prep" in graph.nodes
    assert graph.nodes["goal_meal_prep"].type is NodeType.GOAL
    assert len(graph.neighbors("decision_menu")) == 3

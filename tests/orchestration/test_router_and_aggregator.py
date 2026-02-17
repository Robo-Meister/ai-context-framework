from caiengine.orchestration import (
    ExpertRegistry,
    ExpertResult,
    ExpertRouter,
    RuleBasedRoutingPolicy,
    SimpleConfidenceAggregator,
)


class TaggedExpert:
    def __init__(self, expert_id: str, confidence: float) -> None:
        self.expert_id = expert_id
        self.confidence = confidence

    def run(self, input: dict, context: dict) -> ExpertResult:
        return ExpertResult(
            output={"expert": self.expert_id, "request": input, "context": context},
            confidence=self.confidence,
            debug={"expert": self.expert_id},
            used_layers=["semantic"],
            model_id=self.expert_id,
            model_version="1",
        )


def test_rule_based_policy_selects_expected_expert_ids() -> None:
    registry = ExpertRegistry()
    registry.register(
        TaggedExpert("expert_text_high", 0.9),
        capabilities={
            "category": "analysis",
            "scope": "global",
            "tags": ["text", "priority"],
            "layers": ["semantic"],
        },
    )
    registry.register(
        TaggedExpert("expert_text_low", 0.4),
        capabilities={
            "category": "analysis",
            "scope": "global",
            "tags": ["text"],
            "layers": ["semantic"],
        },
    )
    registry.register(
        TaggedExpert("expert_image", 0.8),
        capabilities={
            "category": "analysis",
            "scope": "global",
            "tags": ["image"],
            "layers": ["vision"],
        },
    )

    policy = RuleBasedRoutingPolicy()
    selected = policy.select(
        experts=registry.list_experts(),
        request={"category": "analysis", "scope": "global", "tags": ["text"]},
        goal_context={},
        context_layers=["semantic"],
    )

    assert selected == ["expert_text_high", "expert_text_low"]


def test_router_and_aggregator_end_to_end() -> None:
    registry = ExpertRegistry()
    registry.register(
        TaggedExpert("expert_a", 0.31),
        capabilities={"category": "analysis", "scope": "global", "tags": ["text"], "layers": ["semantic"]},
    )
    registry.register(
        TaggedExpert("expert_b", 0.95),
        capabilities={"category": "analysis", "scope": "global", "tags": ["text"], "layers": ["semantic"]},
    )
    registry.register(
        TaggedExpert("expert_c", 0.51),
        capabilities={"category": "analysis", "scope": "global", "tags": ["image"], "layers": ["vision"]},
    )

    router = ExpertRouter(
        registry=registry,
        policy=RuleBasedRoutingPolicy(),
        aggregator=SimpleConfidenceAggregator(),
    )

    response = router.route(
        request={"category": "analysis", "scope": "global", "tags": ["text"]},
        goal_context={"goal_id": "g-1"},
        context_layers=["semantic"],
    )

    assert response["selected_experts"] == ["expert_a", "expert_b"]
    assert response["output"]["expert"] == "expert_b"
    assert response["confidence"] == 0.95
    assert len(response["debug"]["all_results"]) == 2


def test_simple_confidence_aggregator_is_stable_for_equal_confidence() -> None:
    aggregator = SimpleConfidenceAggregator()

    first = ExpertResult(
        output={"expert": "first"},
        confidence=0.7,
        debug={"index": 0},
        used_layers=["l1"],
        model_id="m1",
        model_version="v1",
    )
    second = ExpertResult(
        output={"expert": "second"},
        confidence=0.7,
        debug={"index": 1},
        used_layers=["l1"],
        model_id="m2",
        model_version="v1",
    )

    result = aggregator.aggregate([first, second])

    assert result["output"] == {"expert": "first"}
    assert [item["debug"]["index"] for item in result["debug"]["all_results"]] == [0, 1]


def test_rule_based_policy_treats_null_tags_as_empty() -> None:
    registry = ExpertRegistry()
    registry.register(
        TaggedExpert("expert_text", 0.9),
        capabilities={
            "category": "analysis",
            "scope": "global",
            "tags": ["text"],
            "layers": ["semantic"],
        },
    )

    policy = RuleBasedRoutingPolicy()
    selected = policy.select(
        experts=registry.list_experts(),
        request={"category": "analysis", "scope": "global", "tags": None},
        goal_context={},
        context_layers=["semantic"],
    )

    assert selected == ["expert_text"]

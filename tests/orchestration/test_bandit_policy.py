from caiengine.orchestration.bandit_policy import EpsilonGreedyRoutingPolicy
from caiengine.orchestration.expert_registry import RegisteredExpert


class _NoopExpert:
    def run(self, input: dict, context: dict):  # pragma: no cover - not used in policy tests
        del input, context
        return None


def _experts() -> list[RegisteredExpert]:
    return [
        RegisteredExpert(expert_id="expert_a", expert=_NoopExpert(), capabilities={}),
        RegisteredExpert(expert_id="expert_b", expert=_NoopExpert(), capabilities={}),
    ]


def test_epsilon_greedy_shifts_to_best_expert() -> None:
    policy = EpsilonGreedyRoutingPolicy(epsilon=0.0, random_seed=7)

    initial = policy.select(
        experts=_experts(),
        request={"goal": "g1", "task": "t1"},
        goal_context={},
        context_layers=[],
    )
    assert initial == ["expert_a"]

    for _ in range(20):
        policy.record_outcome("expert_a", reward=0.1, context_meta={"goal": "g1", "task": "t1"})
        policy.record_outcome("expert_b", reward=1.0, context_meta={"goal": "g1", "task": "t1"})

    selected = policy.select(
        experts=_experts(),
        request={"goal": "g1", "task": "t1"},
        goal_context={},
        context_layers=[],
    )

    assert selected == ["expert_b"]


def test_epsilon_greedy_persists_stats_in_sqlite(tmp_path) -> None:
    db_path = tmp_path / "bandit.sqlite"

    writer = EpsilonGreedyRoutingPolicy(epsilon=0.0, database=str(db_path), random_seed=1)
    for _ in range(5):
        writer.record_outcome("expert_a", reward=0.2, context_meta={"goal": "g2", "task": "t2"})
        writer.record_outcome("expert_b", reward=0.8, context_meta={"goal": "g2", "task": "t2"})

    reader = EpsilonGreedyRoutingPolicy(epsilon=0.0, database=str(db_path), random_seed=1)
    selected = reader.select(
        experts=_experts(),
        request={"goal": "g2", "task": "t2"},
        goal_context={},
        context_layers=[],
    )

    assert selected == ["expert_b"]


def test_epsilon_greedy_honors_capability_filters() -> None:
    experts = [
        RegisteredExpert(
            expert_id="text_low",
            expert=_NoopExpert(),
            capabilities={"category": "text", "tags": ["safe"], "layers": ["base"]},
        ),
        RegisteredExpert(
            expert_id="text_high",
            expert=_NoopExpert(),
            capabilities={"category": "text", "tags": ["safe"], "layers": ["base"]},
        ),
        RegisteredExpert(
            expert_id="vision_best",
            expert=_NoopExpert(),
            capabilities={"category": "vision", "tags": ["safe"], "layers": ["base"]},
        ),
    ]
    policy = EpsilonGreedyRoutingPolicy(epsilon=0.0, random_seed=11)

    for _ in range(10):
        policy.record_outcome("vision_best", reward=5.0, context_meta={"goal": "g3", "task": "t3"})
        policy.record_outcome("text_low", reward=0.1, context_meta={"goal": "g3", "task": "t3"})
        policy.record_outcome("text_high", reward=1.0, context_meta={"goal": "g3", "task": "t3"})

    selected = policy.select(
        experts=experts,
        request={"goal": "g3", "task": "t3", "category": "text", "tags": ["safe"]},
        goal_context={},
        context_layers=["base"],
    )

    assert selected == ["text_high"]


def test_invalid_table_name_raises_value_error() -> None:
    for table_name in ("1stats", "select", "name-with-dash"):
        try:
            EpsilonGreedyRoutingPolicy(table_name=table_name)
        except ValueError as exc:
            assert "table_name" in str(exc)
        else:  # pragma: no cover - explicit failure branch
            raise AssertionError(f"expected ValueError for invalid table name {table_name!r}")

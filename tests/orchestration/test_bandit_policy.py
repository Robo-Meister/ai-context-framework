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

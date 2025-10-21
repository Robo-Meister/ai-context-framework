from __future__ import annotations

from datetime import datetime, timedelta, timezone

from caiengine.core.goal_feedback_loop import (
    GoalDrivenFeedbackLoop,
    InMemoryGoalFeedbackPersistence,
    SQLiteGoalFeedbackPersistence,
)
from caiengine.core.goal_strategies.simple_goal_strategy import (
    SimpleGoalFeedbackStrategy,
)


def _strategy() -> SimpleGoalFeedbackStrategy:
    return SimpleGoalFeedbackStrategy()


def test_persisted_state_survives_restart(tmp_path) -> None:
    db_path = tmp_path / "goal_feedback.db"
    provider = SQLiteGoalFeedbackPersistence(str(db_path))
    loop = GoalDrivenFeedbackLoop(
        _strategy(), goal_state={"progress": 10}, persistence=provider
    )
    loop.extend_history([
        {"progress": 2.0, "timestamp": datetime.now(timezone.utc).isoformat()},
        {"progress": 4.0},
    ])
    loop.suggest([], [{"progress": 6.0}])

    restored = GoalDrivenFeedbackLoop(
        _strategy(), goal_state={"progress": 10}, persistence=provider
    )

    assert len(restored.history) == 3
    restored.suggest([], [])
    baseline = restored.last_analysis.get("progress", {}).get("baseline")
    assert baseline == 2.0


def test_retention_limit_caps_history() -> None:
    provider = InMemoryGoalFeedbackPersistence()
    loop = GoalDrivenFeedbackLoop(
        _strategy(),
        goal_state={"score": 10},
        persistence=provider,
        retention_limit=2,
    )
    loop.extend_history(
        [
            {"score": 1.0},
            {"score": 3.0},
            {"score": 6.0},
        ]
    )
    assert [item["score"] for item in loop.history] == [3.0, 6.0]

    restored = GoalDrivenFeedbackLoop(
        _strategy(),
        goal_state={"score": 10},
        persistence=provider,
        retention_limit=2,
    )
    restored.suggest([], [])
    baseline = restored.last_analysis.get("score", {}).get("baseline")
    assert baseline == 3.0


def test_retention_window_discards_stale_entries() -> None:
    now = datetime.now(timezone.utc)
    provider = InMemoryGoalFeedbackPersistence()
    loop = GoalDrivenFeedbackLoop(
        _strategy(),
        goal_state={"depth": 5},
        persistence=provider,
        retention_window=timedelta(seconds=1),
    )
    loop.extend_history(
        [
            {"depth": 1, "timestamp": (now - timedelta(seconds=30)).isoformat()},
            {"depth": 2, "timestamp": now.isoformat()},
        ]
    )

    assert [item["depth"] for item in loop.history] == [2]
    loop.extend_history([{"depth": 3}])
    assert [item["depth"] for item in loop.history] == [2, 3]


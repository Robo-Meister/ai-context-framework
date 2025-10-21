from __future__ import annotations

import queue
import threading

import pytest

from caiengine.core.goal_state_tracker import (
    GoalStateTracker,
    SQLiteGoalStateBackend,
)


def test_sqlite_goal_state_persists_between_tracker_instances(tmp_path):
    db_path = tmp_path / "goal_state.db"
    initial_tracker = GoalStateTracker(
        backend_config={"type": "sqlite", "database": str(db_path)}
    )
    state = {"goal": "improve retention", "progress": {"score": 0.75}}

    initial_tracker.save(state)

    rehydrated_tracker = GoalStateTracker(
        backend_config={"type": "sqlite", "database": str(db_path)}
    )
    assert rehydrated_tracker.load() == state


def test_sqlite_goal_state_thread_safe(tmp_path):
    db_path = tmp_path / "goal_state.db"
    tracker = GoalStateTracker(backend_config={"type": "sqlite", "database": str(db_path)})

    errors: queue.Queue[BaseException] = queue.Queue()

    def writer(index: int) -> None:
        try:
            tracker.save({"value": index})
        except BaseException as exc:  # pragma: no cover - defensive
            errors.put(exc)

    threads = [threading.Thread(target=writer, args=(i,)) for i in range(16)]

    for thread in threads:
        thread.start()
    for thread in threads:
        thread.join()

    if not errors.empty():
        raise errors.get()

    final_state = tracker.load()
    assert set(final_state.keys()) == {"value"}
    assert final_state["value"] in range(len(threads))


def test_goal_state_tracker_rejects_backend_and_config(tmp_path):
    db_path = tmp_path / "goal_state.db"
    backend = SQLiteGoalStateBackend(str(db_path))

    with pytest.raises(ValueError):
        GoalStateTracker(backend=backend, backend_config={"type": "memory"})

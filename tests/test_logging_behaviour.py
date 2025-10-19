import logging
from typing import Any, Dict

from caiengine.core.feedback_event_bus import FeedbackEventBus
from caiengine.core.goal_feedback_worker import GoalFeedbackWorker
from caiengine.core.goal_state_tracker import GoalStateTracker
from caiengine.providers.memory_context_provider import MemoryContextProvider


class _ExplodingLoop:
    def __init__(self) -> None:
        self.goal_state: Dict[str, Any] = {}

    def set_goal_state(self, goal_state: Dict[str, Any]) -> None:
        self.goal_state = dict(goal_state)

    def suggest(self, history, actions):  # pragma: no cover - signature compatibility
        raise RuntimeError("boom")

def test_goal_feedback_worker_logs_failures(caplog):
    loop = _ExplodingLoop()
    worker = GoalFeedbackWorker(loop, FeedbackEventBus(), GoalStateTracker(), poll_interval=0.01)

    caplog.set_level(logging.ERROR, logger=worker.logger.name)
    worker._handle_event({"type": "test", "actions": [{"id": 1}]})
    worker._process_pending_actions()

    log_messages = [record.message for record in caplog.records]
    assert any("Goal feedback loop failed" in message for message in log_messages)
    attempts = [record.attempt for record in caplog.records if hasattr(record, "attempt")]
    assert attempts and attempts[-1] == 1


def test_base_provider_logs_subscriber_failure(caplog):
    provider = MemoryContextProvider()

    def _failing_callback(_):
        raise RuntimeError("subscriber boom")

    provider.subscribe_context(_failing_callback)
    caplog.set_level(logging.ERROR, logger=provider.logger.name)

    provider.ingest_context({"payload": "value"})

    assert any("Failed to deliver context update" in record.message for record in caplog.records)
    assert any(getattr(record, "subscriber_id", None) for record in caplog.records)

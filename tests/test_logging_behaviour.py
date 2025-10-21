import logging
from typing import Any, Dict

from caiengine.core.feedback_event_bus import FeedbackEventBus
from caiengine.core.goal_feedback_worker import GoalFeedbackWorker
from caiengine.core.goal_state_tracker import GoalStateTracker
from caiengine.providers.memory_context_provider import MemoryContextProvider
from caiengine.providers.sqlite_context_provider import SQLiteContextProvider


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


def test_goal_feedback_worker_backoff_logs_retry_metadata(caplog):
    loop = _ExplodingLoop()
    worker = GoalFeedbackWorker(loop, FeedbackEventBus(), GoalStateTracker(), poll_interval=0.01)

    worker._handle_event({"type": "test", "actions": [{"id": 1}]})
    caplog.set_level(logging.DEBUG, logger=worker.logger.name)

    worker._process_pending_actions()

    error_records = [
        record
        for record in caplog.records
        if "Goal feedback loop failed to process actions" in record.message
    ]
    assert error_records, "Expected a failure log entry from the feedback worker"
    latest_error = error_records[-1]
    assert getattr(latest_error, "attempt", 0) == 1
    assert getattr(latest_error, "backoff_seconds", 0) > 0

    worker._process_pending_actions()

    defer_records = [
        record
        for record in caplog.records
        if "Deferring feedback processing due to backoff" in record.message
    ]
    assert defer_records, "Expected deferral log entry when backoff is active"
    assert getattr(defer_records[-1], "backoff_remaining", 0) >= 0


def test_sqlite_provider_logs_subscriber_failures(caplog):
    provider = SQLiteContextProvider()

    def _boom(_):
        raise RuntimeError("subscriber exploded")

    provider.subscribe_context(_boom)
    caplog.set_level(logging.ERROR, logger=provider.logger.name)

    provider.ingest_context({"payload": "value"})

    failure_logs = [
        record
        for record in caplog.records
        if "Subscriber callback failed during SQLite ingest" in record.message
    ]
    assert failure_logs
    last_log = failure_logs[-1]
    assert getattr(last_log, "subscriber_id", None)
    assert getattr(last_log, "context_id", None)

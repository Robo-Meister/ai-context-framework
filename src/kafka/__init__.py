"""Simplified Kafka client stubs used for testing."""

from __future__ import annotations

from typing import Any, Callable, Dict


class KafkaProducer:
    def __init__(self, *_, **__):
        self.sent: Dict[str, Any] = {}

    def send(self, topic: str, value: Any) -> None:
        self.sent[topic] = value

    def flush(self) -> None:  # pragma: no cover - trivial
        pass


class KafkaConsumer:
    def __init__(self, *_, **__):
        self.topic = None
        self._callback: Callable[[Any], None] | None = None

    def subscribe(self, topics, listener=None):  # pragma: no cover - not used
        self.topic = topics

    def poll(self, timeout_ms: int = 0):  # pragma: no cover - placeholder
        return None


__all__ = ["KafkaProducer", "KafkaConsumer"]

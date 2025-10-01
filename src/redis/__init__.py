"""Tiny in-memory stand-in for :mod:`redis` used in the tests."""

from __future__ import annotations

from typing import Any, Callable, Dict


class _PubSub:
    def __init__(self) -> None:
        self._handlers: Dict[str, Callable[[Dict[str, Any]], None]] = {}

    def subscribe(self, **handlers: Callable[[Dict[str, Any]], None]) -> None:
        self._handlers.update(handlers)

    def run_in_thread(self, daemon: bool = True):  # pragma: no cover - behaviour mocked in tests
        return _WorkerThread()

    def publish(self, topic: str, message: Dict[str, Any]) -> None:
        handler = self._handlers.get(topic)
        if handler:
            handler({"type": "message", "data": message})

    def unsubscribe(self, topic: str) -> None:
        self._handlers.pop(topic, None)

    def close(self) -> None:  # pragma: no cover - placeholder
        self._handlers.clear()


class _WorkerThread:
    def stop(self) -> None:  # pragma: no cover - placeholder used in tests
        pass


class Redis:
    def __init__(self, host: str = "localhost", port: int = 6379, db: int = 0):
        self.host = host
        self.port = port
        self.db = db
        self._pubsub = _PubSub()
        self._published: Dict[str, Any] = {}

    def publish(self, topic: str, message: str) -> None:
        self._published[topic] = message
        self._pubsub.publish(topic, message)

    def pubsub(self) -> _PubSub:
        return self._pubsub

    def close(self) -> None:  # pragma: no cover - placeholder
        self._pubsub.close()


__all__ = ["Redis"]

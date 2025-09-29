"""Shared fake implementations used by network control-plane tests."""

from __future__ import annotations

import time
from collections import deque
from typing import Any, Deque, Dict, Iterable, List, Optional


class FakePubSub:
    def __init__(self, *, raise_on_subscribe: bool = False):
        self.raise_on_subscribe = raise_on_subscribe
        self.channels: List[str] = []
        self.messages: Deque[Dict[str, Any]] = deque()
        self.closed = False

    def subscribe(self, channel: str) -> None:
        if self.raise_on_subscribe:
            raise RuntimeError("pubsub unavailable")
        self.channels.append(channel)

    def publish(self, channel: str, message: Any) -> None:
        self.messages.append({"type": "message", "channel": channel, "data": message})

    def listen(self) -> Iterable[Dict[str, Any]]:
        while not self.closed:
            if self.messages:
                yield self.messages.popleft()
            else:
                time.sleep(0.01)

    def close(self) -> None:
        self.closed = True


class FakeRedis:
    """Tiny in-memory Redis replacement covering operations used in tests."""

    def __init__(self, *, pubsub_available: bool = True):
        self._hashes: Dict[str, Dict[str, Any]] = {}
        self._lists: Dict[str, Deque[Any]] = {}
        self._pubsub = FakePubSub(raise_on_subscribe=not pubsub_available)
        self.published: List[Dict[str, Any]] = []

    # Hash operations -------------------------------------------------
    def hset(self, key: str, field: str, value: Any) -> None:
        self._hashes.setdefault(key, {})[field] = value

    def hget(self, key: str, field: str) -> Any:
        return self._hashes.get(key, {}).get(field)

    def hgetall(self, key: str) -> Dict[str, Any]:
        return self._hashes.get(key, {}).copy()

    def hdel(self, key: str, field: str) -> None:
        bucket = self._hashes.get(key)
        if bucket and field in bucket:
            del bucket[field]
            if not bucket:
                del self._hashes[key]

    # List operations -------------------------------------------------
    def rpush(self, key: str, value: Any) -> None:
        self._lists.setdefault(key, deque()).append(value)

    def lpop(self, key: str) -> Optional[Any]:
        queue = self._lists.get(key)
        if queue:
            try:
                return queue.popleft()
            except IndexError:
                return None
        return None

    def blpop(self, keys: Iterable[str], timeout: float = 0) -> Optional[List[Any]]:
        if isinstance(keys, (list, tuple)):
            candidates = keys
        else:
            candidates = [keys]
        deadline = time.time() + timeout
        while True:
            for key in candidates:
                item = self.lpop(key)
                if item is not None:
                    return [key, item]
            if timeout <= 0 or time.time() >= deadline:
                return None
            time.sleep(0.01)

    # Pub/Sub ---------------------------------------------------------
    def publish(self, channel: str, message: Any) -> None:
        self.published.append({"channel": channel, "message": message})
        self._pubsub.publish(channel, message)

    def pubsub(self) -> FakePubSub:
        return self._pubsub


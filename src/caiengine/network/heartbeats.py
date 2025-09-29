"""Utilities for tracking node heartbeats within the control plane."""

from __future__ import annotations

import time
from typing import Dict, Optional, Union

from .roboid import RoboId


class HeartbeatStore:
    """Persist last-seen timestamps for nodes.

    The store keeps heartbeats inside a Redis hash (or hash-like interface)
    so that the data model matches :class:`~caiengine.network.node_registry.NodeRegistry`.
    It intentionally relies on the minimal ``hset``/``hget``/``hgetall`` API so
    that in-memory fakes can be used during tests.
    """

    def __init__(self, redis_client, redis_key: str = "mesh:heartbeats"):
        self.redis = redis_client
        self.redis_key = redis_key

    @staticmethod
    def _rid(value: Union[str, RoboId]) -> str:
        return str(value) if isinstance(value, RoboId) else value

    def beat(self, robo_id: Union[str, RoboId], *, timestamp: Optional[float] = None) -> float:
        """Record a heartbeat for ``robo_id`` and return the stored timestamp."""

        ts = float(timestamp) if timestamp is not None else time.time()
        rid = self._rid(robo_id)
        self.redis.hset(self.redis_key, rid, str(ts))
        return ts

    def last_seen(self, robo_id: Union[str, RoboId]) -> Optional[float]:
        """Return the timestamp of the last heartbeat, if available."""

        rid = self._rid(robo_id)
        payload = self.redis.hget(self.redis_key, rid)
        if payload is None:
            return None

        if isinstance(payload, bytes):
            payload = payload.decode("utf-8")

        try:
            return float(payload)
        except (TypeError, ValueError):
            return None

    def remove(self, robo_id: Union[str, RoboId]) -> None:
        """Delete the stored heartbeat for ``robo_id`` if present."""

        rid = self._rid(robo_id)
        self.redis.hdel(self.redis_key, rid)

    def all(self) -> Dict[str, float]:
        """Return a mapping of ``robo_id`` to last heartbeat timestamp."""

        raw = self.redis.hgetall(self.redis_key) or {}
        records: Dict[str, float] = {}
        for key, value in raw.items():
            rid = key.decode("utf-8") if isinstance(key, bytes) else key
            if isinstance(value, bytes):
                value = value.decode("utf-8")
            try:
                records[rid] = float(value)
            except (TypeError, ValueError):
                continue
        return records


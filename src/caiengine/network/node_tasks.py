"""Task queue primitives for the mesh control plane."""

from __future__ import annotations

import json
import time
import uuid
from dataclasses import dataclass
from typing import Any, Dict, Optional

from .roboid import RoboId


@dataclass
class NodeTask:
    """Representation of a queued task destined for a specific node."""

    task_id: str
    payload: Dict[str, Any]
    created_at: float


class NodeTaskQueue:
    """Abstract queue interface used by :class:`NodeAgent`."""

    def enqueue(self, robo_id: RoboId | str, payload: Dict[str, Any]) -> NodeTask:  # pragma: no cover - interface
        raise NotImplementedError

    def dequeue(
        self,
        robo_id: RoboId | str,
        *,
        block: bool = False,
        timeout: Optional[float] = None,
    ) -> Optional[NodeTask]:  # pragma: no cover - interface
        raise NotImplementedError


class RedisNodeTaskQueue(NodeTaskQueue):
    """Redis-backed queue storing tasks per node."""

    def __init__(self, redis_client, redis_prefix: str = "mesh:tasks"):
        self.redis = redis_client
        self.prefix = redis_prefix

    @staticmethod
    def _rid(robo_id: RoboId | str) -> str:
        return str(robo_id) if isinstance(robo_id, RoboId) else robo_id

    def _key(self, robo_id: RoboId | str) -> str:
        return f"{self.prefix}:{self._rid(robo_id)}"

    @staticmethod
    def _serialise(task: NodeTask) -> str:
        return json.dumps(
            {"task_id": task.task_id, "payload": task.payload, "created_at": task.created_at}
        )

    @staticmethod
    def _deserialise(raw: Any) -> Optional[NodeTask]:
        if raw is None:
            return None
        if isinstance(raw, (bytes, bytearray)):
            raw = raw.decode("utf-8")
        if isinstance(raw, (list, tuple)) and len(raw) == 2:
            _queue, raw = raw
        if isinstance(raw, (list, tuple)) and raw:
            raw = raw[-1]
        try:
            data = json.loads(raw)
        except (TypeError, ValueError):
            return None
        return NodeTask(task_id=data["task_id"], payload=data["payload"], created_at=data["created_at"])

    def enqueue(self, robo_id: RoboId | str, payload: Dict[str, Any]) -> NodeTask:
        task = NodeTask(task_id=str(uuid.uuid4()), payload=dict(payload), created_at=time.time())
        self.redis.rpush(self._key(robo_id), self._serialise(task))
        return task

    def dequeue(
        self,
        robo_id: RoboId | str,
        *,
        block: bool = False,
        timeout: Optional[float] = None,
    ) -> Optional[NodeTask]:
        key = self._key(robo_id)
        if block:
            result = self.redis.blpop([key], timeout=timeout or 0)
        else:
            result = self.redis.lpop(key)
        return self._deserialise(result)


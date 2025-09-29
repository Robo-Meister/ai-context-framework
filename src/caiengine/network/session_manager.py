"""Redis-backed tracking of mesh communication sessions."""

import json
from typing import Dict, List, Union

try:
    from .roboid import RoboId
except Exception:  # pragma: no cover - fallback for standalone imports
    from roboid import RoboId  # type: ignore


class SessionManager:
    """Manage active mesh sessions stored in a Redis hash."""

    def __init__(self, redis_client, redis_key: str = "mesh:sessions"):
        self.redis = redis_client
        self.redis_key = redis_key

    def start(self, session_id: str, participants: List[Union[str, RoboId]]) -> None:
        """Register a session with its participating nodes.

        Parameters
        ----------
        session_id:
            Identifier for the session.
        participants:
            Iterable of node identifiers or :class:`RoboId` objects.
        """
        ids = [str(p) if isinstance(p, RoboId) else p for p in participants]
        self.redis.hset(self.redis_key, session_id, json.dumps(ids))

    def end(self, session_id: str) -> None:
        """Terminate a session and remove it from the registry."""
        self.redis.hdel(self.redis_key, session_id)

    def sessions(self) -> Dict[str, List[str]]:
        """Return all active sessions and their participants."""
        raw = self.redis.hgetall(self.redis_key) or {}
        result = {}
        for sid, data in raw.items():
            if isinstance(data, bytes):
                data = data.decode("utf-8")
            result[sid] = json.loads(data)
        return result

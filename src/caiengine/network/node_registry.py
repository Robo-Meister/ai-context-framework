"""Redis-backed registry for tracking network members by RoboID."""

from typing import Dict


class NodeRegistry:
    """Manage mesh nodes stored in a Redis hash."""

    def __init__(self, redis_client, redis_key: str = "mesh:nodes"):
        self.redis = redis_client
        self.redis_key = redis_key

    def join(self, robo_id: str, address: str) -> None:
        """Register a node with its network address."""
        self.redis.hset(self.redis_key, robo_id, address)

    def leave(self, robo_id: str) -> None:
        """Remove a node from the registry."""
        self.redis.hdel(self.redis_key, robo_id)

    def members(self) -> Dict[str, str]:
        """Return all registered nodes and their addresses."""
        return self.redis.hgetall(self.redis_key) or {}


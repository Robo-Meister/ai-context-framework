"""Redis-backed registry for tracking network members by RoboID."""

from typing import Dict, Union

from .roboid import RoboId


class NodeRegistry:
    """Manage mesh nodes stored in a Redis hash."""

    def __init__(self, redis_client, redis_key: str = "mesh:nodes"):
        self.redis = redis_client
        self.redis_key = redis_key

    def join(self, robo_id: Union[str, RoboId], address: str) -> None:
        """Register a node with its network address.

        Parameters
        ----------
        robo_id:
            Either a RoboId instance or RoboID string identifying the node.
        address:
            Network address of the node.
        """
        rid = str(robo_id) if isinstance(robo_id, RoboId) else robo_id
        self.redis.hset(self.redis_key, rid, address)

    def leave(self, robo_id: Union[str, RoboId]) -> None:
        """Remove a node from the registry."""
        rid = str(robo_id) if isinstance(robo_id, RoboId) else robo_id
        self.redis.hdel(self.redis_key, rid)

    def members(self) -> Dict[str, str]:
        """Return all registered nodes and their addresses."""
        return self.redis.hgetall(self.redis_key) or {}


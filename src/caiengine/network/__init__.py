
"""Convenience imports for the :mod:`network` package."""

from .network_manager import NetworkManager
from .simple_network import SimpleNetworkMock
from .context_bus import ContextBus
from .roboid import RoboId
from .roboid_connection import RoboIdConnection
from .node_registry import NodeRegistry
from .agent_network import AgentNetwork
from .model_registry import ModelRegistry
from .pubsub_network import PubSubNetwork

__all__ = [
    "NetworkManager",
    "SimpleNetworkMock",
    "ContextBus",
    "RoboId",
    "RoboIdConnection",
    "NodeRegistry",
    "AgentNetwork",
    "ModelRegistry",
    "PubSubNetwork",
]

try:  # Optional dependencies
    from .redis_pubsub_channel import RedisPubSubChannel

    __all__.append("RedisPubSubChannel")
except Exception:  # pragma: no cover - optional dependency not installed
    RedisPubSubChannel = None

try:
    from .kafka_pubsub_channel import KafkaPubSubChannel

    __all__.append("KafkaPubSubChannel")
except Exception:  # pragma: no cover - optional dependency not installed
    KafkaPubSubChannel = None

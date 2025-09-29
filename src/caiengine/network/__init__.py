
"""Convenience imports for the :mod:`network` package."""

from .network_manager import NetworkManager
from .simple_network import SimpleNetworkMock
from .context_bus import ContextBus
from .roboid import RoboId
from .roboid_connection import RoboIdConnection
from .node_registry import NodeRegistry
from .node_manager import NodeManager
from .session_manager import SessionManager
from .agent_network import AgentNetwork
from .capability_registry import CapabilityRegistry, CapabilityRecord
from .driver_resolver import DriverResolver, DriverResolution
from .dispatcher import MeshDispatcher, DispatchOutcome
from .observability import DispatchEvent, DispatchMonitor
from .heartbeats import HeartbeatStore
from .node_tasks import NodeTask, NodeTaskQueue, RedisNodeTaskQueue
from .node_agent import NodeAgent
from .discovery import NodeDiscoveryService, WebSocketDiscoveryClient
from .model_registry import ModelRegistry
from .pubsub_network import PubSubNetwork

__all__ = [
    "NetworkManager",
    "SimpleNetworkMock",
    "ContextBus",
    "RoboId",
    "RoboIdConnection",
    "NodeRegistry",
    "NodeManager",
    "SessionManager",
    "AgentNetwork",
    "CapabilityRegistry",
    "CapabilityRecord",
    "DriverResolver",
    "DriverResolution",
    "MeshDispatcher",
    "DispatchOutcome",
    "DispatchMonitor",
    "DispatchEvent",
    "HeartbeatStore",
    "NodeTask",
    "NodeTaskQueue",
    "RedisNodeTaskQueue",
    "NodeAgent",
    "NodeDiscoveryService",
    "WebSocketDiscoveryClient",
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

"""Context bus for relaying context updates across multiple networks."""

from typing import Callable, List, Optional
from caiengine.interfaces.network_interface import NetworkInterface


class ContextBus:
    """Simple in-memory context relay between multiple network backends."""

    def __init__(self, networks: Optional[List[NetworkInterface]] = None, filter_fn: Optional[Callable[[str, dict], bool]] = None):
        self.networks: List[NetworkInterface] = networks or []
        self.filter_fn = filter_fn

    def add_network(self, network: NetworkInterface):
        """Register an additional network backend."""
        self.networks.append(network)

    def publish(self, key: str, value: dict):
        """Broadcast a context update to all registered networks."""
        if self.filter_fn and not self.filter_fn(key, value):
            return
        message = {"key": key, "value": value}
        for net in self.networks:
            net.send("all_nodes", message)

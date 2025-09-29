"""Context bus for relaying context updates across multiple networks."""

from typing import Callable, List, Optional

from caiengine.interfaces.network_interface import NetworkInterface


class ContextBus:
    """In-memory relay that mirrors context updates across networks."""

    def __init__(
        self,
        networks: Optional[List[NetworkInterface]] = None,
        filter_fn: Optional[Callable[[str, dict], bool]] = None,
    ):
        self.networks: List[NetworkInterface] = []
        self.filter_fn = filter_fn
        if networks:
            for net in networks:
                self.add_network(net)

    def add_network(self, network: NetworkInterface):
        """Register an additional network backend and start relaying from it."""
        self.networks.append(network)
        # Listen for incoming updates from this network and relay them
        network.start_listening(
            lambda msg, _net=network: self._relay(msg, _net)
        )

    def publish(self, key: str, value: dict):
        """Broadcast a local context update to all registered networks."""
        if self.filter_fn and not self.filter_fn(key, value):
            return
        message = {"key": key, "value": value}
        for net in self.networks:
            net.send("all_nodes", message)

    # Internal methods -------------------------------------------------
    def _relay(self, message: dict, origin: NetworkInterface):
        """Forward an incoming message from ``origin`` to other networks."""
        key = message.get("key")
        value = message.get("value")
        if self.filter_fn and not self.filter_fn(key, value):
            return
        relay_msg = {"key": key, "value": value}
        for net in self.networks:
            if net is not origin:
                net.send("all_nodes", relay_msg)

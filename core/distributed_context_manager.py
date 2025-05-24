from core.cache_manager import CacheManager
from interfaces.network_interface import NetworkInterface


class DistributedContextManager:
    """
    Wraps context management with network sync capability.
    """
    def __init__(self, cache_manager: CacheManager, network: NetworkInterface):
        self.cache_manager = cache_manager
        self.network = network

    def update_context(self, key, value):
        self.cache_manager.set(key, value)
        # Broadcast update to other nodes
        self.network.send("all_nodes", {"key": key, "value": value})

    def receive_updates(self):
        message = self.network.receive()
        if message:
            data = message.get("message")
            key = data.get("key")
            value = data.get("value")
            self.cache_manager.set(key, value)
            print(f"Context updated from network: {key} -> {value}")

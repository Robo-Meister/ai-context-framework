"""Tools for synchronizing ``ContextManager`` state across network nodes."""

from core.context_manager import ContextManager
from interfaces.network_interface import NetworkInterface


class DistributedContextManager:
    """Combine a :class:`ContextManager` with a network backend."""
    def __init__(self, context_manager: ContextManager, network: NetworkInterface):
        """Create the manager and begin listening for network updates."""
        self.context_manager = context_manager
        self.network = network

        self.network.start_listening(self._on_network_message)

    def update_context(self, key, value):
        """Update locally and broadcast the change to peers."""
        self.context_manager.update_context(key, value)
        self.network.send("all_nodes", {"key": key, "value": value})

    def receive_updates(self):
        """Manually pull and apply a single pending update if present."""
        message = self.network.receive()
        if message:
            data = message.get("message")
            key = data.get("key")
            value = data.get("value")
            self.context_manager.update_context(key, value)
            print(f"Context updated from network: {key} -> {value}")

    # Optionally expose ContextManager methods here as needed
    def get_context(self, key):
        """Proxy to :class:`ContextManager.get_context`."""
        return self.context_manager.get_context(key)

    def assign_role(self, user_id, role):
        """Proxy to :class:`ContextManager.assign_role`."""
        self.context_manager.assign_role(user_id, role)

    def get_role(self, user_id):
        """Proxy to :class:`ContextManager.get_role`."""
        return self.context_manager.get_role(user_id)

    def _on_network_message(self, message):
        """Internal callback for asynchronous updates."""
        key = message.get("key")
        value = message.get("value")
        self.context_manager.update_context(key, value)
        print(f"Context updated from network: {key} -> {value}")

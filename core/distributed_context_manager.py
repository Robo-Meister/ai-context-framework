from core.context_manager import ContextManager
from interfaces.network_interface import NetworkInterface


class DistributedContextManager:
    """
    Wraps context management with network sync capability.
    """
    def __init__(self, context_manager: ContextManager, network: NetworkInterface):
        self.context_manager = context_manager
        self.network = network

        self.network.start_listening(self._on_network_message)

    def update_context(self, key, value):
        # Use ContextManager's merging logic
        self.context_manager.update_context(key, value)
        # Broadcast update to other nodes
        self.network.send("all_nodes", {"key": key, "value": value})

    def receive_updates(self):
        message = self.network.receive()
        if message:
            data = message.get("message")
            key = data.get("key")
            value = data.get("value")
            self.context_manager.update_context(key, value)
            print(f"Context updated from network: {key} -> {value}")

    # Optionally expose ContextManager methods here as needed
    def get_context(self, key):
        return self.context_manager.get_context(key)

    def assign_role(self, user_id, role):
        self.context_manager.assign_role(user_id, role)

    def get_role(self, user_id):
        return self.context_manager.get_role(user_id)

    def _on_network_message(self, message):
        # Called by NetworkManager when message arrives
        key = message.get("key")
        value = message.get("value")
        self.context_manager.update_context(key, value)
        print(f"Context updated from network: {key} -> {value}")
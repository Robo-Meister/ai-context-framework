# network/simple_network_mock.py
from interfaces.network_interface import NetworkInterface


class SimpleNetworkMock(NetworkInterface):
    def __init__(self):
        self.messages = []

    def send(self, recipient_id: str, message: dict):
        self.messages.append((recipient_id, message))
        print(f"Mock send to {recipient_id}: {message}")

    def broadcast(self, message: dict):
        self.messages.append(("broadcast", message))
        print(f"Mock broadcast: {message}")

    def receive(self):
        if self.messages:
            return self.messages.pop(0)
        return None
    def start_listening(self, on_message_callback):
        # Start background listening and call on_message_callback(msg) on new messages
        pass
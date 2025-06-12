"""Networking utilities for sending and receiving messages between nodes."""

from interfaces.network_interface import NetworkInterface
import threading
import time


class NetworkManager(NetworkInterface):
    """High-level manager that wraps a :class:`NetworkInterface` implementation."""

    def __init__(self, network_interface: NetworkInterface):
        self.network_interface = network_interface
        self.listening = False
        self.on_message_callback = None
        self._listen_thread = None

    def send(self, recipient_id: str, message: dict):
        self.network_interface.send(recipient_id, message)

    def broadcast(self, message: dict):
        self.network_interface.broadcast(message)

    def receive(self):
        """Return the next message from the underlying network if available."""
        return self.network_interface.receive()

    def _listen_loop(self):
        """Background thread fetching messages and invoking the callback."""
        while self.listening:
            msg = self.receive()
            if msg:
                _recipient, message = msg
                if self.on_message_callback:
                    self.on_message_callback(message)
            else:
                time.sleep(0.02)  # avoid busy waiting

    def start_listening(self, on_message_callback):
        """Begin asynchronously listening for incoming messages."""
        self.on_message_callback = on_message_callback
        if not self.listening:
            self.listening = True
            self._listen_thread = threading.Thread(target=self._listen_loop, daemon=True)
            self._listen_thread.start()

    def stop_listening(self):
        """Stop the background listening thread."""
        self.listening = False
        if self._listen_thread:
            self._listen_thread.join()
            self._listen_thread = None

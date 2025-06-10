"""Lightweight in-memory implementation of ``NetworkInterface`` for testing."""

from interfaces.network_interface import NetworkInterface
import threading
import time


class SimpleNetworkMock(NetworkInterface):
    """A very small network used in unit tests and local demos."""

    def __init__(self):
        self.messages = []
        self.listening = False
        self._callback = None
        self._thread = None

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
        """Process queued messages in a background thread."""
        self._callback = on_message_callback
        if not self.listening:
            self.listening = True
            self._thread = threading.Thread(target=self._loop, daemon=True)
            self._thread.start()

    def _loop(self):
        while self.listening:
            msg = self.receive()
            if msg and self._callback:
                _recipient, message = msg
                self._callback(message)
            else:
                time.sleep(0.05)

    def stop_listening(self):
        self.listening = False
        if self._thread:
            self._thread.join()
            self._thread = None

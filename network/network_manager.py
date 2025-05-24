# network/network_manager.py
from interfaces.network_interface import NetworkInterface
import threading
import time


class NetworkManager(NetworkInterface):
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
        msg = self.network_interface.receive()
        while msg:
            recipient, message = msg
            # Here you could add logic to handle messages, route them, etc.
            print(f"Received message for {recipient}: {message}")
            msg = self.network_interface.receive()

    def _listen_loop(self):
        while self.listening:
            msg = self.receive()
            if msg:
                recipient, message = msg
                if self.on_message_callback:
                    self.on_message_callback(message)
            else:
                time.sleep(0.1)  # avoid busy waiting

    def start_listening(self, on_message_callback):
        self.on_message_callback = on_message_callback
        if not self.listening:
            self.listening = True
            self._listen_thread = threading.Thread(target=self._listen_loop, daemon=True)
            self._listen_thread.start()

    def stop_listening(self):
        self.listening = False
        if self._listen_thread:
            self._listen_thread.join()
# interfaces/network_interface.py
from abc import ABC, abstractmethod


class NetworkInterface(ABC):
    @abstractmethod
    def send(self, recipient_id: str, message: dict):
        pass

    @abstractmethod
    def broadcast(self, message: dict):
        pass

    @abstractmethod
    def receive(self):
        pass

    @abstractmethod
    def start_listening(self, _on_network_message):
        pass

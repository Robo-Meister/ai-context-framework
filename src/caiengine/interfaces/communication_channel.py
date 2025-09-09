"""Interface for pub/sub communication channels."""

from abc import ABC, abstractmethod
from typing import Callable, Dict, Any


class CommunicationChannel(ABC):
    """Abstract base class for pub/sub communication channels."""

    @abstractmethod
    def publish(self, topic: str, message: Dict[str, Any]) -> None:
        """Publish a message to a topic."""

    @abstractmethod
    def subscribe(self, topic: str, callback: Callable[[Dict[str, Any]], None]) -> None:
        """Subscribe to a topic and invoke ``callback`` for each message."""

    @abstractmethod
    def unsubscribe(self, topic: str) -> None:
        """Unsubscribe from a topic."""

    @abstractmethod
    def close(self) -> None:
        """Close the channel and release resources."""

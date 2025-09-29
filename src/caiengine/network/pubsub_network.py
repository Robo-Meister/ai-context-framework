"""NetworkInterface adapter using a pub/sub CommunicationChannel."""

from __future__ import annotations

import threading
from typing import Any, Callable, Dict, List, Tuple

from caiengine.interfaces.network_interface import NetworkInterface
from caiengine.interfaces.communication_channel import CommunicationChannel


class PubSubNetwork(NetworkInterface):
    """Adapt a :class:`CommunicationChannel` to the :class:`NetworkInterface` API.

    Each node subscribes to its own topic as well as a shared broadcast topic.
    Messages are queued internally so that ``receive`` can be polled by a
    :class:`~caiengine.network.network_manager.NetworkManager`.
    """

    def __init__(self, channel: CommunicationChannel, node_id: str, broadcast_topic: str = "broadcast"):
        self._channel = channel
        self._node_id = node_id
        self._broadcast_topic = broadcast_topic
        self._messages: List[Tuple[str, Dict[str, Any]]] = []
        self._lock = threading.Lock()
        self._callback: Callable[[Dict[str, Any]], None] | None = None

        # Subscribe to direct and broadcast topics.
        self._channel.subscribe(node_id, self._create_handler(node_id))
        if broadcast_topic:
            self._channel.subscribe(broadcast_topic, self._create_handler("broadcast"))

    def _create_handler(self, tag: str) -> Callable[[Dict[str, Any]], None]:
        def handler(message: Dict[str, Any]) -> None:
            with self._lock:
                self._messages.append((tag, message))
            if self._callback:
                self._callback(message)
        return handler

    # -- NetworkInterface API -------------------------------------------------
    def send(self, recipient_id: str, message: Dict[str, Any]):
        self._channel.publish(recipient_id, message)

    def broadcast(self, message: Dict[str, Any]):
        self._channel.publish(self._broadcast_topic, message)

    def receive(self) -> Tuple[str, Dict[str, Any]] | None:
        with self._lock:
            if self._messages:
                return self._messages.pop(0)
        return None

    def start_listening(self, on_message_callback: Callable[[Dict[str, Any]], None]):
        """Register a callback invoked for each incoming message."""
        self._callback = on_message_callback

    # Optional convenience to mirror ``SimpleNetworkMock``
    def stop_listening(self):
        """Unsubscribe from topics and clear the callback."""
        self._channel.unsubscribe(self._node_id)
        if self._broadcast_topic:
            self._channel.unsubscribe(self._broadcast_topic)
        self._callback = None

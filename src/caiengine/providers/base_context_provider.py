import uuid
from typing import Callable, Dict, List

from caiengine.objects.context_data import ContextData, SubscriptionHandle


class BaseContextProvider:
    """Base class providing unified pub/sub and broadcasting."""

    def __init__(self):
        self.subscribers: Dict[SubscriptionHandle, Callable[[ContextData], None]] = {}
        self.peers: List["BaseContextProvider"] = []

    def subscribe_context(self, callback: Callable[[ContextData], None]) -> SubscriptionHandle:
        handle = uuid.uuid4()
        self.subscribers[handle] = callback
        return handle

    def add_peer(self, peer: "BaseContextProvider"):
        if peer is not self and peer not in self.peers:
            self.peers.append(peer)

    def publish_context(self, data: ContextData, broadcast: bool = True):
        for cb in self.subscribers.values():
            cb(data)
        if broadcast:
            for peer in self.peers:
                peer.publish_context(data, broadcast=False)

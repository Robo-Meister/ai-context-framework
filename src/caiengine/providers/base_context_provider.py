import logging
import uuid
from typing import Callable, Dict, List

from caiengine.objects.context_data import ContextData, SubscriptionHandle


class BaseContextProvider:
    """Base class providing unified pub/sub and broadcasting."""

    def __init__(self):
        self.logger = logging.getLogger(f"{__name__}.{self.__class__.__name__}")
        self.subscribers: Dict[SubscriptionHandle, Callable[[ContextData], None]] = {}
        self.peers: List["BaseContextProvider"] = []

    def subscribe_context(self, callback: Callable[[ContextData], None]) -> SubscriptionHandle:
        handle = uuid.uuid4()
        self.subscribers[handle] = callback
        self.logger.debug(
            "Subscriber registered", extra={"subscriber_count": len(self.subscribers)}
        )
        return handle

    def add_peer(self, peer: "BaseContextProvider"):
        if peer is not self and peer not in self.peers:
            self.peers.append(peer)
            self.logger.debug(
                "Peer added", extra={"peer": peer.__class__.__name__, "peer_count": len(self.peers)}
            )

    def publish_context(self, data: ContextData, broadcast: bool = True):
        for cb in list(self.subscribers.values()):
            try:
                cb(data)
            except Exception:
                self.logger.exception("Subscriber callback failed", extra={"data_source": data.source_id})
        if broadcast:
            for peer in self.peers:
                try:
                    peer.publish_context(data, broadcast=False)
                except Exception:
                    self.logger.exception(
                        "Failed to broadcast context to peer",
                        extra={"peer": peer.__class__.__name__},
                    )

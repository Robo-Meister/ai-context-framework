import logging
import uuid
from typing import Callable, Dict, List

from caiengine.objects.context_data import ContextData, SubscriptionHandle


class BaseContextProvider:
    """Base class providing unified pub/sub and broadcasting."""

    def __init__(self):
        self.subscribers: Dict[SubscriptionHandle, Callable[[ContextData], None]] = {}
        self.peers: List["BaseContextProvider"] = []
        self.logger = logging.getLogger(
            f"{self.__class__.__module__}.{self.__class__.__name__}"
        )

    def subscribe_context(self, callback: Callable[[ContextData], None]) -> SubscriptionHandle:
        handle = uuid.uuid4()
        self.subscribers[handle] = callback
        self.logger.debug(
            "Registered context subscriber",
            extra={"subscriber_id": str(handle)},
        )
        return handle

    def add_peer(self, peer: "BaseContextProvider"):
        if peer is not self and peer not in self.peers:
            self.peers.append(peer)
            self.logger.debug(
                "Added peer provider",
                extra={"peer": f"{peer.__class__.__module__}.{peer.__class__.__name__}"},
            )

    def publish_context(self, data: ContextData, broadcast: bool = True):
        for handle, cb in list(self.subscribers.items()):
            try:
                cb(data)
            except Exception:
                self.logger.exception(
                    "Failed to deliver context update to subscriber",
                    extra={
                        "subscriber_id": str(handle),
                        "context_source": getattr(data, "source_id", None),
                    },
                )
        if broadcast:
            for peer in self.peers:
                try:
                    peer.publish_context(data, broadcast=False)
                except Exception:
                    self.logger.exception(
                        "Peer provider failed while broadcasting context",
                        extra={
                            "peer": f"{peer.__class__.__module__}.{peer.__class__.__name__}",
                            "context_source": getattr(data, "source_id", None),
                        },
                    )

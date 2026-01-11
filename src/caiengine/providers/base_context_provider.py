import logging
import uuid
from typing import Any, Callable, Dict, List

from caiengine.objects.context_data import ContextData, SubscriptionHandle
from caiengine.objects.context_event import create_context_event


class BaseContextProvider:
    """Base class providing unified pub/sub and broadcasting."""

    def __init__(self):
        self.subscribers: Dict[SubscriptionHandle, Callable[[Dict[str, Any]], None]] = {}
        self.peers: List["BaseContextProvider"] = []
        self.logger = logging.getLogger(
            f"{self.__class__.__module__}.{self.__class__.__name__}"
        )

    def subscribe_context(self, callback: Callable[[Dict[str, Any]], None]) -> SubscriptionHandle:
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
        event_payload = create_context_event(data).to_dict()
        for handle, cb in list(self.subscribers.items()):
            try:
                cb(event_payload)
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

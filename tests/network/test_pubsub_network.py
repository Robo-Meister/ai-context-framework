import time
from typing import Any, Callable, Dict, List

from caiengine.interfaces.communication_channel import CommunicationChannel
from caiengine.network.pubsub_network import PubSubNetwork
from caiengine.network.network_manager import NetworkManager


class DummyChannel(CommunicationChannel):
    def __init__(self):
        self._subs: Dict[str, List[Callable[[Dict[str, Any]], None]]] = {}

    def publish(self, topic: str, message: Dict[str, Any]) -> None:
        for cb in list(self._subs.get(topic, [])):
            cb(message)

    def subscribe(self, topic: str, callback: Callable[[Dict[str, Any]], None]) -> None:
        self._subs.setdefault(topic, []).append(callback)

    def unsubscribe(self, topic: str) -> None:
        self._subs.pop(topic, None)

    def close(self) -> None:
        self._subs.clear()


def test_pubsub_network_send_receive():
    channel = DummyChannel()
    sender = PubSubNetwork(channel, "sender")
    receiver = PubSubNetwork(channel, "receiver")
    mgr = NetworkManager(receiver)
    received: List[Dict[str, Any]] = []
    mgr.start_listening(lambda msg: received.append(msg))

    sender.send("receiver", {"hello": "world"})
    time.sleep(0.05)
    mgr.stop_listening()

    assert {"hello": "world"} in received


def test_pubsub_network_broadcast():
    channel = DummyChannel()
    broadcaster = PubSubNetwork(channel, "node1")
    listener = PubSubNetwork(channel, "node2")
    mgr = NetworkManager(listener)
    received: List[Dict[str, Any]] = []
    mgr.start_listening(lambda msg: received.append(msg))

    broadcaster.broadcast({"foo": "bar"})
    time.sleep(0.05)
    mgr.stop_listening()

    assert {"foo": "bar"} in received

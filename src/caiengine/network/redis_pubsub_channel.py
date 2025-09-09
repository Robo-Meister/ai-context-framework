"""Redis implementation of :class:`CommunicationChannel`."""

import json
from typing import Callable, Dict, Any

from redis import Redis

from caiengine.interfaces.communication_channel import CommunicationChannel


class RedisPubSubChannel(CommunicationChannel):
    """Simple Redis backed pub/sub channel."""

    def __init__(self, host: str = "localhost", port: int = 6379, db: int = 0):
        self._client = Redis(host=host, port=port, db=db)
        self._pubsub = self._client.pubsub()
        self._thread = None
        self._callbacks: Dict[str, Callable[[Dict[str, Any]], None]] = {}

    def publish(self, topic: str, message: Dict[str, Any]) -> None:
        payload = json.dumps(message)
        self._client.publish(topic, payload)

    def subscribe(self, topic: str, callback: Callable[[Dict[str, Any]], None]) -> None:
        self._callbacks[topic] = callback
        self._pubsub.subscribe(**{topic: self._create_handler(topic)})
        if self._thread is None:
            # ``run_in_thread`` returns a ``PubSubWorkerThread``
            self._thread = self._pubsub.run_in_thread(daemon=True)

    def _create_handler(self, topic: str):
        def handler(message):
            if message.get("type") == "message":
                data = message.get("data")
                if isinstance(data, bytes):
                    data = data.decode("utf-8")
                try:
                    payload = json.loads(data)
                except Exception:
                    payload = data
                cb = self._callbacks.get(topic)
                if cb:
                    cb(payload)
        return handler

    def unsubscribe(self, topic: str) -> None:
        self._pubsub.unsubscribe(topic)
        self._callbacks.pop(topic, None)

    def close(self) -> None:
        if self._thread is not None:
            self._thread.stop()
            self._thread = None
        self._pubsub.close()
        self._client.close()

"""Kafka implementation of :class:`CommunicationChannel`."""

import json
import threading
from typing import Callable, Dict, Any

from kafka import KafkaProducer, KafkaConsumer

from caiengine.interfaces.communication_channel import CommunicationChannel


class KafkaPubSubChannel(CommunicationChannel):
    """Kafka backed pub/sub channel."""

    def __init__(self, bootstrap_servers: str = "localhost:9092", group_id: str | None = None):
        self._producer = KafkaProducer(
            bootstrap_servers=bootstrap_servers,
            value_serializer=lambda v: json.dumps(v).encode("utf-8"),
        )
        self._bootstrap_servers = bootstrap_servers
        self._group_id = group_id
        self._consumers: Dict[str, KafkaConsumer] = {}
        self._threads: Dict[str, threading.Thread] = {}

    def publish(self, topic: str, message: Dict[str, Any]) -> None:
        self._producer.send(topic, message)
        self._producer.flush()

    def subscribe(self, topic: str, callback: Callable[[Dict[str, Any]], None]) -> None:
        consumer = KafkaConsumer(
            topic,
            bootstrap_servers=self._bootstrap_servers,
            group_id=self._group_id,
            value_deserializer=lambda m: json.loads(m.decode("utf-8")),
            auto_offset_reset="earliest",
            enable_auto_commit=True,
        )
        thread = threading.Thread(target=self._consume, args=(topic, callback, consumer), daemon=True)
        thread.start()
        self._consumers[topic] = consumer
        self._threads[topic] = thread

    def _consume(self, topic: str, callback: Callable[[Dict[str, Any]], None], consumer: KafkaConsumer) -> None:
        for message in consumer:
            callback(message.value)

    def unsubscribe(self, topic: str) -> None:
        consumer = self._consumers.pop(topic, None)
        if consumer:
            consumer.close()
        thread = self._threads.pop(topic, None)
        if thread and thread.is_alive():
            thread.join(timeout=0)

    def close(self) -> None:
        for topic in list(self._consumers.keys()):
            self.unsubscribe(topic)
        self._producer.close()

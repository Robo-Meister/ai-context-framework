import json
import logging
import threading
import uuid
from datetime import datetime
from typing import List, Optional, Union

from caiengine.core.cache_manager import CacheManager
from caiengine.objects.context_data import ContextData
from caiengine.objects.context_query import ContextQuery
from caiengine.providers.base_context_provider import BaseContextProvider

try:  # pragma: no cover - optional dependency may be missing
    from kafka import KafkaConsumer, KafkaProducer
except Exception:  # pragma: no cover - optional dependency may be missing
    KafkaConsumer = None
    KafkaProducer = None


class KafkaContextProvider(BaseContextProvider):
    """Consume context messages from a Kafka topic."""

    def __init__(
        self,
        topic: str,
        bootstrap_servers: str = "localhost:9092",
        group_id: Optional[str] = None,
        auto_start: bool = True,
        publish_topic: Optional[str] = None,
        feedback_topic: Optional[str] = None,
    ):
        if KafkaConsumer is None:
            raise ImportError(
                "kafka-python package is required for KafkaContextProvider. "
                "Install it with `pip install caiengine[kafka]`."
            )
        super().__init__()
        self.topic = topic
        self.bootstrap_servers = bootstrap_servers
        self.group_id = group_id
        self.consumer = KafkaConsumer(
            topic,
            bootstrap_servers=bootstrap_servers,
            group_id=group_id,
            auto_offset_reset="earliest",
            enable_auto_commit=True,
        )
        self.publish_topic = publish_topic
        self.feedback_topic = feedback_topic
        self.producer = None
        if publish_topic or feedback_topic:
            if KafkaProducer is None:
                raise ImportError(
                    "kafka-python package is required for KafkaContextProvider. "
                    "Install it with `pip install caiengine[kafka]`."
                )
            self.producer = KafkaProducer(bootstrap_servers=bootstrap_servers)
        self.cache = CacheManager()
        self._thread: Optional[threading.Thread] = None
        if auto_start:
            self.start()
        self.logger.info(
            "Initialized Kafka context provider",
            extra={
                "topic": topic,
                "bootstrap_servers": bootstrap_servers,
                "publish_topic": publish_topic,
                "feedback_topic": feedback_topic,
            },
        )

    # ------------------------------------------------------------------
    def start(self):
        if self._thread:
            self.logger.debug("Kafka consumer thread already running")
            return
        self._thread = threading.Thread(target=self._consume_loop, daemon=True)
        self.logger.info(
            "Starting Kafka consumer thread",
            extra={"topic": self.topic},
        )
        self._thread.start()

    def stop(self):
        if self._thread:
            self.consumer.close()
            self._thread.join()
            self._thread = None
            self.logger.info(
                "Stopped Kafka consumer thread",
                extra={"topic": self.topic},
            )

    def _consume_loop(self):  # pragma: no cover - requires Kafka
        for msg in self.consumer:
            self.ingest_record(msg)

    def ingest_record(self, record):
        """Process a single Kafka record."""
        try:
            value = (
                record.value.decode()
                if isinstance(record.value, (bytes, bytearray))
                else record.value
            )
            data = json.loads(value)
        except Exception:
            self.logger.exception(
                "Failed to decode Kafka record",
                extra={"topic": self.topic},
            )
            return
        timestamp = (
            datetime.fromtimestamp(record.timestamp / 1000.0)
            if getattr(record, "timestamp", None) is not None
            else datetime.utcnow()
        )
        payload = data.get("payload", data)
        metadata = data.get("metadata") if isinstance(data, dict) else None
        self.ingest_context(payload, timestamp=timestamp, metadata=metadata)

    # ------------------------------------------------------------------
    def ingest_context(
        self,
        payload: dict,
        timestamp: Union[datetime, None] = None,
        metadata: Union[dict, None] = None,
        source_id: str = "kafka",
        confidence: float = 1.0,
        ttl: Union[int, None] = None,
    ) -> str:
        context_id = str(uuid.uuid4())
        cd = ContextData(
            payload=payload,
            timestamp=timestamp or datetime.utcnow(),
            source_id=source_id,
            confidence=confidence,
            metadata=metadata or {},
            roles=(metadata or {}).get("roles", []),
            situations=(metadata or {}).get("situations", []),
            content=(metadata or {}).get("content", ""),
        )
        self.cache.set(context_id, cd, ttl)
        super().publish_context(cd)
        if self.publish_topic and self.producer:
            try:
                msg = json.dumps({"payload": payload, "metadata": metadata or {}}).encode()
                self.producer.send(self.publish_topic, msg)
            except Exception:
                self.logger.exception(
                    "Failed to publish context to Kafka topic",
                    extra={"publish_topic": self.publish_topic},
                )
        return context_id

    def fetch_context(self, query_params: ContextQuery) -> List[ContextData]:
        results = []
        for key in list(self.cache.cache.keys()):
            cd = self.cache.get(key)
            if not cd:
                continue
            if query_params.time_range[0] <= cd.timestamp <= query_params.time_range[1]:
                results.append(cd)
        return results

    def get_context(self, query: ContextQuery) -> List[dict]:
        raw = self.fetch_context(query)
        return [self._to_dict(cd) for cd in raw]

    def _to_dict(self, cd: ContextData) -> dict:
        return {
            "id": None,
            "roles": cd.roles,
            "timestamp": cd.timestamp,
            "situations": cd.situations,
            "content": cd.content,
            "context": cd.payload,
            "confidence": cd.confidence,
        }

    def send_feedback(self, message: dict) -> None:
        """Publish a feedback message to the feedback topic."""
        if not self.feedback_topic or not self.producer:
            return
        try:
            self.producer.send(self.feedback_topic, json.dumps(message).encode())
        except Exception:
            self.logger.exception(
                "Failed to send feedback to Kafka",
                extra={"feedback_topic": self.feedback_topic},
            )

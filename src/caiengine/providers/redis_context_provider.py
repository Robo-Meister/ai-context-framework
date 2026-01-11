import logging
import threading

try:
    import redis
except ImportError:
    redis = None  # or handle this differently, e.g. raise error on usage
import uuid
import json
from typing import List, Optional
from datetime import datetime
from caiengine.objects.context_data import ContextData
from caiengine.objects.context_event import create_context_event
from caiengine.objects.context_query import ContextQuery

logger = logging.getLogger(__name__)
from .base_context_provider import BaseContextProvider

# Assuming ContextQuery and ContextData are already defined as in previous message

class RedisContextProvider(BaseContextProvider):
    def __init__(self, redis_url: str, key_prefix: str = "context:"):
        if redis is None:
            raise ImportError("Redis package is required for RedisContextProvider. "
                              "Install it with `pip install caiengine[redis]`.")
        super().__init__()
        self.redis = redis.Redis.from_url(redis_url, decode_responses=True)
        self.key_prefix = key_prefix
        # Start pub/sub listener thread
        self.pubsub = self.redis.pubsub()
        self.pubsub.subscribe("context:new")
        self.listener_thread = threading.Thread(target=self._listen_to_pubsub, daemon=True)
        self.listener_thread.start()

    def ingest_context(
        self,
        payload: dict,
        timestamp: Optional[datetime] = None,
        metadata: Optional[dict] = None,
        source_id: str = "redis",
        confidence: float = 1.0,
        ttl: Optional[int] = None,
    ) -> str:
        if metadata is None:
            metadata = {}
        else:
            metadata = dict(metadata)

        context_id = str(uuid.uuid4())
        metadata.setdefault("id", context_id)
        ts = timestamp or datetime.utcnow()

        base = f"{self.key_prefix}{context_id}"
        encoded_metadata = json.dumps(metadata)
        entries = {
            f"{base}:payload": json.dumps(payload),
            f"{base}:timestamp": ts.isoformat(),
            f"{base}:metadata": encoded_metadata,
            f"{base}:source_id": source_id,
            f"{base}:confidence": str(confidence),
        }

        for key, value in entries.items():
            if ttl:
                self.redis.setex(key, ttl, value)
            else:
                self.redis.set(key, value)

        context = ContextData(
            payload=payload,
            timestamp=ts,
            source_id=source_id,
            confidence=confidence,
            metadata=metadata,
            roles=metadata.get("roles", []),
            situations=metadata.get("situations", []),
            content=metadata.get("content", ""),
        )

        super().publish_context(context)
        event_payload = create_context_event(context, context_id=context_id).to_dict()
        self.redis.publish("context:new", json.dumps(event_payload))
        logger.info(
            "Stored context in Redis",
            extra={"context_id": context_id, "source_id": source_id},
        )
        return context_id
    def fetch_context(self, query_params: ContextQuery) -> List[ContextData]:
        keys = self.redis.keys(f"{self.key_prefix}*")
        uuids = set(":".join(k.split(":")[1:2]) for k in keys)

        context_list = []
        for context_id in uuids:
            base = f"{self.key_prefix}{context_id}"
            try:
                payload = json.loads(self.redis.get(f"{base}:payload"))
                timestamp = datetime.fromisoformat(self.redis.get(f"{base}:timestamp"))
                metadata = json.loads(self.redis.get(f"{base}:metadata") or "{}")
                source_id = self.redis.get(f"{base}:source_id") or "redis"
                confidence = float(self.redis.get(f"{base}:confidence") or 1.0)

                # Filter by time
                if query_params.time_range[0] <= timestamp <= query_params.time_range[1]:
                    context_list.append(ContextData(
                        payload=payload,
                        timestamp=timestamp,
                        source_id=source_id,
                        confidence=confidence,
                        metadata=metadata,
                        roles=metadata.get("roles", []),
                        situations=metadata.get("situations", []),
                        content=metadata.get("content", ""),
                    ))
            except Exception as e:
                logger.error("Error parsing context %s: %s", context_id, e)
        return context_list

    def get_context(self, query: ContextQuery = None) -> List[dict]:
        raw_contexts = self.fetch_context(query)
        return [self._to_dict(cd) for cd in raw_contexts]

    def _to_dict(self, cd: ContextData) -> dict:
        return {
            "id": cd.metadata.get("id", None),
            "roles": cd.metadata.get("roles", []),
            "timestamp": cd.timestamp,
            "situations": cd.metadata.get("situations", []),
            "content": cd.metadata.get("content", ""),
            "context": cd.payload,
            "confidence": cd.confidence,
        }
    def _listen_to_pubsub(self):
        for message in self.pubsub.listen():
            if message["type"] == "message":
                context_id = message["data"]
                if isinstance(context_id, str):
                    try:
                        payload = json.loads(context_id)
                    except json.JSONDecodeError:
                        payload = None
                    if isinstance(payload, dict) and payload.get("context_id"):
                        self.push_context(payload["context_id"])
                    else:
                        self.push_context(context_id)

    def push_context(self, context_id: str):
        """Manually push context by ID to all subscribers"""
        base = f"{self.key_prefix}{context_id}"
        try:
            payload = json.loads(self.redis.get(f"{base}:payload"))
            timestamp = datetime.fromisoformat(self.redis.get(f"{base}:timestamp"))
            metadata = json.loads(self.redis.get(f"{base}:metadata") or "{}")
            source_id = self.redis.get(f"{base}:source_id") or "redis"
            confidence = float(self.redis.get(f"{base}:confidence") or 1.0)

            context = ContextData(
                payload=payload,
                timestamp=timestamp,
                source_id=source_id,
                confidence=confidence,
                metadata=metadata
            )
            self.publish_context(context)
        except Exception as e:
            logger.error("Failed to push context %s: %s", context_id, e)

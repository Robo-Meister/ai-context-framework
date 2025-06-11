import threading

try:
    import redis
except ImportError:
    redis = None  # or handle this differently, e.g. raise error on usage
import uuid
import json
from typing import Callable, List
from datetime import datetime
from objects.context_data import ContextData
from objects.context_query import ContextQuery

# Assuming ContextQuery and ContextData are already defined as in previous message

class RedisContextProvider:
    def __init__(self, redis_url: str, key_prefix: str = "context:"):
        if redis is None:
            raise ImportError("Redis package is required for RedisContextProvider. "
                              "Install it with `pip install my_package[redis]`.")
        self.redis = redis.Redis.from_url(redis_url, decode_responses=True)
        self.key_prefix = key_prefix
        self.subscribers: dict[uuid.UUID, Callable[[ContextData], None]] = {}
        # Start pub/sub listener thread
        self.pubsub = self.redis.pubsub()
        self.pubsub.subscribe("context:new")
        self.listener_thread = threading.Thread(target=self._listen_to_pubsub, daemon=True)
        self.listener_thread.start()

    def ingest_context(redis_conn, context_id: str, payload: dict, timestamp: datetime, metadata: dict,
                       source_id="manual", confidence=1.0):
        base = f"context:{context_id}"
        redis_conn.set(f"{base}:payload", json.dumps(payload))
        redis_conn.set(f"{base}:timestamp", timestamp.isoformat())
        redis_conn.set(f"{base}:metadata", json.dumps(metadata))
        redis_conn.set(f"{base}:source_id", source_id)
        redis_conn.set(f"{base}:confidence", str(confidence))

        # Notify listeners via pub/sub
        redis_conn.publish("context:new", context_id)
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
                        metadata=metadata
                    ))
            except Exception as e:
                print(f"Error parsing context {context_id}: {e}")
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
                    self.push_context(context_id)

    def subscribe_context(self, callback: Callable[[ContextData], None]) -> uuid.UUID:
        handle = uuid.uuid4()
        self.subscribers[handle] = callback
        return handle

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
            for cb in self.subscribers.values():
                cb(context)
        except Exception as e:
            print(f"Failed to push context {context_id}: {e}")


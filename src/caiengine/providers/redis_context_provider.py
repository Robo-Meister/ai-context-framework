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
from caiengine.objects.context_query import ContextQuery

logger = logging.getLogger(__name__)
from .base_context_provider import BaseContextProvider

# Assuming ContextQuery and ContextData are already defined as in previous message

class RedisContextProvider(BaseContextProvider):
    def __init__(
        self,
        redis_url: str,
        key_prefix: str = "context:",
        max_entries: Optional[int] = None,
    ):
        if redis is None:
            raise ImportError("Redis package is required for RedisContextProvider. "
                              "Install it with `pip install caiengine[redis]`.")
        super().__init__()
        self.redis = redis.Redis.from_url(redis_url, decode_responses=True)
        self.key_prefix = key_prefix
        self.max_entries = max_entries
        self.index_key = f"{self.key_prefix}index"
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

        if self.max_entries and self.max_entries > 0:
            self._add_to_index(context_id, ts)
            self._prune_missing_index_entries()
            self._prune_max_entries()

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
        self.redis.publish("context:new", context_id)
        logger.info(
            "Stored context in Redis",
            extra={"context_id": context_id, "source_id": source_id},
        )
        return context_id

    def _context_keys(self, context_id: str) -> List[str]:
        base = f"{self.key_prefix}{context_id}"
        return [
            f"{base}:payload",
            f"{base}:timestamp",
            f"{base}:metadata",
            f"{base}:source_id",
            f"{base}:confidence",
        ]

    def _add_to_index(self, context_id: str, timestamp: datetime) -> None:
        self.redis.zadd(self.index_key, {context_id: timestamp.timestamp()})

    def _prune_max_entries(self) -> None:
        if not self.max_entries or self.max_entries <= 0:
            return
        excess = self.redis.zcard(self.index_key) - self.max_entries
        if excess <= 0:
            return
        removed = self.redis.zpopmin(self.index_key, excess)
        if not removed:
            return
        pipeline = self.redis.pipeline()
        for context_id, _score in removed:
            pipeline.delete(*self._context_keys(context_id))
        pipeline.execute()

    def prune_cache(self) -> None:
        """Enforce max-entry limits and remove index drift."""
        if not self.max_entries or self.max_entries <= 0:
            return
        self._prune_missing_index_entries()
        self._prune_max_entries()

    def fetch_context(self, query_params: ContextQuery) -> List[ContextData]:
        if self.max_entries and self.max_entries > 0:
            self._prune_missing_index_entries()
            self._backfill_index_if_empty()
            uuids = list(self.redis.zrange(self.index_key, 0, -1))
        else:
            keys = self.redis.keys(f"{self.key_prefix}*")
            uuids = list(set(":".join(k.split(":")[1:2]) for k in keys))

        context_list = []
        for context_id in uuids:
            base = f"{self.key_prefix}{context_id}"
            try:
                payload = json.loads(self.redis.get(f"{base}:payload"))
                timestamp = datetime.fromisoformat(self.redis.get(f"{base}:timestamp"))
                metadata = json.loads(self.redis.get(f"{base}:metadata") or "{}")
                source_id = self.redis.get(f"{base}:source_id") or "redis"
                confidence = float(self.redis.get(f"{base}:confidence") or 1.0)

                if payload is None or timestamp is None:
                    raise ValueError("Missing context fields")

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
                if self.max_entries and self.max_entries > 0:
                    self.redis.zrem(self.index_key, context_id)
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

    def _prune_missing_index_entries(self) -> None:
        if not self.max_entries or self.max_entries <= 0:
            return
        members = self.redis.zrange(self.index_key, 0, -1)
        if not members:
            return
        pipeline = self.redis.pipeline()
        for context_id in members:
            pipeline.exists(self._context_keys(context_id)[0])
        exists_results = pipeline.execute()
        for context_id, exists in zip(members, exists_results):
            if not exists:
                self.redis.zrem(self.index_key, context_id)

    def _backfill_index_if_empty(self) -> None:
        if not self.max_entries or self.max_entries <= 0:
            return
        if self.redis.zcard(self.index_key) > 0:
            return
        timestamp_keys = self.redis.keys(f"{self.key_prefix}*:timestamp")
        if not timestamp_keys:
            return
        pipeline = self.redis.pipeline()
        for key in timestamp_keys:
            pipeline.get(key)
        timestamps = pipeline.execute()
        additions = {}
        for key, ts in zip(timestamp_keys, timestamps):
            if not ts:
                continue
            try:
                timestamp = datetime.fromisoformat(ts)
            except ValueError:
                continue
            context_id = key[len(self.key_prefix):].split(":", 1)[0]
            additions[context_id] = timestamp.timestamp()
        if additions:
            self.redis.zadd(self.index_key, additions)
            self._prune_max_entries()

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

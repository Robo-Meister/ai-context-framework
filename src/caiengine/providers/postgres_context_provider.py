import json
import logging
import uuid
from datetime import datetime, timedelta
from typing import Callable, List, Optional, Union

try:
    import psycopg2
except ImportError:  # pragma: no cover - optional dependency
    psycopg2 = None

from caiengine.objects.context_data import ContextData, SubscriptionHandle
from caiengine.objects.context_query import ContextQuery


class PostgresContextProvider:
    """PostgreSQL-backed context provider."""

    def __init__(self, dsn: str):
        if psycopg2 is None:
            raise ImportError(
                "psycopg2 is required for PostgresContextProvider. Install with `pip install psycopg2-binary`."
            )
        self.logger = logging.getLogger(
            f"{self.__class__.__module__}.{self.__class__.__name__}"
        )
        self.conn = psycopg2.connect(dsn)
        self.conn.autocommit = True
        with self.conn.cursor() as cur:
            cur.execute(
                """
                CREATE TABLE IF NOT EXISTS context (
                    id TEXT PRIMARY KEY,
                    payload TEXT,
                    timestamp TIMESTAMP,
                    metadata TEXT,
                    source_id TEXT,
                    confidence REAL,
                    expiry TIMESTAMP
                )
                """
        )
        self.subscribers: dict[SubscriptionHandle, Callable[[ContextData], None]] = {}
        self.logger.debug(
            "PostgresContextProvider initialised",
            extra={"dsn": dsn.split("@")[0] if "@" in dsn else "redacted"},
        )

    def ingest_context(
        self,
        payload: dict,
        timestamp: Union[datetime, None] = None,
        metadata: Union[dict, None] = None,
        source_id: str = "postgres",
        confidence: float = 1.0,
        ttl: Optional[int] = None,
    ) -> str:
        context_id = str(uuid.uuid4())
        ts = timestamp or datetime.utcnow()
        expiry_ts = ts + timedelta(seconds=ttl) if ttl else None
        cd = ContextData(
            payload=payload,
            timestamp=ts,
            source_id=source_id,
            confidence=confidence,
            metadata=metadata or {},
            roles=(metadata or {}).get("roles", []),
            situations=(metadata or {}).get("situations", []),
            content=(metadata or {}).get("content", ""),
        )
        with self.conn.cursor() as cur:
            cur.execute(
                "INSERT INTO context VALUES (%s, %s, %s, %s, %s, %s, %s)",
                (
                    context_id,
                    json.dumps(payload),
                    ts,
                    json.dumps(metadata or {}),
                    source_id,
                    confidence,
                    expiry_ts,
                ),
            )
        for handle, cb in list(self.subscribers.items()):
            try:
                cb(cd)
            except Exception:
                self.logger.exception(
                    "Subscriber callback failed during Postgres ingest",
                    extra={
                        "subscriber_id": str(handle),
                        "context_id": context_id,
                    },
                )
        self.logger.info(
            "Context stored in Postgres backend",
            extra={
                "context_id": context_id,
                "source_id": source_id,
            },
        )
        return context_id

    def fetch_context(self, query_params: ContextQuery) -> List[ContextData]:
        start = query_params.time_range[0]
        end = query_params.time_range[1]
        now = datetime.utcnow()
        with self.conn.cursor() as cur:
            cur.execute(
                """
                SELECT id, payload, timestamp, metadata, source_id, confidence
                FROM context
                WHERE timestamp >= %s AND timestamp <= %s
                  AND (expiry IS NULL OR expiry > %s)
                """,
                (start, end, now),
            )
            rows = cur.fetchall()
        result: List[ContextData] = []
        for row in rows:
            payload = json.loads(row[1])
            ts = row[2]
            metadata = json.loads(row[3])
            cd = ContextData(
                payload=payload,
                timestamp=ts,
                source_id=row[4],
                confidence=row[5],
                metadata=metadata,
                roles=metadata.get("roles", []),
                situations=metadata.get("situations", []),
                content=metadata.get("content", ""),
            )
            result.append(cd)
        self.logger.debug(
            "Fetched context rows from Postgres",
            extra={"result_count": len(result)},
        )
        return result

    def get_context(self, query: ContextQuery) -> List[dict]:
        raw = self.fetch_context(query)
        return [self._to_dict(cd) for cd in raw]

    def subscribe_context(self, callback: Callable[[ContextData], None]) -> SubscriptionHandle:
        handle = uuid.uuid4()
        self.subscribers[handle] = callback
        self.logger.debug(
            "Registered Postgres subscriber",
            extra={"subscriber_id": str(handle)},
        )
        return handle

    def publish_context(
        self,
        payload: dict,
        timestamp: Union[datetime, None] = None,
        metadata: Union[dict, None] = None,
        source_id: str = "postgres",
        confidence: float = 1.0,
        ttl: Optional[int] = None,
    ) -> str:
        return self.ingest_context(payload, timestamp, metadata, source_id, confidence, ttl)

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

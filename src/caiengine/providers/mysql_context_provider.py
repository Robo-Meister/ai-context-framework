import json
import logging
import uuid
from datetime import datetime, timedelta
from typing import Callable, List, Optional, Union

try:
    import mysql.connector
except ImportError:  # pragma: no cover - optional dependency
    mysql = None
else:
    mysql = mysql.connector

from caiengine.objects.context_data import ContextData, SubscriptionHandle
from caiengine.objects.context_event import create_context_event
from caiengine.objects.context_query import ContextQuery


class MySQLContextProvider:
    """MySQL-backed context provider."""

    def __init__(self, **connect_kwargs):
        if mysql is None:
            raise ImportError(
                "mysql-connector-python is required for MySQLContextProvider. Install with `pip install mysql-connector-python`."
            )
        self.logger = logging.getLogger(
            f"{self.__class__.__module__}.{self.__class__.__name__}"
        )
        self.conn = mysql.connect(**connect_kwargs)
        self.conn.autocommit = True
        cur = self.conn.cursor()
        cur.execute(
            """
            CREATE TABLE IF NOT EXISTS context (
                id VARCHAR(255) PRIMARY KEY,
                payload TEXT,
                timestamp DATETIME,
                metadata TEXT,
                source_id VARCHAR(255),
                confidence DOUBLE,
                expiry DATETIME
            )
            """
        )
        cur.close()
        self.subscribers: dict[SubscriptionHandle, Callable[[dict], None]] = {}
        self.logger.debug(
            "MySQLContextProvider initialised",
            extra={"options": {k: v for k, v in connect_kwargs.items() if k != "password"}},
        )

    def ingest_context(
        self,
        payload: dict,
        timestamp: Union[datetime, None] = None,
        metadata: Union[dict, None] = None,
        source_id: str = "mysql",
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
        cur = self.conn.cursor()
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
        cur.close()
        event_payload = create_context_event(cd, context_id=context_id).to_dict()
        for handle, cb in list(self.subscribers.items()):
            try:
                cb(event_payload)
            except Exception:
                self.logger.exception(
                    "Subscriber callback failed during MySQL ingest",
                    extra={
                        "subscriber_id": str(handle),
                        "context_id": context_id,
                    },
                )
        self.logger.info(
            "Context stored in MySQL backend",
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
        cur = self.conn.cursor()
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
        cur.close()
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
            "Fetched context rows from MySQL",
            extra={"result_count": len(result)},
        )
        return result

    def get_context(self, query: ContextQuery) -> List[dict]:
        raw = self.fetch_context(query)
        return [self._to_dict(cd) for cd in raw]

    def subscribe_context(self, callback: Callable[[dict], None]) -> SubscriptionHandle:
        handle = uuid.uuid4()
        self.subscribers[handle] = callback
        self.logger.debug(
            "Registered MySQL subscriber",
            extra={"subscriber_id": str(handle)},
        )
        return handle

    def publish_context(
        self,
        payload: dict,
        timestamp: Union[datetime, None] = None,
        metadata: Union[dict, None] = None,
        source_id: str = "mysql",
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

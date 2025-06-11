import sqlite3
import uuid
import json
from datetime import datetime, timedelta
from typing import Callable, List, Optional, Union

from objects.context_data import ContextData, SubscriptionHandle
from objects.context_query import ContextQuery


class SQLiteContextProvider:
    """SQLite-backed context provider for local storage."""

    def __init__(self, db_path: str = ":memory:"):
        self.conn = sqlite3.connect(db_path, check_same_thread=False)
        self.conn.execute(
            """
            CREATE TABLE IF NOT EXISTS context (
                id TEXT PRIMARY KEY,
                payload TEXT,
                timestamp TEXT,
                metadata TEXT,
                source_id TEXT,
                confidence REAL,
                expiry TEXT
            )
            """
        )
        self.conn.commit()
        self.subscribers: dict[SubscriptionHandle, Callable[[ContextData], None]] = {}

    def ingest_context(
        self,
        payload: dict,
        timestamp: Union[datetime, None] = None,
        metadata: Union[dict, None] = None,
        source_id: str = "sqlite",
        confidence: float = 1.0,
        ttl: Optional[int] = None,
    ) -> str:
        context_id = str(uuid.uuid4())
        ts = timestamp or datetime.utcnow()
        expiry_ts = (ts + timedelta(seconds=ttl)).isoformat() if ttl else None
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
        self.conn.execute(
            "INSERT INTO context VALUES (?, ?, ?, ?, ?, ?, ?)",
            (
                context_id,
                json.dumps(payload),
                ts.isoformat(),
                json.dumps(metadata or {}),
                source_id,
                confidence,
                expiry_ts,
            ),
        )
        self.conn.commit()
        for cb in self.subscribers.values():
            cb(cd)
        return context_id

    def fetch_context(self, query_params: ContextQuery) -> List[ContextData]:
        start = query_params.time_range[0].isoformat()
        end = query_params.time_range[1].isoformat()
        now = datetime.utcnow().isoformat()
        rows = self.conn.execute(
            """
            SELECT id, payload, timestamp, metadata, source_id, confidence FROM context
            WHERE timestamp >= ? AND timestamp <= ?
            AND (expiry IS NULL OR expiry > ?)
            """,
            (start, end, now),
        ).fetchall()
        result = []
        for row in rows:
            payload = json.loads(row[1])
            ts = datetime.fromisoformat(row[2])
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
        return result

    def get_context(self, query: ContextQuery) -> List[dict]:
        raw = self.fetch_context(query)
        return [self._to_dict(cd) for cd in raw]

    def subscribe_context(self, callback: Callable[[ContextData], None]) -> SubscriptionHandle:
        handle = uuid.uuid4()
        self.subscribers[handle] = callback
        return handle

    def publish_context(
        self,
        payload: dict,
        timestamp: Union[datetime, None] = None,
        metadata: Union[dict, None] = None,
        source_id: str = "sqlite",
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

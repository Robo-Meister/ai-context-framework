import uuid
from datetime import datetime
from typing import Callable, List

import objects.context_data as ContextData
import objects.context_query as ContextQuery


class SimpleContextProvider:
    """Very small in-memory provider for examples and tests."""

    def __init__(self):
        self._data: List[ContextData.ContextData] = []
        self._subscribers: dict[uuid.UUID, Callable[[ContextData.ContextData], None]] = {}

    def ingest_context(
        self,
        payload: dict,
        timestamp: datetime | None = None,
        metadata: dict | None = None,
        source_id: str = "simple",
        confidence: float = 1.0,
    ) -> str:
        context_id = str(uuid.uuid4())
        cd = ContextData.ContextData(
            payload=payload,
            timestamp=timestamp or datetime.utcnow(),
            source_id=source_id,
            confidence=confidence,
            metadata=metadata or {},
            roles=(metadata or {}).get("roles", []),
            situations=(metadata or {}).get("situations", []),
            content=(metadata or {}).get("content", ""),
        )
        self._data.append(cd)
        for cb in self._subscribers.values():
            cb(cd)
        return context_id

    def fetch_context(self, query_params: ContextQuery.ContextQuery) -> List[ContextData.ContextData]:
        results = []
        for cd in self._data:
            if query_params.time_range[0] <= cd.timestamp <= query_params.time_range[1]:
                results.append(cd)
        return results

    def get_context(self, query: ContextQuery.ContextQuery) -> List[dict]:
        raw = self.fetch_context(query)
        return [self._to_dict(cd) for cd in raw]

    def subscribe_context(self, callback: Callable[[ContextData.ContextData], None]) -> uuid.UUID:
        handle = uuid.uuid4()
        self._subscribers[handle] = callback
        return handle

    def publish_context(
        self,
        payload: dict,
        timestamp: datetime | None = None,
        metadata: dict | None = None,
        source_id: str = "simple",
        confidence: float = 1.0,
    ):
        self.ingest_context(payload, timestamp, metadata, source_id, confidence)

    def _to_dict(self, cd: ContextData.ContextData) -> dict:
        return {
            "id": None,
            "roles": cd.roles,
            "timestamp": cd.timestamp,
            "situations": cd.situations,
            "content": cd.content,
            "context": cd.payload,
            "confidence": cd.confidence,
        }

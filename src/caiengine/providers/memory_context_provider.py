import uuid
from datetime import datetime
from typing import List, Union, Optional

from caiengine.core.cache_manager import CacheManager
from caiengine.objects.context_data import ContextData
from caiengine.objects.ocr_metadata import OCRMetadata
from caiengine.objects.context_query import ContextQuery
from .base_context_provider import BaseContextProvider


class MemoryContextProvider(BaseContextProvider):
    """In-memory context provider using :class:`CacheManager`."""

    def __init__(self):
        super().__init__()
        self.cache = CacheManager()

    def ingest_context(
            self,
            payload: dict,
            timestamp: Union[datetime, None] = None,
            metadata: Union[dict, None] = None,
            source_id: str = "memory",
            confidence: float = 1.0,
            ttl: Union[int, None] = None,
            ocr_metadata: Optional[OCRMetadata] = None,
    ) -> str:
        """Store a new context entry and notify subscribers."""
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
            ocr_metadata=ocr_metadata,
        )
        self.cache.set(context_id, cd, ttl)
        super().publish_context(cd)
        self.logger.info(
            "Stored context in memory",
            extra={"context_id": context_id, "source_id": source_id},
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
        self.logger.debug(
            "Fetched context records from memory",
            extra={"result_count": len(results)},
        )
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
            "ocr_metadata": cd.ocr_metadata.to_dict() if cd.ocr_metadata else None,
        }

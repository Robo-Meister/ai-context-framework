import uuid
from datetime import datetime
from typing import List, Optional

import caiengine.objects.context_data as ContextData
import caiengine.objects.context_query as ContextQuery
from caiengine.objects.ocr_metadata import OCRMetadata
from .base_context_provider import BaseContextProvider


class SimpleContextProvider(BaseContextProvider):
    """Very small in-memory provider for examples and tests."""

    def __init__(self):
        super().__init__()
        self._data: List[ContextData.ContextData] = []
        self.logger.debug("Simple context provider initialised")

    def ingest_context(
        self,
        payload: dict,
        timestamp: datetime | None = None,
        metadata: dict | None = None,
        source_id: str = "simple",
        confidence: float = 1.0,
        ocr_metadata: Optional[OCRMetadata] = None,
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
            ocr_metadata=ocr_metadata,
        )
        self._data.append(cd)
        self.logger.info(
            "Stored context entry",
            extra={"entry_id": context_id, "source_id": cd.source_id, "total_entries": len(self._data)},
        )
        super().publish_context(cd)
        return context_id

    def fetch_context(self, query_params: ContextQuery.ContextQuery) -> List[ContextData.ContextData]:
        results = []
        for cd in self._data:
            if query_params.time_range[0] <= cd.timestamp <= query_params.time_range[1]:
                results.append(cd)
        self.logger.debug(
            "Fetched simple context entries",
            extra={"count": len(results)},
        )
        return results

    def get_context(self, query: ContextQuery.ContextQuery) -> List[dict]:
        raw = self.fetch_context(query)
        return [self._to_dict(cd) for cd in raw]

    def _to_dict(self, cd: ContextData.ContextData) -> dict:
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

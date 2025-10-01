"""Context provider specialised for OCR-ingested documents."""

from __future__ import annotations

from datetime import datetime
from typing import TYPE_CHECKING, Any, Dict, List, Optional, Sequence, Union

from caiengine.objects.context_query import ContextQuery
from caiengine.objects.ocr_metadata import OCRMetadata, OCRSpan

from .memory_context_provider import MemoryContextProvider

if TYPE_CHECKING:  # pragma: no cover - imported for type checking only
    from caiengine.objects.context_data import ContextData


class OCRContextProvider(MemoryContextProvider):
    """Store OCR payloads with spatial metadata for downstream modules."""

    def ingest_ocr_document(
        self,
        raw_text: str,
        *,
        display_text: Optional[str] = None,
        document_type_hint: Optional[str] = None,
        spans: Optional[Sequence[Union[OCRSpan, Dict[str, Any]]]] = None,
        confidence_scores: Optional[Dict[str, float]] = None,
        language: Optional[str] = None,
        extras: Optional[Dict[str, Any]] = None,
        timestamp: Optional[datetime] = None,
        metadata: Optional[Dict[str, Any]] = None,
        source_id: str = "ocr",
        confidence: float = 1.0,
    ) -> str:
        """Ingest OCR data and broadcast a :class:`ContextData` instance."""

        ocr_metadata = OCRMetadata(
            raw_text=raw_text,
            display_text=display_text,
            document_type_hint=document_type_hint,
            spans=OCRMetadata.normalise_spans(spans),
            confidence_scores=confidence_scores or {},
            language=language,
            extras=extras or {},
        )

        payload = ocr_metadata.to_payload()
        enriched_metadata = dict(metadata or {})
        if "roles" not in enriched_metadata:
            enriched_metadata["roles"] = []
        if "situations" not in enriched_metadata:
            enriched_metadata["situations"] = []
        if "content" not in enriched_metadata:
            enriched_metadata["content"] = payload["text"]

        return super().ingest_context(
            payload=payload,
            timestamp=timestamp,
            metadata=enriched_metadata,
            source_id=source_id,
            confidence=confidence,
            ocr_metadata=ocr_metadata,
        )

    def get_structured_context(self, query: ContextQuery) -> List["ContextData"]:
        """Return raw :class:`ContextData` records for advanced OCR consumers."""

        return self.fetch_context(query)


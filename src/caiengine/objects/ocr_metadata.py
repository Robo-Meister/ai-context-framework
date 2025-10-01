"""Data structures representing OCR metadata for context payloads."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional, Sequence, Tuple, Union

__all__ = ["OCRMetadata", "OCRSpan", "BoundingBox", "OffsetRange"]


BoundingBox = Tuple[float, float, float, float]
OffsetRange = Tuple[int, int]


@dataclass
class OCRSpan:
    """Represents a candidate OCR field with spatial metadata."""

    field_name: str
    value: str
    bbox: Optional[BoundingBox] = None
    page_number: Optional[int] = None
    confidence: Optional[float] = None
    offsets: Optional[OffsetRange] = None
    extra: Dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> Dict[str, Any]:
        """Convert the span to a serialisable dictionary."""

        data: Dict[str, Any] = {
            "field_name": self.field_name,
            "value": self.value,
        }
        if self.bbox is not None:
            data["bbox"] = self.bbox
        if self.page_number is not None:
            data["page_number"] = self.page_number
        if self.confidence is not None:
            data["confidence"] = self.confidence
        if self.offsets is not None:
            data["offsets"] = self.offsets
        if self.extra:
            data["extra"] = self.extra
        return data


@dataclass
class OCRMetadata:
    """Container for OCR-specific payload signals."""

    raw_text: str
    document_type_hint: Optional[str] = None
    display_text: Optional[str] = None
    spans: List[OCRSpan] = field(default_factory=list)
    confidence_scores: Dict[str, float] = field(default_factory=dict)
    language: Optional[str] = None
    extras: Dict[str, Any] = field(default_factory=dict)

    def to_payload(self) -> Dict[str, Any]:
        """Create a payload dict suitable for storage in :class:`ContextData`."""

        payload: Dict[str, Any] = {
            "text": self.raw_text,
            "display_text": self.display_text or self.raw_text,
            "document_type_hint": self.document_type_hint,
            "spans": [span.to_dict() for span in self.spans],
            "confidence_scores": self.confidence_scores,
        }
        if self.language is not None:
            payload["language"] = self.language
        if self.extras:
            payload["extras"] = self.extras
        return payload

    def to_dict(self) -> Dict[str, Any]:
        """Serialise the metadata into a dictionary, keeping structured spans."""

        data = self.to_payload()
        data["spans"] = [span.to_dict() for span in self.spans]
        return data

    @classmethod
    def normalise_spans(
        cls, spans: Optional[Sequence[Union["OCRSpan", Dict[str, Any]]]]
    ) -> List["OCRSpan"]:
        """Coerce dictionaries into :class:`OCRSpan` instances."""

        if not spans:
            return []

        normalised: List[OCRSpan] = []
        for span in spans:
            if isinstance(span, OCRSpan):
                normalised.append(span)
                continue

            if not isinstance(span, dict):
                raise TypeError(
                    "OCR spans must be OCRSpan instances or dictionaries; "
                    f"received {type(span)!r}."
                )

            normalised.append(
                OCRSpan(
                    field_name=span.get("field_name") or span.get("field", ""),
                    value=span.get("value", ""),
                    bbox=span.get("bbox"),
                    page_number=span.get("page_number"),
                    confidence=span.get("confidence"),
                    offsets=span.get("offsets"),
                    extra=span.get("extra", {}),
                )
            )
        return normalised


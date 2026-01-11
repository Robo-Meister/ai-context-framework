"""Structured context event payloads for provider pub/sub."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from typing import Any, Dict, Optional
import uuid

from .context_data import ContextData
from .ocr_metadata import OCRMetadata

__all__ = ["ContextEventPayload", "create_context_event", "context_data_from_payload"]


def _serialise_timestamp(value: Any) -> Any:
    if isinstance(value, datetime):
        return value.isoformat()
    return value


def _normalise_timestamp(value: Any) -> datetime:
    if isinstance(value, datetime):
        return value
    if isinstance(value, str):
        try:
            return datetime.fromisoformat(value)
        except ValueError:
            return datetime.utcnow()
    return datetime.utcnow()


def context_data_to_payload(data: ContextData) -> Dict[str, Any]:
    return {
        "payload": data.payload,
        "timestamp": _serialise_timestamp(data.timestamp),
        "source_id": data.source_id,
        "metadata": data.metadata,
        "roles": data.roles,
        "situations": data.situations,
        "content": data.content,
        "confidence": data.confidence,
        "ocr_metadata": data.ocr_metadata.to_dict() if data.ocr_metadata else None,
    }


def context_data_from_payload(payload: Dict[str, Any]) -> ContextData:
    timestamp = _normalise_timestamp(payload.get("timestamp"))
    metadata = payload.get("metadata") or {}
    ocr_metadata = payload.get("ocr_metadata")
    if ocr_metadata and isinstance(ocr_metadata, OCRMetadata):
        resolved_ocr = ocr_metadata
    else:
        resolved_ocr = None
    return ContextData(
        payload=payload.get("payload", {}),
        timestamp=timestamp,
        source_id=payload.get("source_id", "unknown"),
        metadata=metadata,
        roles=payload.get("roles", metadata.get("roles", [])),
        situations=payload.get("situations", metadata.get("situations", [])),
        content=payload.get("content", metadata.get("content", "")),
        confidence=float(payload.get("confidence", 1.0)),
        ocr_metadata=resolved_ocr,
    )


@dataclass(frozen=True)
class ContextEventPayload:
    context_id: str
    action: str
    status: str
    timestamps: Dict[str, datetime]
    goal_metrics: Dict[str, Any]
    context: ContextData

    def to_dict(self) -> Dict[str, Any]:
        return {
            "context_id": self.context_id,
            "action": self.action,
            "status": self.status,
            "timestamps": {
                key: _serialise_timestamp(value) for key, value in self.timestamps.items()
            },
            "goal_metrics": self.goal_metrics,
            "context": context_data_to_payload(self.context),
        }


def create_context_event(
    data: ContextData,
    *,
    context_id: Optional[str] = None,
    action: str = "context_update",
    status: str = "published",
    goal_metrics: Optional[Dict[str, Any]] = None,
    timestamps: Optional[Dict[str, datetime]] = None,
) -> ContextEventPayload:
    resolved_context_id = context_id or (data.metadata or {}).get("id")
    if not resolved_context_id:
        resolved_context_id = str(uuid.uuid4())
    resolved_timestamps = {
        "context_time": data.timestamp,
        "event_time": datetime.utcnow(),
    }
    if timestamps:
        resolved_timestamps.update(timestamps)
    return ContextEventPayload(
        context_id=resolved_context_id,
        action=action,
        status=status,
        timestamps=resolved_timestamps,
        goal_metrics=goal_metrics or {},
        context=data,
    )

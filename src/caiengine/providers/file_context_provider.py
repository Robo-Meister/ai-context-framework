import json
import logging
import os
import uuid
from typing import Callable, List, Union
from datetime import datetime

from caiengine.objects.context_data import ContextData, SubscriptionHandle
from caiengine.objects.context_query import ContextQuery
from .base_context_provider import BaseContextProvider


class FileContextProvider(BaseContextProvider):
    """Persist context entries to a local JSON file."""

    def __init__(self, file_path: str):
        super().__init__()
        self.file_path = file_path
        self.logger = logging.getLogger(f"{__name__}.{self.__class__.__name__}")
        # Ensure the storage file exists
        if not os.path.exists(self.file_path):
            with open(self.file_path, "w", encoding="utf-8") as f:
                json.dump([], f)
            self.logger.info("Created new context store", extra={"path": self.file_path})

    def _load_entries(self) -> List[dict]:
        try:
            with open(self.file_path, "r", encoding="utf-8") as f:
                return json.load(f)
        except FileNotFoundError:
            self.logger.warning(
                "Context file missing; returning empty result", extra={"path": self.file_path}
            )
            return []
        except json.JSONDecodeError:
            self.logger.error(
                "Failed to decode context file; ignoring corrupted contents",
                extra={"path": self.file_path},
            )
            return []
        except OSError:
            self.logger.exception(
                "Failed to read context file", extra={"path": self.file_path}
            )
            raise

    def _save_entries(self, entries: List[dict]):
        try:
            with open(self.file_path, "w", encoding="utf-8") as f:
                json.dump(entries, f, indent=2)
        except OSError:
            self.logger.exception(
                "Failed to persist context entries", extra={"path": self.file_path}
            )
            raise

    def ingest_context(
        self,
        payload: dict,
        timestamp: Union[datetime, None] = None,
        metadata: Union[dict, None] = None,
        source_id: str = "file",
        confidence: float = 1.0,
    ) -> str:
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
        )
        entries = self._load_entries()
        entries.append(
            {
                "id": context_id,
                "timestamp": cd.timestamp.isoformat(),
                "source_id": cd.source_id,
                "confidence": cd.confidence,
                "metadata": cd.metadata,
                "data": cd.payload,
            }
        )
        self._save_entries(entries)
        self.logger.info(
            "Context entry ingested",
            extra={
                "path": self.file_path,
                "entry_id": context_id,
                "entries": len(entries),
            },
        )
        super().publish_context(cd)
        return context_id

    def fetch_context(self, query_params: ContextQuery) -> List[ContextData]:
        entries = self._load_entries()
        results = []
        for entry in entries:
            ts = datetime.fromisoformat(entry["timestamp"])
            if query_params.time_range[0] <= ts <= query_params.time_range[1]:
                metadata = entry.get("metadata", {})
                results.append(
                    ContextData(
                        payload=entry.get("data", {}),
                        timestamp=ts,
                        source_id=entry.get("source_id", "file"),
                        metadata=metadata,
                        roles=metadata.get("roles", []),
                        situations=metadata.get("situations", []),
                        content=metadata.get("content", ""),
                        confidence=entry.get("confidence", 1.0),
                    )
                )
        return results

    def get_context(self, query: ContextQuery) -> List[dict]:
        raw_contexts = self.fetch_context(query)
        return [self._to_dict(cd) for cd in raw_contexts]

    def subscribe_context(self, callback: Callable[[ContextData], None]) -> SubscriptionHandle:
        return super().subscribe_context(callback)

    def publish_context(
        self,
        payload: dict,
        timestamp: Union[datetime, None] = None,
        metadata: Union[dict, None] = None,
        source_id: str = "file",
        confidence: float = 1.0,
    ):
        return self.ingest_context(payload, timestamp, metadata, source_id, confidence)

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

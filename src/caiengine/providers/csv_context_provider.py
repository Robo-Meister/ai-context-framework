import csv
import os
import json
import uuid
from datetime import datetime
from typing import Callable, List, Union

from caiengine.objects.context_data import ContextData, SubscriptionHandle
from caiengine.objects.context_query import ContextQuery
from .base_context_provider import BaseContextProvider


class CSVContextProvider(BaseContextProvider):
    """Persist context entries to a local CSV file."""

    def __init__(self, file_path: str):
        super().__init__()
        self.file_path = file_path
        if not os.path.exists(self.file_path):
            with open(self.file_path, "w", newline="", encoding="utf-8") as f:
                writer = csv.writer(f)
                writer.writerow([
                    "id",
                    "timestamp",
                    "source_id",
                    "confidence",
                    "metadata",
                    "data",
                ])

    def _write_row(self, row: dict):
        with open(self.file_path, "a", newline="", encoding="utf-8") as f:
            writer = csv.writer(f)
            writer.writerow(
                [
                    row["id"],
                    row["timestamp"],
                    row["source_id"],
                    row["confidence"],
                    row["metadata"],
                    row["data"],
                ]
            )

    def _read_rows(self) -> List[dict]:
        if not os.path.exists(self.file_path):
            return []
        with open(self.file_path, "r", newline="", encoding="utf-8") as f:
            reader = csv.DictReader(f)
            return list(reader)

    def ingest_context(
        self,
        payload: dict,
        timestamp: Union[datetime, None] = None,
        metadata: Union[dict, None] = None,
        source_id: str = "csv",
        confidence: float = 1.0,
    ) -> str:
        context_id = str(uuid.uuid4())
        ts = timestamp or datetime.utcnow()
        meta = metadata or {}
        cd = ContextData(
            payload=payload,
            timestamp=ts,
            source_id=source_id,
            confidence=confidence,
            metadata=meta,
            roles=meta.get("roles", []),
            situations=meta.get("situations", []),
            content=meta.get("content", ""),
        )
        self._write_row(
            {
                "id": context_id,
                "timestamp": ts.isoformat(),
                "source_id": source_id,
                "confidence": confidence,
                "metadata": json.dumps(meta),
                "data": json.dumps(payload),
            }
        )
        super().publish_context(cd)
        return context_id

    def fetch_context(self, query_params: ContextQuery) -> List[ContextData]:
        rows = self._read_rows()
        results: List[ContextData] = []
        for row in rows:
            try:
                ts = datetime.fromisoformat(row["timestamp"])
            except Exception:
                continue
            if query_params.time_range[0] <= ts <= query_params.time_range[1]:
                metadata = json.loads(row.get("metadata", "{}"))
                payload = json.loads(row.get("data", "{}"))
                cd = ContextData(
                    payload=payload,
                    timestamp=ts,
                    source_id=row.get("source_id", "csv"),
                    confidence=float(row.get("confidence", 1.0)),
                    metadata=metadata,
                    roles=metadata.get("roles", []),
                    situations=metadata.get("situations", []),
                    content=metadata.get("content", ""),
                )
                results.append(cd)
        return results

    def get_context(self, query: ContextQuery) -> List[dict]:
        raw = self.fetch_context(query)
        return [self._to_dict(cd) for cd in raw]

    def publish_context(
        self,
        payload: dict,
        timestamp: Union[datetime, None] = None,
        metadata: Union[dict, None] = None,
        source_id: str = "csv",
        confidence: float = 1.0,
    ) -> str:
        return self.ingest_context(payload, timestamp, metadata, source_id, confidence)

    def subscribe_context(self, callback: Callable[[ContextData], None]) -> SubscriptionHandle:
        return super().subscribe_context(callback)

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

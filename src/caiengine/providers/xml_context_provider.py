import os
import uuid
import json
import xml.etree.ElementTree as ET
from datetime import datetime
from typing import Callable, List, Union

from caiengine.objects.context_data import ContextData, SubscriptionHandle
from caiengine.objects.context_query import ContextQuery


class XMLContextProvider:
    """Persist context entries to a local XML file."""

    def __init__(self, file_path: str):
        self.file_path = file_path
        self.subscribers: dict[SubscriptionHandle, Callable[[ContextData], None]] = {}
        if not os.path.exists(self.file_path):
            root = ET.Element("contexts")
            tree = ET.ElementTree(root)
            tree.write(self.file_path, encoding="utf-8")

    def _load_root(self) -> ET.Element:
        tree = ET.parse(self.file_path)
        return tree.getroot()

    def _save_root(self, root: ET.Element):
        tree = ET.ElementTree(root)
        tree.write(self.file_path, encoding="utf-8")

    def ingest_context(
        self,
        payload: dict,
        timestamp: Union[datetime, None] = None,
        metadata: Union[dict, None] = None,
        source_id: str = "xml",
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
        root = self._load_root()
        entry = ET.SubElement(root, "context", id=context_id)
        ET.SubElement(entry, "timestamp").text = cd.timestamp.isoformat()
        ET.SubElement(entry, "source_id").text = cd.source_id
        ET.SubElement(entry, "confidence").text = str(cd.confidence)
        ET.SubElement(entry, "metadata").text = json.dumps(cd.metadata)
        ET.SubElement(entry, "data").text = json.dumps(payload)
        self._save_root(root)
        for cb in self.subscribers.values():
            cb(cd)
        return context_id

    def fetch_context(self, query_params: ContextQuery) -> List[ContextData]:
        root = self._load_root()
        results: List[ContextData] = []
        for entry in root.findall("context"):
            ts = datetime.fromisoformat(entry.findtext("timestamp"))
            if query_params.time_range[0] <= ts <= query_params.time_range[1]:
                payload = json.loads(entry.findtext("data") or "{}")
                metadata = json.loads(entry.findtext("metadata") or "{}")
                cd = ContextData(
                    payload=payload,
                    timestamp=ts,
                    source_id=entry.findtext("source_id") or "xml",
                    confidence=float(entry.findtext("confidence") or 1.0),
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

    def subscribe_context(self, callback: Callable[[ContextData], None]) -> SubscriptionHandle:
        handle = uuid.uuid4()
        self.subscribers[handle] = callback
        return handle

    def publish_context(
        self,
        payload: dict,
        timestamp: Union[datetime, None] = None,
        metadata: Union[dict, None] = None,
        source_id: str = "xml",
        confidence: float = 1.0,
    ):
        self.ingest_context(payload, timestamp, metadata, source_id, confidence)

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

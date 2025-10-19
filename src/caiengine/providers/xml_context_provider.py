import json
import logging
import os
import uuid
import xml.etree.ElementTree as ET
from datetime import datetime
from typing import Callable, List, Union

from caiengine.objects.context_data import ContextData, SubscriptionHandle
from caiengine.objects.context_query import ContextQuery
from .base_context_provider import BaseContextProvider


class XMLContextProvider(BaseContextProvider):
    """Persist context entries to a local XML file."""

    def __init__(self, file_path: str):
        super().__init__()
        self.file_path = file_path
        self.logger = logging.getLogger(f"{__name__}.{self.__class__.__name__}")
        if not os.path.exists(self.file_path):
            root = ET.Element("contexts")
            tree = ET.ElementTree(root)
            tree.write(self.file_path, encoding="utf-8")
            self.logger.info("Created new XML context store", extra={"path": self.file_path})

    def _load_root(self) -> ET.Element:
        try:
            tree = ET.parse(self.file_path)
            return tree.getroot()
        except FileNotFoundError:
            self.logger.warning(
                "XML context store missing; recreating", extra={"path": self.file_path}
            )
            root = ET.Element("contexts")
            self._save_root(root)
            return root
        except ET.ParseError:
            self.logger.error(
                "Failed to parse XML context store; returning empty root",
                extra={"path": self.file_path},
            )
            root = ET.Element("contexts")
            self._save_root(root)
            return root

    def _save_root(self, root: ET.Element):
        try:
            tree = ET.ElementTree(root)
            tree.write(self.file_path, encoding="utf-8")
        except OSError:
            self.logger.exception(
                "Failed to write XML context store", extra={"path": self.file_path}
            )
            raise

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
        self.logger.info(
            "Context entry ingested into XML store",
            extra={"path": self.file_path, "entry_id": context_id},
        )
        super().publish_context(cd)
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
        self.logger.debug(
            "Fetched XML context entries",
            extra={"count": len(results), "path": self.file_path},
        )
        return results

    def get_context(self, query: ContextQuery) -> List[dict]:
        raw = self.fetch_context(query)
        return [self._to_dict(cd) for cd in raw]

    def subscribe_context(self, callback: Callable[[ContextData], None]) -> SubscriptionHandle:
        return super().subscribe_context(callback)

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

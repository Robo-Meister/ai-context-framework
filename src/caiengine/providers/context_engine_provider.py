import json
from datetime import datetime
from typing import Dict, List, Tuple, Union, Optional

from caiengine.objects.context_data import ContextData
from caiengine.objects.context_query import ContextQuery
from .base_context_provider import BaseContextProvider


class ContextEngineProvider(BaseContextProvider):
    """Provider that understands hierarchical context keys stored in Redis."""

    def __init__(self, redis_client, key_prefix: str = "Context"):
        super().__init__()
        self.redis = redis_client
        self.key_prefix = key_prefix
        self.links: Dict[Tuple[str, str], str] = {}

    # ------------------------------------------------------------------
    def register_link(self, source_scope: str, field: str, target_scope: str) -> None:
        self.links[(source_scope, field)] = target_scope

    # ------------------------------------------------------------------
    def ingest_context(
        self,
        scope: str,
        entity_id: str,
        field: str,
        value: Union[str, int, float],
        timestamp: Optional[datetime] = None,
        metadata: Optional[dict] = None,
        source_id: str = "context_engine",
        confidence: float = 1.0,
    ) -> str:
        ts = timestamp or datetime.utcnow()
        payload = {
            "value": value,
            "timestamp": ts.isoformat(),
            "metadata": metadata or {},
            "source_id": source_id,
            "confidence": confidence,
        }
        key = f"{self.key_prefix}:{scope}:{entity_id}:{field}"
        self.redis.set(key, json.dumps(payload))
        cd = ContextData(
            payload={field: value},
            timestamp=ts,
            source_id=source_id,
            confidence=confidence,
            metadata=metadata or {},
            roles=(metadata or {}).get("roles", []),
            situations=(metadata or {}).get("situations", []),
            content=(metadata or {}).get("content", ""),
        )
        super().publish_context(cd)
        return key

    # ------------------------------------------------------------------
    def _gather(self, scope: str, entity_id: str, visited: Optional[set] = None) -> List[dict]:
        if visited is None:
            visited = set()
        if (scope, entity_id) in visited:
            return []
        visited.add((scope, entity_id))

        pattern = f"{self.key_prefix}:{scope}:{entity_id}:"
        result = []
        for key in self.redis.keys(pattern + "*"):
            field = key.split(":")[-1]
            try:
                data = json.loads(self.redis.get(key))
            except Exception:
                continue
            try:
                ts = datetime.fromisoformat(data.get("timestamp"))
            except Exception:
                ts = datetime.utcnow()
            entry = {
                "field": field,
                "value": data.get("value"),
                "timestamp": ts,
                "metadata": data.get("metadata", {}),
                "source_id": data.get("source_id", "context_engine"),
                "confidence": float(data.get("confidence", 1.0)),
            }
            result.append(entry)
            link_scope = self.links.get((scope, field))
            if link_scope:
                nested_id = str(entry["value"])
                result.extend(self._gather(link_scope, nested_id, visited))
        return result

    # ------------------------------------------------------------------
    def fetch_context(self, query_params: ContextQuery) -> List[ContextData]:
        if ":" not in query_params.scope:
            return []
        scope, entity_id = query_params.scope.split(":", 1)
        entries = self._gather(scope, entity_id)
        results: List[ContextData] = []
        for e in entries:
            if query_params.time_range[0] <= e["timestamp"] <= query_params.time_range[1]:
                meta = e.get("metadata", {})
                cd = ContextData(
                    payload={e["field"]: e["value"]},
                    timestamp=e["timestamp"],
                    source_id=e.get("source_id", "context_engine"),
                    confidence=e.get("confidence", 1.0),
                    metadata=meta,
                    roles=meta.get("roles", []),
                    situations=meta.get("situations", []),
                    content=meta.get("content", ""),
                )
                results.append(cd)
        return results

    # ------------------------------------------------------------------
    def get_context(self, query: ContextQuery) -> List[dict]:
        raw = self.fetch_context(query)
        combined: Dict[str, Union[str, int, float]] = {}
        for cd in raw:
            for k, v in cd.payload.items():
                combined[k] = v
        return [{"context": combined, "timestamp": raw[-1].timestamp if raw else None}]

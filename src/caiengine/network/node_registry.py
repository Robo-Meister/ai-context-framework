"""Redis-backed registry for tracking network members by RoboID."""

from __future__ import annotations

import json
from typing import Any, Dict, List, Optional, Union

from .roboid import RoboId


class NodeRegistry:
    """Manage mesh nodes stored in a Redis hash."""

    def __init__(self, redis_client, redis_key: str = "mesh:nodes"):
        self.redis = redis_client
        self.redis_key = redis_key

    @staticmethod
    def _rid(robo_id: Union[str, RoboId]) -> str:
        return str(robo_id) if isinstance(robo_id, RoboId) else robo_id

    @staticmethod
    def _normalise_record(data: Dict[str, Any]) -> Dict[str, Any]:
        """Return a registry record with guaranteed keys and value copies."""

        address = data.get("address")
        capabilities = list(data.get("capabilities", []) or [])
        drivers = list(data.get("drivers", []) or [])
        apps = list(data.get("apps", []) or [])
        meta = dict(data.get("meta", {}) or {})
        return {
            "address": address,
            "capabilities": capabilities,
            "drivers": drivers,
            "apps": apps,
            "meta": meta,
        }

    def _decode_payload(self, payload: Any) -> Dict[str, Any]:
        if isinstance(payload, bytes):
            payload = payload.decode("utf-8")

        if isinstance(payload, str):
            try:
                data = json.loads(payload)
            except json.JSONDecodeError:
                # Backwards compatibility with registries that stored the raw
                # address string as the value.
                data = {"address": payload}
        elif isinstance(payload, dict):
            data = payload
        else:
            data = {}

        return self._normalise_record(data)

    def _write_record(self, rid: str, record: Dict[str, Any]) -> None:
        normalised = self._normalise_record(record)
        self.redis.hset(self.redis_key, rid, json.dumps(normalised))

    def join(
        self,
        robo_id: Union[str, RoboId],
        address: str,
        *,
        capabilities: Optional[List[str]] = None,
        drivers: Optional[List[str]] = None,
        apps: Optional[List[str]] = None,
        meta: Optional[Dict[str, Any]] = None,
    ) -> None:
        """Register or update a node with optional metadata."""

        rid = self._rid(robo_id)
        record = {
            "address": address,
            "capabilities": capabilities or [],
            "drivers": drivers or [],
            "apps": apps or [],
            "meta": meta or {},
        }
        self._write_record(rid, record)

    def leave(self, robo_id: Union[str, RoboId]) -> None:
        """Remove a node from the registry."""
        rid = self._rid(robo_id)
        self.redis.hdel(self.redis_key, rid)

    def get(self, robo_id: Union[str, RoboId]) -> Optional[Dict[str, Any]]:
        """Return a single node record if present."""

        rid = self._rid(robo_id)
        payload = self.redis.hget(self.redis_key, rid)
        if payload is None:
            return None
        return self._decode_payload(payload)

    def update(
        self,
        robo_id: Union[str, RoboId],
        *,
        address: Optional[str] = None,
        capabilities: Optional[List[str]] = None,
        drivers: Optional[List[str]] = None,
        apps: Optional[List[str]] = None,
        meta: Optional[Dict[str, Any]] = None,
    ) -> None:
        """Update fields for an existing node record."""

        rid = self._rid(robo_id)
        current = self.get(rid)
        if current is None:
            return

        if address is not None:
            current["address"] = address
        if capabilities is not None:
            current["capabilities"] = list(capabilities)
        if drivers is not None:
            current["drivers"] = list(drivers)
        if apps is not None:
            current["apps"] = list(apps)
        if meta is not None:
            current["meta"] = dict(meta)

        self._write_record(rid, current)

    def members(self) -> Dict[str, Dict[str, Any]]:
        """Return all registered nodes with their metadata."""

        raw = self.redis.hgetall(self.redis_key) or {}
        members: Dict[str, Dict[str, Any]] = {}
        for raw_key, payload in raw.items():
            key = raw_key.decode("utf-8") if isinstance(raw_key, bytes) else raw_key
            members[key] = self._decode_payload(payload)
        return members

    def find(
        self,
        *,
        node_type: Optional[str] = None,
        role: Optional[str] = None,
        place: Optional[str] = None,
        capability: Optional[str] = None,
        driver: Optional[str] = None,
        app: Optional[str] = None,
    ) -> Dict[str, Dict[str, Any]]:
        """Return nodes whose RoboID and metadata match the given filters."""

        matches: Dict[str, Dict[str, Any]] = {}
        for rid, record in self.members().items():
            try:
                parsed = RoboId.parse(rid)
            except ValueError:
                # Skip malformed entries rather than failing
                continue

            if node_type and parsed.node_type != node_type:
                continue
            if role and parsed.role != role:
                continue
            if place and parsed.place != place:
                continue
            if capability and capability not in record.get("capabilities", []):
                continue
            if driver and driver not in record.get("drivers", []):
                continue
            if app and app not in record.get("apps", []):
                continue

            matches[rid] = record
        return matches


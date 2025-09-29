"""Manage node metadata such as capabilities and installed apps."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional, Union

from .roboid import RoboId
from .node_registry import NodeRegistry


@dataclass
class NodeInfo:
    """Metadata stored for each node."""

    address: str
    capabilities: List[str] = field(default_factory=list)
    drivers: List[str] = field(default_factory=list)
    apps: List[str] = field(default_factory=list)
    metadata: Dict[str, Any] = field(default_factory=dict)


class NodeManager:
    """Track nodes and their capabilities/inventory.

    A lightweight in-memory manager that wraps :class:`NodeRegistry` for
    membership and keeps additional metadata per node. It is intended as a
    starting point for more advanced node management features.
    """

    def __init__(self, registry: NodeRegistry):
        self.registry = registry
        self._nodes: Dict[str, NodeInfo] = {}
        self._load_from_registry()

    @staticmethod
    def _rid(value: Union[str, RoboId]) -> str:
        return str(value) if isinstance(value, RoboId) else value

    def _load_from_registry(self) -> None:
        """Populate the local cache from registry contents."""

        for rid, record in self.registry.members().items():
            info = NodeInfo(
                address=record.get("address", ""),
                capabilities=list(record.get("capabilities", [])),
                drivers=list(record.get("drivers", [])),
                apps=list(record.get("apps", [])),
                metadata=dict(record.get("meta", {})),
            )
            self._nodes[rid] = info

    def register(
        self,
        robo_id: Union[str, RoboId],
        address: str,
        *,
        capabilities: Optional[List[str]] = None,
        drivers: Optional[List[str]] = None,
        apps: Optional[List[str]] = None,
        metadata: Optional[Dict[str, Any]] = None,
    ) -> None:
        """Register a node with optional capabilities and apps."""

        rid = self._rid(robo_id)
        info = NodeInfo(
            address=address,
            capabilities=list(capabilities or []),
            drivers=list(drivers or []),
            apps=list(apps or []),
            metadata=dict(metadata or {}),
        )
        self.registry.join(
            rid,
            address,
            capabilities=info.capabilities,
            drivers=info.drivers,
            apps=info.apps,
            meta=info.metadata,
        )
        self._nodes[rid] = info

    def unregister(self, robo_id: Union[str, RoboId]) -> None:
        """Remove a node from the manager and registry."""

        rid = self._rid(robo_id)
        self.registry.leave(rid)
        self._nodes.pop(rid, None)

    def get(self, robo_id: Union[str, RoboId]) -> Optional[NodeInfo]:
        """Return metadata for a node if present."""

        rid = self._rid(robo_id)
        info = self._nodes.get(rid)
        if info is not None:
            return info

        record = self.registry.get(rid)
        if record is None:
            return None

        info = NodeInfo(
            address=record.get("address", ""),
            capabilities=list(record.get("capabilities", [])),
            drivers=list(record.get("drivers", [])),
            apps=list(record.get("apps", [])),
            metadata=dict(record.get("meta", {})),
        )
        self._nodes[rid] = info
        return info

    def find_by_capability(self, capability: str) -> Dict[str, NodeInfo]:
        """Return nodes that advertise a given capability."""

        matches = self.registry.find(capability=capability)
        result: Dict[str, NodeInfo] = {}
        for rid, record in matches.items():
            info = NodeInfo(
                address=record.get("address", ""),
                capabilities=list(record.get("capabilities", [])),
                drivers=list(record.get("drivers", [])),
                apps=list(record.get("apps", [])),
                metadata=dict(record.get("meta", {})),
            )
            self._nodes[rid] = info
            result[rid] = info
        return result

    def add_app(self, robo_id: Union[str, RoboId], app_name: str) -> None:
        """Record an installed application for a node."""

        rid = self._rid(robo_id)
        info = self.get(rid)
        if info and app_name not in info.apps:
            info.apps.append(app_name)
            self.registry.update(rid, apps=info.apps)

    def has_app(self, robo_id: Union[str, RoboId], app_name: str) -> bool:
        """Check if a node reports a given application."""

        rid = self._rid(robo_id)
        info = self._nodes.get(rid)
        return bool(info and app_name in info.apps)

    def add_driver(self, robo_id: Union[str, RoboId], driver_name: str) -> None:
        """Record an installed driver for a node."""

        rid = self._rid(robo_id)
        info = self.get(rid)
        if info and driver_name not in info.drivers:
            info.drivers.append(driver_name)
            self.registry.update(rid, drivers=info.drivers)

    def has_driver(self, robo_id: Union[str, RoboId], driver_name: str) -> bool:
        """Check if a node reports a given driver."""

        rid = self._rid(robo_id)
        info = self._nodes.get(rid)
        return bool(info and driver_name in info.drivers)

    def update_inventory(
        self,
        robo_id: Union[str, RoboId],
        *,
        address: Optional[str] = None,
        capabilities: Optional[List[str]] = None,
        drivers: Optional[List[str]] = None,
        apps: Optional[List[str]] = None,
        metadata: Optional[Dict[str, Any]] = None,
    ) -> None:
        """Update cached metadata and propagate to the registry."""

        rid = self._rid(robo_id)
        info = self.get(rid)
        if info is None:
            return

        updates: Dict[str, Any] = {}
        if address is not None:
            info.address = address
            updates["address"] = address
        if capabilities is not None:
            info.capabilities = list(capabilities)
            updates["capabilities"] = info.capabilities
        if drivers is not None:
            info.drivers = list(drivers)
            updates["drivers"] = info.drivers
        if apps is not None:
            info.apps = list(apps)
            updates["apps"] = info.apps
        if metadata is not None:
            info.metadata = dict(metadata)
            updates["meta"] = info.metadata

        if updates:
            self.registry.update(rid, **updates)

    def all_nodes(self) -> Dict[str, NodeInfo]:
        """Return shallow copies of all cached node records."""

        snapshot: Dict[str, NodeInfo] = {}
        for rid, info in self._nodes.items():
            snapshot[rid] = NodeInfo(
                address=info.address,
                capabilities=list(info.capabilities),
                drivers=list(info.drivers),
                apps=list(info.apps),
                metadata=dict(info.metadata),
            )
        return snapshot

    def find_nodes(
        self,
        *,
        capabilities: Optional[List[str]] = None,
        drivers: Optional[List[str]] = None,
        apps: Optional[List[str]] = None,
    ) -> Dict[str, NodeInfo]:
        """Return nodes satisfying the given inventory requirements."""

        required_caps = set(capabilities or [])
        required_drivers = set(drivers or [])
        required_apps = set(apps or [])

        matches: Dict[str, NodeInfo] = {}
        for rid, info in self._nodes.items():
            if required_caps and not required_caps.issubset(info.capabilities):
                continue
            if required_drivers and not required_drivers.issubset(info.drivers):
                continue
            if required_apps and not required_apps.issubset(info.apps):
                continue
            matches[rid] = NodeInfo(
                address=info.address,
                capabilities=list(info.capabilities),
                drivers=list(info.drivers),
                apps=list(info.apps),
                metadata=dict(info.metadata),
            )
        return matches

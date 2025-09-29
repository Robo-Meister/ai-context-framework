"""Capability inventory registry built on top of :mod:`caiengine.network` tools."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Dict, Iterable, List, Optional, Union

from .node_manager import NodeManager, NodeInfo
from .roboid import RoboId


@dataclass
class CapabilityRecord:
    """Snapshot of a node's capability and driver inventory."""

    robo_id: str
    address: str
    capabilities: List[str] = field(default_factory=list)
    drivers: List[str] = field(default_factory=list)
    apps: List[str] = field(default_factory=list)
    metadata: Dict[str, Any] = field(default_factory=dict)


class CapabilityRegistry:
    """Thin wrapper that exposes capability focused helpers."""

    def __init__(self, node_manager: NodeManager):
        self.node_manager = node_manager

    @staticmethod
    def _rid(value: Union[str, RoboId]) -> str:
        return str(value) if isinstance(value, RoboId) else value

    @staticmethod
    def _record_from_info(rid: str, info: NodeInfo) -> CapabilityRecord:
        return CapabilityRecord(
            robo_id=rid,
            address=info.address,
            capabilities=list(info.capabilities),
            drivers=list(info.drivers),
            apps=list(info.apps),
            metadata=dict(info.metadata),
        )

    def register(
        self,
        robo_id: Union[str, RoboId],
        address: str,
        *,
        capabilities: Optional[Iterable[str]] = None,
        drivers: Optional[Iterable[str]] = None,
        apps: Optional[Iterable[str]] = None,
        metadata: Optional[Dict[str, Any]] = None,
    ) -> CapabilityRecord:
        """Register a node and immediately return its capability snapshot."""

        caps = list(capabilities or [])
        drvs = list(drivers or [])
        app_list = list(apps or [])
        self.node_manager.register(
            robo_id,
            address,
            capabilities=caps,
            drivers=drvs,
            apps=app_list,
            metadata=metadata,
        )
        record = self.get(robo_id)
        assert record is not None
        return record

    def update(
        self,
        robo_id: Union[str, RoboId],
        *,
        address: Optional[str] = None,
        capabilities: Optional[Iterable[str]] = None,
        drivers: Optional[Iterable[str]] = None,
        apps: Optional[Iterable[str]] = None,
        metadata: Optional[Dict[str, Any]] = None,
    ) -> Optional[CapabilityRecord]:
        """Update stored information and return the new snapshot if present."""

        caps = list(capabilities) if capabilities is not None else None
        drvs = list(drivers) if drivers is not None else None
        app_list = list(apps) if apps is not None else None
        self.node_manager.update_inventory(
            robo_id,
            address=address,
            capabilities=caps,
            drivers=drvs,
            apps=app_list,
            metadata=metadata,
        )
        return self.get(robo_id)

    def get(self, robo_id: Union[str, RoboId]) -> Optional[CapabilityRecord]:
        """Return a capability record for ``robo_id`` if known."""

        rid = self._rid(robo_id)
        info = self.node_manager.get(rid)
        if info is None:
            return None
        return self._record_from_info(rid, info)

    def all_nodes(self) -> Dict[str, CapabilityRecord]:
        """Return a snapshot of all nodes tracked by the registry."""

        snapshot: Dict[str, CapabilityRecord] = {}
        for rid, info in self.node_manager.all_nodes().items():
            snapshot[rid] = self._record_from_info(rid, info)
        return snapshot

    def find(
        self,
        *,
        capabilities: Optional[Iterable[str]] = None,
        drivers: Optional[Iterable[str]] = None,
        apps: Optional[Iterable[str]] = None,
    ) -> Dict[str, CapabilityRecord]:
        """Return nodes satisfying the provided capability filters."""

        caps = list(capabilities or [])
        drvs = list(drivers or [])
        app_list = list(apps or [])
        matches: Dict[str, CapabilityRecord] = {}
        for rid, info in self.node_manager.find_nodes(
            capabilities=caps,
            drivers=drvs,
            apps=app_list,
        ).items():
            matches[rid] = self._record_from_info(rid, info)
        return matches

    def has_requirements(
        self,
        robo_id: Union[str, RoboId],
        *,
        capabilities: Optional[Iterable[str]] = None,
        drivers: Optional[Iterable[str]] = None,
        apps: Optional[Iterable[str]] = None,
    ) -> bool:
        """Check if ``robo_id`` satisfies the supplied requirements."""

        record = self.get(robo_id)
        if record is None:
            return False

        cap_set = set(capabilities or [])
        driver_set = set(drivers or [])
        app_set = set(apps or [])
        if cap_set and not cap_set.issubset(record.capabilities):
            return False
        if driver_set and not driver_set.issubset(record.drivers):
            return False
        if app_set and not app_set.issubset(record.apps):
            return False
        return True

    def mark_driver_available(self, robo_id: Union[str, RoboId], driver_name: str) -> None:
        """Record that ``driver_name`` is now available on ``robo_id``."""

        self.node_manager.add_driver(robo_id, driver_name)

    def has_driver(self, robo_id: Union[str, RoboId], driver_name: str) -> bool:
        """Return ``True`` if ``driver_name`` is recorded for ``robo_id``."""

        return self.node_manager.has_driver(robo_id, driver_name)


__all__ = ["CapabilityRegistry", "CapabilityRecord"]

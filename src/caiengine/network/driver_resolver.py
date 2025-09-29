"""Utilities for resolving driver requirements before dispatching commands."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Callable, Iterable, List, Optional, Sequence, Union

from .capability_registry import CapabilityRegistry
from .roboid import RoboId

Installer = Callable[[str, str], bool]
RequestHandler = Callable[[str, Sequence[str]], None]


@dataclass
class DriverResolution:
    """Result of attempting to satisfy driver requirements for a node."""

    target: str
    satisfied: bool
    missing: List[str] = field(default_factory=list)
    installed: List[str] = field(default_factory=list)
    requested: List[str] = field(default_factory=list)

    @property
    def outstanding(self) -> List[str]:
        """Drivers still missing after attempted installation."""

        return list(self.missing)


class DriverResolver:
    """Resolve driver dependencies for nodes prior to execution."""

    def __init__(
        self,
        capability_registry: CapabilityRegistry,
        *,
        installer: Optional[Installer] = None,
        request_handler: Optional[RequestHandler] = None,
    ) -> None:
        self.registry = capability_registry
        self.installer = installer
        self.request_handler = request_handler

    @staticmethod
    def _rid(value: Union[str, RoboId]) -> str:
        return str(value) if isinstance(value, RoboId) else value

    def resolve(
        self,
        robo_id: Union[str, RoboId],
        required_drivers: Optional[Iterable[str]],
        *,
        request_missing: bool = True,
    ) -> DriverResolution:
        """Ensure ``required_drivers`` are available for ``robo_id``."""

        rid = self._rid(robo_id)
        required = [drv for drv in (required_drivers or []) if drv]
        record = self.registry.get(rid)
        if record is None:
            missing = list(dict.fromkeys(required))
            requested: List[str] = []
            if missing and request_missing and self.request_handler:
                self.request_handler(rid, missing)
                requested = list(missing)
            return DriverResolution(rid, not missing, missing=missing, requested=requested)

        available = set(record.drivers)
        missing = [drv for drv in required if drv not in available]
        installed: List[str] = []

        if missing and self.installer:
            for driver in list(missing):
                try:
                    success = bool(self.installer(rid, driver))
                except Exception:
                    success = False
                if success:
                    installed.append(driver)
                    self.registry.mark_driver_available(rid, driver)
        remaining = [drv for drv in missing if drv not in installed]

        requested: List[str] = []
        if remaining and request_missing and self.request_handler:
            self.request_handler(rid, remaining)
            requested = list(remaining)

        satisfied = not remaining
        return DriverResolution(
            rid,
            satisfied,
            missing=remaining,
            installed=installed,
            requested=requested,
        )


__all__ = ["DriverResolver", "DriverResolution"]

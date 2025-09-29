"""Utilities for recording mesh dispatch telemetry and health signals."""

from __future__ import annotations

import logging
import time
from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional

logger = logging.getLogger(__name__)


@dataclass
class DispatchEvent:
    """Represents a single dispatch outcome for monitoring purposes."""

    pack_id: str
    status: str
    target: Optional[str]
    address: Optional[str]
    attempts: List[str] = field(default_factory=list)
    timestamp: float = field(default_factory=lambda: time.time())
    latency_ms: Optional[float] = None
    error: Optional[str] = None
    metadata: Dict[str, Any] = field(default_factory=dict)


class DispatchMonitor:
    """Collects dispatch telemetry for observability dashboards."""

    def __init__(self) -> None:
        self._events: List[DispatchEvent] = []

    def record(
        self,
        *,
        pack_id: str,
        status: str,
        target: Optional[str],
        address: Optional[str],
        attempts: List[str],
        latency_ms: Optional[float] = None,
        error: Optional[str] = None,
        metadata: Optional[Dict[str, Any]] = None,
    ) -> DispatchEvent:
        event = DispatchEvent(
            pack_id=pack_id,
            status=status,
            target=target,
            address=address,
            attempts=list(attempts),
            latency_ms=latency_ms,
            error=error,
            metadata=dict(metadata or {}),
        )
        self._events.append(event)
        logger.debug("Dispatch event recorded: %s", event)
        return event

    def recent(self, limit: int = 20) -> List[DispatchEvent]:
        """Return the ``limit`` most recent dispatch events."""

        if limit <= 0:
            return []
        return self._events[-limit:]

    def failures(self) -> List[DispatchEvent]:
        """Return events corresponding to failed dispatch attempts."""

        return [event for event in self._events if event.status != "dispatched"]


__all__ = ["DispatchMonitor", "DispatchEvent"]

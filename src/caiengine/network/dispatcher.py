"""Mesh dispatcher coordinating capability lookups and driver resolution."""

from __future__ import annotations

import logging
import time
from dataclasses import dataclass, field
from typing import Any, Dict, Iterable, List, Optional, Set, Tuple

from caiengine.interfaces.network_interface import NetworkInterface

from .capability_registry import CapabilityRecord, CapabilityRegistry
from .driver_resolver import DriverResolution, DriverResolver
from .observability import DispatchMonitor

logger = logging.getLogger(__name__)


@dataclass
class DispatchOutcome:
    """Result of attempting to dispatch a command pack to the mesh."""

    status: str
    target: Optional[str]
    address: Optional[str]
    installed_drivers: List[str] = field(default_factory=list)
    missing_drivers: List[str] = field(default_factory=list)
    reason: Optional[str] = None
    attempted_targets: List[str] = field(default_factory=list)
    errors: List[str] = field(default_factory=list)
    metrics: Dict[str, Any] = field(default_factory=dict)

    @property
    def dispatched(self) -> bool:
        """Return ``True`` when the pack was sent to a remote node."""

        return self.status == "dispatched"


class MeshDispatcher:
    """Select nodes for execution and forward command packs."""

    def __init__(
        self,
        capability_registry: CapabilityRegistry,
        network: NetworkInterface,
        *,
        driver_resolver: Optional[DriverResolver] = None,
        monitor: Optional[DispatchMonitor] = None,
        retry_attempts: int = 2,
        retry_backoff: float = 0.2,
    ) -> None:
        self.registry = capability_registry
        self.network = network
        self.driver_resolver = driver_resolver or DriverResolver(capability_registry)
        self.monitor = monitor or DispatchMonitor()
        self.retry_attempts = max(1, retry_attempts)
        self.retry_backoff = max(0.0, retry_backoff)

    @staticmethod
    def _pack_identifier(pack: Dict[str, Any]) -> str:
        return str(
            pack.get("id")
            or pack.get("name")
            or pack.get("command")
            or pack.get("action")
            or "<unknown>"
        )

    def _record_monitor(
        self,
        pack_id: str,
        status: str,
        target: Optional[str],
        address: Optional[str],
        attempts: List[str],
        *,
        latency_ms: Optional[float] = None,
        reason: Optional[str] = None,
        metadata: Optional[Dict[str, Any]] = None,
    ) -> None:
        if not self.monitor:
            return
        self.monitor.record(
            pack_id=pack_id,
            status=status,
            target=target,
            address=address,
            attempts=list(attempts),
            latency_ms=latency_ms,
            error=reason,
            metadata=metadata or {},
        )

    def _send_with_retry(
        self, address: str, message: Dict[str, Any]
    ) -> Tuple[bool, Optional[float], Optional[str], int]:
        """Send a message with retry/backoff handling."""

        last_error: Optional[str] = None
        attempts = 0
        for attempt in range(1, self.retry_attempts + 1):
            attempts = attempt
            start = time.monotonic()
            try:
                self.network.send(address, message)
                latency_ms = (time.monotonic() - start) * 1000.0
                return True, latency_ms, None, attempts
            except Exception as exc:  # pragma: no cover - depends on network impl
                last_error = str(exc)
                logger.warning(
                    "Dispatch send attempt %s to %s failed: %s",
                    attempt,
                    address,
                    last_error,
                )
                if attempt < self.retry_attempts and self.retry_backoff > 0:
                    time.sleep(self.retry_backoff * attempt)
        return False, None, last_error, attempts

    @staticmethod
    def _normalise_requirements(requirements: Optional[Dict[str, Iterable[str]]]) -> Dict[str, List[str]]:
        req = requirements or {}
        return {
            "capabilities": list(req.get("capabilities", [])),
            "drivers": list(req.get("drivers", [])),
            "apps": list(req.get("apps", [])),
        }

    def _candidate_records(self, requirements: Dict[str, List[str]]) -> List[CapabilityRecord]:
        """Return candidate nodes ordered by preference."""

        caps = requirements["capabilities"]
        drivers = requirements["drivers"]
        apps = requirements["apps"]

        exact_matches = self.registry.find(capabilities=caps, drivers=drivers, apps=apps)
        fallback_matches = self.registry.find(capabilities=caps, apps=apps)

        ordered: List[CapabilityRecord] = []
        seen: Set[str] = set()
        for mapping in (exact_matches, fallback_matches):
            for rid, record in mapping.items():
                if rid in seen:
                    continue
                ordered.append(record)
                seen.add(rid)
        return ordered

    def dispatch(
        self,
        pack: Dict[str, Any],
        *,
        origin: Optional[str] = None,
        requirements: Optional[Dict[str, Iterable[str]]] = None,
    ) -> DispatchOutcome:
        """Dispatch ``pack`` to an eligible node if available."""

        req = self._normalise_requirements(requirements or pack.get("requirements"))
        candidates = self._candidate_records(req)
        pack_id = self._pack_identifier(pack)
        if not candidates:
            outcome = DispatchOutcome(
                status="no_candidates",
                target=None,
                address=None,
                reason="No nodes match requested capabilities",
            )
            self._record_monitor(
                pack_id,
                outcome.status,
                outcome.target,
                outcome.address,
                outcome.attempted_targets,
                reason=outcome.reason,
            )
            return outcome

        attempts: List[str] = []
        errors: List[str] = []
        best_failure: Optional[Dict[str, Any]] = None
        start_time = time.monotonic()

        for candidate in candidates:
            attempts.append(candidate.robo_id)
            resolution: DriverResolution = self.driver_resolver.resolve(
                candidate.robo_id,
                req.get("drivers"),
            )
            if resolution.satisfied:
                message = {
                    "pack": pack,
                    "origin": origin,
                    "target": candidate.robo_id,
                    "requirements": req,
                }
                # Use the recorded network address as the recipient id.
                success, send_latency, error_message, network_attempts = self._send_with_retry(
                    candidate.address, message
                )
                if success:
                    total_latency = (time.monotonic() - start_time) * 1000.0
                    outcome = DispatchOutcome(
                        status="dispatched",
                        target=candidate.robo_id,
                        address=candidate.address,
                        installed_drivers=resolution.installed,
                        attempted_targets=list(attempts),
                        errors=list(errors),
                        metrics={
                            "latency_ms": total_latency,
                            "network_attempts": network_attempts,
                            "drivers_installed": list(resolution.installed),
                        },
                    )
                    self._record_monitor(
                        pack_id,
                        outcome.status,
                        outcome.target,
                        outcome.address,
                        outcome.attempted_targets,
                        latency_ms=total_latency,
                        metadata=outcome.metrics,
                    )
                    return outcome

                reason = error_message or "Network send failed"
                errors.append(f"{candidate.robo_id}:{reason}")
                self._record_monitor(
                    pack_id,
                    "delivery_failed",
                    candidate.robo_id,
                    candidate.address,
                    list(attempts),
                    reason=reason,
                    metadata={
                        "network_attempts": network_attempts,
                        "drivers_installed": list(resolution.installed),
                    },
                )
                continue

            failure_payload = {
                "candidate": candidate,
                "resolution": resolution,
                "attempts": list(attempts),
            }
            if best_failure is None:
                best_failure = failure_payload
            else:
                current_missing = len(best_failure["resolution"].missing)
                new_missing = len(resolution.missing)
                if new_missing < current_missing:
                    best_failure = failure_payload

        if best_failure is not None:
            candidate = best_failure["candidate"]
            resolution = best_failure["resolution"]
            outcome = DispatchOutcome(
                status="drivers_missing",
                target=candidate.robo_id,
                address=candidate.address,
                installed_drivers=resolution.installed,
                missing_drivers=resolution.missing,
                reason="Driver requirements not satisfied",
                attempted_targets=best_failure["attempts"],
                errors=list(errors),
                metrics={
                    "drivers_missing": list(resolution.missing),
                    "drivers_installed": list(resolution.installed),
                },
            )
            self._record_monitor(
                pack_id,
                outcome.status,
                outcome.target,
                outcome.address,
                outcome.attempted_targets,
                reason=outcome.reason,
                metadata=outcome.metrics,
            )
            return outcome

        outcome = DispatchOutcome(
            status="delivery_failed",
            target=None,
            address=None,
            reason="All candidate routes failed",
            attempted_targets=attempts,
            errors=list(errors),
        )
        self._record_monitor(
            pack_id,
            outcome.status,
            outcome.target,
            outcome.address,
            outcome.attempted_targets,
            reason=outcome.reason,
            metadata={"errors": list(errors)},
        )
        return outcome


__all__ = ["MeshDispatcher", "DispatchOutcome"]

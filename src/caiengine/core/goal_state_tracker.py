from __future__ import annotations

import logging
import threading
from copy import deepcopy
from typing import Any, Dict, Protocol


logger = logging.getLogger(__name__)


class GoalStateBackend(Protocol):
    """Protocol describing a persistence backend for goal state."""

    def load(self) -> Dict[str, Any]:
        """Return the current goal state."""

    def save(self, state: Dict[str, Any]) -> None:
        """Persist ``state``."""


class _InMemoryGoalStateBackend:
    """Fallback backend that keeps state in memory only."""

    def __init__(self) -> None:
        self._state: Dict[str, Any] = {}
        self._lock = threading.RLock()

    def load(self) -> Dict[str, Any]:
        with self._lock:
            return deepcopy(self._state)

    def save(self, state: Dict[str, Any]) -> None:
        with self._lock:
            self._state = deepcopy(state)


class GoalStateTracker:
    """Persist and retrieve goal feedback loop state.

    This is a placeholder for more robust storage such as a database or
    distributed cache.
    """

    def __init__(self, backend: GoalStateBackend | None = None) -> None:
        self._backend: GoalStateBackend = backend or _InMemoryGoalStateBackend()
        self._lock = threading.RLock()
        if backend is None:
            logger.warning(
                "GoalStateTracker defaulting to in-memory storage; state will reset on restart",
                extra={"backend": "memory"},
            )

    def load(self) -> Dict[str, Any]:
        """Return the last known goal state and progress metrics."""
        with self._lock:
            state = self._backend.load()
        logger.debug(
            "Loaded goal state",
            extra={"keys": sorted(state.keys())},
        )
        return deepcopy(state)

    def save(self, state: Dict[str, Any]) -> None:
        """Persist updated goal state."""
        if not isinstance(state, dict):
            raise TypeError("Goal state must be a dictionary")
        snapshot = deepcopy(state)
        with self._lock:
            self._backend.save(snapshot)
        logger.info(
            "Persisted goal state",
            extra={"keys": sorted(snapshot.keys()), "size": len(snapshot)},
        )

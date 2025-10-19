from __future__ import annotations

import logging
from typing import Any, Callable, Dict, Optional


class GoalStateTracker:
    """Persist and retrieve goal feedback loop state.

    This is a placeholder for more robust storage such as a database or
    distributed cache.
    """

    def __init__(
        self,
        loader: Optional[Callable[[], Dict[str, Any]]] = None,
        saver: Optional[Callable[[Dict[str, Any]], None]] = None,
    ) -> None:
        self.logger = logging.getLogger(f"{__name__}.{self.__class__.__name__}")
        self._loader = loader
        self._saver = saver
        self._state: Dict[str, Any] = {}

        if self._loader:
            try:
                loaded = self._loader() or {}
                if not isinstance(loaded, dict):
                    raise TypeError("Loader must return a mapping")
                self._state.update(loaded)
                self.logger.info(
                    "Loaded goal state from persistence backend",
                    extra={"keys": list(self._state.keys())},
                )
            except Exception:
                self.logger.exception(
                    "Failed to load goal state from persistence backend; using in-memory store"
                )
        else:
            self.logger.warning(
                "Using in-memory goal state store; provide loader/saver for durability"
            )

    def load(self) -> Dict[str, Any]:
        """Return the last known goal state and progress metrics."""
        return dict(self._state)

    def save(self, state: Dict[str, Any]) -> None:
        """Persist updated goal state."""
        self._state = dict(state)
        if self._saver is None:
            self.logger.debug("Goal state saved in memory only", extra={"keys": list(self._state.keys())})
            return
        try:
            self._saver(self._state)
        except Exception:
            self.logger.exception("Failed to persist goal state; retaining in-memory copy")

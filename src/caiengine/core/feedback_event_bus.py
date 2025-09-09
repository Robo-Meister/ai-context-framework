from __future__ import annotations

from typing import Any, Callable, Dict, List


class FeedbackEventBus:
    """Simple publish/subscribe bus for goal feedback events."""

    def __init__(self) -> None:
        self._subscribers: List[Callable[[Dict[str, Any]], None]] = []

    def subscribe(self, handler: Callable[[Dict[str, Any]], None]) -> None:
        """Register a callback for future events."""
        self._subscribers.append(handler)

    def publish(self, event: Dict[str, Any]) -> None:
        """Send ``event`` to all subscribers."""
        # TODO: Replace with async queue or external message broker
        for handler in list(self._subscribers):
            handler(event)

from __future__ import annotations

import logging
from typing import Any, Callable, Dict, List


class FeedbackEventBus:
    """Simple publish/subscribe bus for goal feedback events."""

    def __init__(self) -> None:
        self._subscribers: List[Callable[[Dict[str, Any]], None]] = []
        self.logger = logging.getLogger(f"{__name__}.{self.__class__.__name__}")

    def subscribe(self, handler: Callable[[Dict[str, Any]], None]) -> None:
        """Register a callback for future events."""
        self._subscribers.append(handler)
        self.logger.debug(
            "Subscriber registered", extra={"subscriber_count": len(self._subscribers)}
        )

    def publish(self, event: Dict[str, Any]) -> None:
        """Send ``event`` to all subscribers."""
        if not self._subscribers:
            self.logger.debug(
                "Published event with no subscribers",
                extra={"event_keys": list(event.keys())},
            )
            return

        self.logger.debug(
            "Dispatching event to subscribers",
            extra={"subscriber_count": len(self._subscribers), "event_keys": list(event.keys())},
        )
        for handler in list(self._subscribers):
            try:
                handler(event)
            except Exception:
                self.logger.exception(
                    "Subscriber failed to process event", extra={"event_keys": list(event.keys())}
                )

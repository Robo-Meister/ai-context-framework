from __future__ import annotations

import logging
from typing import Any, Callable, Dict, List


logger = logging.getLogger(__name__)


class FeedbackEventBus:
    """Simple publish/subscribe bus for goal feedback events."""

    def __init__(self) -> None:
        self._subscribers: List[Callable[[Dict[str, Any]], None]] = []
        self._sync_warning_emitted = False

    def subscribe(self, handler: Callable[[Dict[str, Any]], None]) -> None:
        """Register a callback for future events."""
        self._subscribers.append(handler)
        logger.debug(
            "Registered feedback event handler",
            extra={"handler": getattr(handler, "__name__", repr(handler)), "subscriber_count": len(self._subscribers)},
        )

    def publish(self, event: Dict[str, Any]) -> None:
        """Send ``event`` to all subscribers."""
        if not self._sync_warning_emitted and len(self._subscribers) > 1:
            logger.warning(
                "FeedbackEventBus is operating synchronously; consider providing an async bus for high throughput",
                extra={"subscriber_count": len(self._subscribers)},
            )
            self._sync_warning_emitted = True
        for handler in list(self._subscribers):
            try:
                handler(event)
            except Exception:
                logger.exception(
                    "Feedback event handler failed",
                    extra={
                        "handler": getattr(handler, "__name__", repr(handler)),
                        "event_keys": sorted(event.keys()),
                    },
                )

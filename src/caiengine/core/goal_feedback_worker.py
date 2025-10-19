from __future__ import annotations

import logging
import threading
import time
from typing import Callable, Dict, Iterable, List, Optional

from .goal_feedback_loop import GoalDrivenFeedbackLoop
from .goal_state_tracker import GoalStateTracker
from .feedback_event_bus import FeedbackEventBus


class GoalFeedbackWorker:
    """Background worker that keeps the goal feedback loop running.

    This scaffold wires the loop to an event bus and a simple state tracker.
    """

    def __init__(
        self,
        loop: GoalDrivenFeedbackLoop,
        event_bus: FeedbackEventBus,
        state_tracker: GoalStateTracker | None = None,
        poll_interval: float = 5.0,
        poll_callback: Optional[Callable[[], Iterable[Dict]]] = None,
    ) -> None:
        self.loop = loop
        self.event_bus = event_bus
        self.state_tracker = state_tracker or GoalStateTracker()
        self.poll_interval = poll_interval
        self.poll_callback = poll_callback
        self._thread: Optional[threading.Thread] = None
        self._stop = threading.Event()
        self._idle_notice_logged = False
        self.logger = logging.getLogger(f"{__name__}.{self.__class__.__name__}")
        self.event_bus.subscribe(self._handle_event)
        self.logger.debug("Goal feedback worker initialised", extra={"poll_interval": poll_interval})

    def start(self) -> None:
        """Start the background thread."""
        if self._thread and self._thread.is_alive():
            self.logger.debug("Background thread already running; start skipped")
            return
        self._thread = threading.Thread(target=self._run, daemon=True)
        self._thread.start()
        self.logger.info("Goal feedback worker started", extra={"poll_interval": self.poll_interval})

    def stop(self) -> None:
        """Signal the worker to terminate."""
        self._stop.set()
        if self._thread:
            self._thread.join()
        self.logger.info("Goal feedback worker stopped")

    def _handle_event(self, event: Dict) -> None:
        """React to new actions or goal changes."""
        event_type = event.get("type", "unknown")
        self.logger.info(
            "Received feedback event",
            extra={
                "event_type": event_type,
                "event_keys": sorted(event.keys()),
            },
        )

        try:
            current_state = self.state_tracker.load()
            if "goal_state" in event:
                goal_state = event["goal_state"]
                if isinstance(goal_state, dict):
                    self.loop.set_goal_state(goal_state)
                    current_state["goal_state"] = goal_state
                    self.logger.debug(
                        "Updated goal state from event",
                        extra={"event_type": event_type, "goal_keys": list(goal_state.keys())},
                    )
                else:
                    self.logger.warning(
                        "Goal state payload must be a mapping; ignoring",
                        extra={"event_type": event_type},
                    )

            history: List[Dict] = current_state.get("history", [])
            history_override = event.get("history")
            if isinstance(history_override, list):
                history = history_override

            actions: List[Dict] = event.get("actions", [])
            if actions:
                suggestions = self.loop.suggest(history, actions)
                history = [dict(item) for item in history]
                history.extend(dict(action) for action in actions)
                current_state["history"] = history
                current_state["suggestions"] = suggestions
                self.logger.info(
                    "Processed actions through feedback loop",
                    extra={
                        "event_type": event_type,
                        "actions_processed": len(actions),
                        "suggestions_generated": len(suggestions),
                    },
                )
            else:
                self.logger.debug(
                    "Feedback event did not include actions",
                    extra={"event_type": event_type},
                )

            self.state_tracker.save(current_state)
        except Exception:
            self.logger.exception(
                "Failed to handle feedback event", extra={"event_type": event_type}
            )

    def _run(self) -> None:
        """Main polling loop."""
        while not self._stop.is_set():
            if self.poll_callback is None:
                if not self._idle_notice_logged:
                    self.logger.debug(
                        "No poll callback configured; worker will idle between events",
                        extra={"poll_interval": self.poll_interval},
                    )
                    self._idle_notice_logged = True
                time.sleep(self.poll_interval)
                continue

            try:
                events = self.poll_callback() or []
            except Exception:
                self.logger.exception(
                    "Poll callback raised error; backing off",
                    extra={"backoff_seconds": self.poll_interval},
                )
                time.sleep(self.poll_interval)
                continue

            dispatched = 0
            for event in events:
                self._handle_event(event)
                dispatched += 1

            if dispatched == 0:
                self.logger.debug("Poll callback returned no events")
            time.sleep(self.poll_interval)

from __future__ import annotations

import asyncio
import logging
import threading
import time
from typing import Dict, List, Optional

from .goal_feedback_loop import GoalDrivenFeedbackLoop
from .goal_state_tracker import GoalStateTracker
from .feedback_event_bus import AsyncFeedbackEventBus, FeedbackEventBus


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
    ) -> None:
        self.loop = loop
        self.event_bus = event_bus
        self.state_tracker = state_tracker or GoalStateTracker()
        self.poll_interval = poll_interval
        self._thread: Optional[threading.Thread] = None
        self._stop = threading.Event()
        self._backoff_attempts = 0
        self._backoff_until = 0.0
        self._threading_warning_emitted = False
        self._poll_warning_logged = False
        self._using_async_bus = False
        self.logger = logging.getLogger(
            f"{__name__}.{self.__class__.__name__}"
        )
        self._register_event_consumer()

    def start(self) -> None:
        """Start the background thread."""
        if self._thread and self._thread.is_alive():
            self.logger.debug(
                "Goal feedback worker already running",
                extra={"thread_name": self._thread.name},
            )
            return
        if not self._threading_warning_emitted:
            self.logger.warning(
                "Starting thread-based goal feedback worker; configure an external scheduler for production workloads",
                extra={"poll_interval": self.poll_interval},
            )
            self._threading_warning_emitted = True
        self._thread = threading.Thread(target=self._run, daemon=True)
        self.logger.info(
            "Starting goal feedback worker",
            extra={"poll_interval": self.poll_interval, "thread_name": self._thread.name},
        )
        self._thread.start()

    def stop(self) -> None:
        """Signal the worker to terminate."""
        self._stop.set()
        if self._thread:
            self.logger.info(
                "Stopping goal feedback worker",
                extra={"thread_name": self._thread.name},
            )
            self._thread.join()
            self.logger.debug(
                "Goal feedback worker stopped",
                extra={"thread_name": self._thread.name},
            )

    def _handle_event(self, event: Dict) -> None:
        """React to new actions or goal changes."""
        if not isinstance(event, dict):
            self.logger.warning(
                "Ignoring non-mapping feedback event",
                extra={"received_type": type(event).__name__},
            )
            return

        state = self.state_tracker.load()
        updated = False

        goal_state = event.get("goal_state")
        if isinstance(goal_state, dict):
            self.loop.set_goal_state(goal_state)
            state["goal_state"] = goal_state
            updated = True

        history = event.get("history")
        if isinstance(history, list):
            state["history"] = history
            updated = True

        actions = event.get("actions")
        if isinstance(actions, list) and actions:
            state.setdefault("pending_actions", []).extend(actions)
            self._backoff_attempts = 0
            self._backoff_until = 0.0
            updated = True

        if updated:
            self.state_tracker.save(state)
            self.logger.info(
                "Applied feedback event",
                extra={
                    "event_type": event.get("type", "unknown"),
                    "pending_actions": len(state.get("pending_actions", [])),
                },
            )
        else:
            self.logger.debug(
                "Feedback event produced no changes",
                extra={"event_keys": sorted(event.keys())},
            )

    def _run(self) -> None:
        """Main polling loop."""
        while not self._stop.is_set():
            try:
                self._process_pending_actions()
            except Exception:
                self.logger.exception("Unexpected failure while processing feedback actions")
            if not self._poll_warning_logged:
                self.logger.debug(
                    "No external pollers configured; sleeping",
                    extra={"poll_interval": self.poll_interval},
                )
                self._poll_warning_logged = True
            self._stop.wait(self.poll_interval)

    # ------------------------------------------------------------------
    # Internal helpers
    # ------------------------------------------------------------------
    def _process_pending_actions(self) -> None:
        """Process queued actions if backoff allows."""

        now = time.monotonic()
        if now < self._backoff_until:
            remaining = max(self._backoff_until - now, 0.0)
            self.logger.debug(
                "Deferring feedback processing due to backoff",
                extra={"backoff_remaining": round(remaining, 3)},
            )
            return

        state = self.state_tracker.load()
        pending = state.get("pending_actions", [])
        history: List[Dict] = state.get("history", [])
        if not pending:
            self.logger.debug("No pending goal actions to process")
            return

        self.logger.info(
            "Processing goal feedback actions",
            extra={"pending_actions": len(pending)},
        )
        try:
            suggestions = self.loop.suggest(history, pending)
        except Exception:
            self._backoff_attempts += 1
            delay = min(self.poll_interval * (2 ** (self._backoff_attempts - 1)), 300)
            self._backoff_until = time.monotonic() + delay
            self.logger.error(
                "Goal feedback loop failed to process actions",
                exc_info=True,
                extra={
                    "pending_actions": len(pending),
                    "backoff_seconds": round(delay, 3),
                    "attempt": self._backoff_attempts,
                },
            )
            return

        state["pending_actions"] = []
        state["suggestions"] = suggestions
        state["history"] = history + pending
        self._backoff_attempts = 0
        self._backoff_until = 0.0
        self.state_tracker.save(state)
        self.logger.info(
            "Generated goal feedback suggestions",
            extra={"suggestion_count": len(suggestions)},
        )

    # ------------------------------------------------------------------
    # Event bus helpers
    # ------------------------------------------------------------------
    def _register_event_consumer(self) -> None:
        """Subscribe to the configured event bus."""

        if isinstance(self.event_bus, AsyncFeedbackEventBus):
            loop = self._maybe_get_running_loop()
            self._using_async_bus = self.event_bus.add_background_consumer(
                self._handle_event,
                loop=loop,
            )
            if self._using_async_bus:
                worker_count = len(getattr(self.event_bus, "_workers", []))
                self.logger.debug(
                    "Registered async feedback event consumer",
                    extra={"worker_tasks": worker_count},
                )
            else:
                self.logger.debug(
                    "Async event bus unavailable; falling back to synchronous dispatch",
                )
            return
        self.event_bus.subscribe(self._handle_event)

    @staticmethod
    def _maybe_get_running_loop() -> asyncio.AbstractEventLoop | None:
        try:
            return asyncio.get_running_loop()
        except RuntimeError:
            return None

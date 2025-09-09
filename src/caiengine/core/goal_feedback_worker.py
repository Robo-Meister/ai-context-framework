from __future__ import annotations

import threading
import time
from typing import Dict, List, Optional

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
    ) -> None:
        self.loop = loop
        self.event_bus = event_bus
        self.state_tracker = state_tracker or GoalStateTracker()
        self.poll_interval = poll_interval
        self._thread: Optional[threading.Thread] = None
        self._stop = threading.Event()
        self.event_bus.subscribe(self._handle_event)

    def start(self) -> None:
        """Start the background thread."""
        # TODO: Consider using asyncio or external worker system
        if self._thread and self._thread.is_alive():
            return
        self._thread = threading.Thread(target=self._run, daemon=True)
        self._thread.start()

    def stop(self) -> None:
        """Signal the worker to terminate."""
        self._stop.set()
        if self._thread:
            self._thread.join()

    def _handle_event(self, event: Dict) -> None:
        """React to new actions or goal changes."""
        # TODO: Feed actions to loop and persist results
        pass

    def _run(self) -> None:
        """Main polling loop."""
        history: List[Dict] = []
        while not self._stop.is_set():
            # TODO: Poll external sources for new actions
            time.sleep(self.poll_interval)

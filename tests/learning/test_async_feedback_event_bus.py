from __future__ import annotations

import asyncio
import time
from typing import Dict, List

from caiengine.core.feedback_event_bus import AsyncFeedbackEventBus
from caiengine.core.goal_feedback_worker import GoalFeedbackWorker
from caiengine.core.goal_state_tracker import GoalStateTracker


def test_async_feedback_event_bus_dispatches_without_blocking() -> None:
    async def runner() -> None:
        bus = AsyncFeedbackEventBus(loop=asyncio.get_running_loop())

        processed = asyncio.Event()
        call_order: List[int] = []

        async def handler(event: Dict[str, int]) -> None:
            await asyncio.sleep(0.01)
            call_order.append(event["value"])
            processed.set()

        assert bus.add_background_consumer(handler)

        start = time.perf_counter()
        bus.publish({"value": 1})
        publish_elapsed = time.perf_counter() - start

        # Publishing should return immediately even though the handler sleeps.
        assert publish_elapsed < 0.05
        assert not processed.is_set()

        await asyncio.wait_for(processed.wait(), timeout=1)
        await bus.join()
        await bus.aclose()

        assert call_order == [1]

    asyncio.run(runner())


class _FailingFeedbackLoop:
    def __init__(self) -> None:
        self.goal_state: Dict[str, int] = {}
        self.suggest_calls = 0

    def set_goal_state(self, goal_state: Dict[str, int]) -> None:
        self.goal_state = goal_state

    def suggest(self, history: List[Dict[str, int]], actions: List[Dict[str, int]]) -> List[Dict[str, int]]:
        self.suggest_calls += 1
        raise RuntimeError("loop failure")


def test_goal_feedback_worker_backoff_survives_async_bus() -> None:
    async def runner() -> None:
        event_loop = asyncio.get_running_loop()
        bus = AsyncFeedbackEventBus(loop=event_loop)
        tracker = GoalStateTracker()
        feedback_loop = _FailingFeedbackLoop()
        worker = GoalFeedbackWorker(feedback_loop, bus, tracker, poll_interval=0.01)

        assert worker._using_async_bus

        bus.publish(
            {
                "goal_state": {"progress": 1},
                "actions": [{"progress": 1}],
                "history": [],
            }
        )
        await asyncio.wait_for(bus.join(), timeout=1)

        state = tracker.load()
        assert state["goal_state"] == {"progress": 1}
        assert state["pending_actions"] == [{"progress": 1}]

        # First processing attempt should back off after failure.
        await event_loop.run_in_executor(None, worker._process_pending_actions)
        assert feedback_loop.suggest_calls == 1
        assert worker._backoff_attempts == 1
        remaining_backoff = max(worker._backoff_until - time.monotonic(), 0.0)
        assert remaining_backoff > 0

        # Subsequent processing should honour backoff and avoid another suggest() call.
        await event_loop.run_in_executor(None, worker._process_pending_actions)
        assert feedback_loop.suggest_calls == 1

        await bus.aclose()

    asyncio.run(runner())

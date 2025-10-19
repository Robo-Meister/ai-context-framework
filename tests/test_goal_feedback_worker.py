import unittest
from typing import Dict, List

from caiengine.core.feedback_event_bus import FeedbackEventBus
from caiengine.core.goal_feedback_worker import GoalFeedbackWorker
from caiengine.core.goal_state_tracker import GoalStateTracker


class DummyLoop:
    def __init__(self) -> None:
        self.goal_state: Dict[str, int] = {}
        self.suggest_calls: List = []

    def set_goal_state(self, goal_state: Dict) -> None:
        self.goal_state = goal_state

    def suggest(self, history: List[Dict], actions: List[Dict]) -> List[Dict]:
        self.suggest_calls.append((history, actions))
        return [{"processed": len(actions)}]


class FailingLoop(DummyLoop):
    def suggest(self, history: List[Dict], actions: List[Dict]) -> List[Dict]:
        raise RuntimeError("boom")


class GoalFeedbackWorkerTests(unittest.TestCase):
    def test_handle_event_persists_state(self):
        loop = DummyLoop()
        tracker = GoalStateTracker()
        bus = FeedbackEventBus()
        worker = GoalFeedbackWorker(loop, bus, tracker)

        event = {
            "type": "actions",
            "goal_state": {"metric": 42},
            "history": [{"metric": 21}],
            "actions": [{"metric": 42}],
        }

        worker._handle_event(event)

        state = tracker.load()
        self.assertEqual(state["goal_state"], {"metric": 42})
        self.assertEqual(len(state["history"]), 2)
        self.assertEqual(state["history"][0]["metric"], 21)
        self.assertEqual(state["suggestions"], [{"processed": 1}])
        self.assertEqual(loop.goal_state, {"metric": 42})

    def test_handle_event_logs_failures(self):
        loop = FailingLoop()
        tracker = GoalStateTracker()
        bus = FeedbackEventBus()
        worker = GoalFeedbackWorker(loop, bus, tracker)

        with self.assertLogs(worker.logger.name, level="ERROR") as cm:
            worker._handle_event({"type": "failing", "actions": [{"value": 1}]})

        self.assertTrue(
            any("Failed to handle feedback event" in entry for entry in cm.output),
            cm.output,
        )


if __name__ == "__main__":
    unittest.main()

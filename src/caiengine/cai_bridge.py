from __future__ import annotations

from typing import List, Dict, Optional

from caiengine.core.goal_feedback_loop import GoalDrivenFeedbackLoop
from caiengine.core.goal_strategies import (
    SimpleGoalFeedbackStrategy,
    PersonalityGoalFeedbackStrategy,
)


class CAIBridge:
    """Simple bridge for running goal feedback with optional NPC personalities."""

    def __init__(
        self,
        goal_state: Optional[Dict] = None,
        personality: Optional[str] = None,
        one_direction_layers: Optional[List[str]] | None = None,
    ) -> None:
        self.goal_state = goal_state or {}
        strategy = None
        if personality:
            strategy = PersonalityGoalFeedbackStrategy(
                personality=personality,
                one_direction_layers=one_direction_layers or [],
            )
        elif one_direction_layers is not None:
            strategy = SimpleGoalFeedbackStrategy(one_direction_layers)

        self.feedback_loop = (
            GoalDrivenFeedbackLoop(strategy, goal_state=self.goal_state)
            if strategy
            else None
        )

    def suggest(self, history: List[Dict], actions: List[Dict]) -> List[Dict]:
        if self.feedback_loop:
            return self.feedback_loop.suggest(history, actions)
        return actions

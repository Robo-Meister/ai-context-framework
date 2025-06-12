from typing import List, Dict

from caiengine.interfaces.goal_feedback_strategy import GoalFeedbackStrategy


class GoalDrivenFeedbackLoop:
    """Dummy implementation of a goal-driven feedback loop."""

    def __init__(self, strategy: GoalFeedbackStrategy, goal_state: Dict | None = None):
        self.strategy = strategy
        self.goal_state = goal_state or {}

    def set_goal_state(self, goal_state: Dict):
        """Update the desired context state."""
        self.goal_state = goal_state

    def suggest(self, history: List[Dict], current_actions: List[Dict]) -> List[Dict]:
        """Return actions nudging context toward :attr:`goal_state`."""
        return self.strategy.suggest_actions(history, current_actions, self.goal_state)


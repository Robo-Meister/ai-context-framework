from typing import List, Dict


class GoalFeedbackStrategy:
    """Interface for suggesting actions toward a goal state."""

    def suggest_actions(
        self,
        history: List[Dict],
        current_actions: List[Dict],
        goal_state: Dict,
    ) -> List[Dict]:
        """Return actions adjusted toward ``goal_state``."""
        raise NotImplementedError()


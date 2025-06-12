from typing import List, Dict

from caiengine.interfaces.goal_feedback_strategy import GoalFeedbackStrategy


class SimpleGoalFeedbackStrategy(GoalFeedbackStrategy):
    """Naive strategy nudging numeric fields toward a goal state."""

    def suggest_actions(
        self,
        history: List[Dict],
        current_actions: List[Dict],
        goal_state: Dict,
    ) -> List[Dict]:
        last_context = history[-1] if history else {}
        suggestions = []
        for action in current_actions:
            updated = dict(action)
            for key, target in goal_state.items():
                if isinstance(target, (int, float)):
                    current_val = last_context.get(key, 0.0)
                    delta = target - float(current_val)
                    updated[key] = float(current_val) + delta * 0.5
            suggestions.append(updated)
        return suggestions

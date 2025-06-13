from typing import List, Dict, Iterable

from caiengine.interfaces.goal_feedback_strategy import GoalFeedbackStrategy


class SimpleGoalFeedbackStrategy(GoalFeedbackStrategy):
    """Naive strategy nudging numeric fields toward a goal state.

    Optionally supports "one-direction" layers that will never move
    backwards. This is useful for time-based fields where the goal can
    only progress forward.
    """

    def __init__(self, one_direction_layers: Iterable[str] | None = None):
        self.one_direction_layers = set(one_direction_layers or [])

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
                    current_val = float(last_context.get(key, 0.0))
                    delta = float(target) - current_val
                    if key in self.one_direction_layers and delta < 0:
                        delta = 0
                    updated[key] = current_val + delta * 0.5
            suggestions.append(updated)
        return suggestions

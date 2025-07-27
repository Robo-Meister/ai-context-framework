from typing import Iterable, List, Dict

from caiengine.interfaces.goal_feedback_strategy import GoalFeedbackStrategy

class PersonalityGoalFeedbackStrategy(GoalFeedbackStrategy):
    """Adjust suggestions based on a simple NPC personality trait."""

    PERSONALITY_FACTOR = {
        "cautious": 0.25,
        "neutral": 0.5,
        "aggressive": 0.75,
    }

    def __init__(self, personality: str = "neutral", one_direction_layers: Iterable[str] | None = None):
        self.personality = personality.lower()
        self.one_direction_layers = set(one_direction_layers or [])

    def suggest_actions(
        self,
        history: List[Dict],
        current_actions: List[Dict],
        goal_state: Dict,
    ) -> List[Dict]:
        factor = self.PERSONALITY_FACTOR.get(self.personality, 0.5)
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
                    updated[key] = current_val + delta * factor
            suggestions.append(updated)
        return suggestions

from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Dict, List, Sequence, TYPE_CHECKING

if TYPE_CHECKING:  # pragma: no cover - used only for type checking
    from caiengine.parser.conversation_parser import ConversationState


@dataclass
class CoachingTip:
    """Simple data structure returned by :class:`AdaptiveCoach`."""

    message: str
    priority: str = "normal"
    category: str = "general"

    def to_payload(self) -> Dict[str, Any]:
        return {
            "type": "coaching_tip",
            "message": self.message,
            "priority": self.priority,
            "category": self.category,
            "source": "adaptive_coach",
        }


class AdaptiveCoach:
    """Generate coaching advice from conversation state and marketing plan."""

    def __init__(
        self,
        *,
        friction_threshold: int = 2,
        unanswered_question_limit: int = 1,
        long_turn_limit: int = 6,
    ) -> None:
        self.friction_threshold = friction_threshold
        self.unanswered_question_limit = unanswered_question_limit
        self.long_turn_limit = long_turn_limit

    def generate(
        self,
        state: "ConversationState",
        marketing_plan: Sequence[Dict[str, Any]],
    ) -> List[Dict[str, Any]]:
        tips: List[CoachingTip] = []

        if state.friction >= self.friction_threshold:
            tips.append(
                CoachingTip(
                    message="Acknowledge the customer's frustration and reassure them of next steps.",
                    priority="high",
                    category="friction",
                )
            )

        if state.open_questions and len(state.open_questions) >= self.unanswered_question_limit:
            question = state.open_questions[0]
            tips.append(
                CoachingTip(
                    message=f"Address the outstanding question: '{question}'",
                    priority="high",
                    category="open_question",
                )
            )

        if state.metrics.get("customer_messages", 0) - state.metrics.get("agent_messages", 0) > 1:
            tips.append(
                CoachingTip(
                    message="Balance the conversation by responding to the customer's latest message.",
                    priority="medium",
                    category="responsiveness",
                )
            )

        if not marketing_plan:
            tips.append(
                CoachingTip(
                    message="Clarify the customer's goals before proposing actions.",
                    priority="medium",
                    category="discovery",
                )
            )
        else:
            dominant_goal = marketing_plan[0].get("goal")
            if dominant_goal == "address_churn":
                tips.append(
                    CoachingTip(
                        message="Offer retention incentives or highlight recent improvements to keep the customer engaged.",
                        priority="high",
                        category="retention",
                    )
                )
            elif dominant_goal == "qualify_lead":
                tips.append(
                    CoachingTip(
                        message="Ask about timeline, budget, and decision makers to qualify the opportunity.",
                        priority="medium",
                        category="qualification",
                    )
                )

        if state.metrics.get("total_messages", 0) >= self.long_turn_limit:
            tips.append(
                CoachingTip(
                    message="Summarise progress and confirm the agreed next step to keep momentum.",
                    priority="medium",
                    category="momentum",
                )
            )

        if state.last_customer_message:
            tips.append(
                CoachingTip(
                    message=f"Reference the customer's last message to personalise your response: '{state.last_customer_message}'.",
                    priority="low",
                    category="personalisation",
                )
            )

        return [tip.to_payload() for tip in tips]


__all__ = ["AdaptiveCoach", "CoachingTip"]

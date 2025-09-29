from __future__ import annotations

from collections import defaultdict
from dataclasses import dataclass, field
from typing import Any, Dict, Iterable, List, Optional, Sequence, Set

from caiengine.commands import COMMAND
from caiengine.interfaces.goal_feedback_strategy import GoalFeedbackStrategy
from caiengine.parser.conversation_parser import ConversationParser, ConversationState
from caiengine.core.marketing_coach import AdaptiveCoach


@dataclass(frozen=True)
class EscalationRule:
    name: str
    keywords: Sequence[str] = field(default_factory=tuple)
    goals: Sequence[str] = field(default_factory=tuple)
    escalate_after: int = 1
    actions: Sequence[Dict[str, Any]] = field(default_factory=tuple)


DEFAULT_GOAL_LIBRARY: Dict[str, Dict[str, Any]] = {
    "qualify_lead": {
        "keywords": ["budget", "timeline", "decision"],
        "actions": [
            {
                "command": COMMAND.UPDATE_CRM,
                "metadata": {"stage": "qualification"},
                "auto_execute": True,
            },
            {
                "command": COMMAND.SEND_EMAIL,
                "metadata": {
                    "template": "lead_qualification",
                },
                "auto_execute": False,
            },
        ],
        "insights": "Probe for buying intent and readiness to purchase.",
    },
    "address_churn": {
        "keywords": ["cancel", "churn", "refund", "switch"],
        "actions": [
            {
                "command": COMMAND.SEND_EMAIL,
                "metadata": {
                    "template": "churn_recovery",
                },
                "auto_execute": False,
            },
            {
                "command": COMMAND.UPDATE_CRM,
                "metadata": {"risk": "churn"},
                "auto_execute": True,
            },
        ],
        "insights": "Reassure the customer and offer retention incentives.",
    },
}


DEFAULT_ESCALATION_RULES: Sequence[EscalationRule] = (
    EscalationRule(
        name="churn_escalation",
        keywords=("cancel", "refund", "chargeback"),
        goals=("address_churn",),
        escalate_after=1,
        actions=(
            {
                "command": COMMAND.ESCALATE,
                "metadata": {"reason": "churn_risk"},
                "auto_execute": True,
            },
        ),
    ),
    EscalationRule(
        name="stalled_qualification",
        goals=("qualify_lead",),
        escalate_after=3,
        actions=(
            {
                "command": COMMAND.SCHEDULE_CALL,
                "metadata": {"priority": "high"},
                "auto_execute": True,
            },
        ),
    ),
)


class MarketingGoalFeedbackStrategy(GoalFeedbackStrategy):
    """Strategy that maps qualitative marketing goals into concrete actions."""

    def __init__(
        self,
        *,
        config: Optional[Dict[str, Any]] = None,
        session_store: Any | None = None,
        telemetry_hook: Optional[Any] = None,
        conversation_parser: Optional[ConversationParser] = None,
        coach: Optional[AdaptiveCoach] = None,
    ) -> None:
        config = config or {}
        self.goal_library: Dict[str, Dict[str, Any]] = config.get(
            "goal_library", DEFAULT_GOAL_LIBRARY
        )
        self.escalation_rules: Sequence[EscalationRule] = config.get(
            "escalation_rules", DEFAULT_ESCALATION_RULES
        )
        self.session_store = session_store
        self.telemetry_hook = telemetry_hook
        self.conversation_parser = conversation_parser or ConversationParser()
        self.coach = coach or AdaptiveCoach(
            friction_threshold=config.get("friction_threshold", 3)
        )
        self._friction_escalation_threshold = config.get(
            "friction_threshold", 3
        )

    # ------------------------------------------------------------------
    # GoalFeedbackStrategy interface
    # ------------------------------------------------------------------
    def suggest_actions(
        self,
        history: List[Dict],
        current_actions: List[Dict],
        goal_state: Dict,
    ) -> List[Dict]:
        session_id = self._resolve_session_id(goal_state)
        customer_text = self._extract_customer_text(history)
        explicit_goals = set(goal_state.get("qualitative_targets", []))
        detected_goals = self._detect_goals(customer_text, explicit_goals)

        conversation_state: ConversationState | None = None
        if self.conversation_parser:
            conversation_state = self.conversation_parser.parse(
                session_id, history
            )

        attempt_tracker: Dict[str, int] = defaultdict(int)
        if self.session_store and session_id:
            session = self.session_store.get_session(session_id)
            attempt_tracker.update(session.get("attempts", {}))

        updated_actions: List[Dict] = []
        telemetry_payload: Dict[str, Any] = {
            "session_id": session_id,
            "detected_goals": list(detected_goals),
            "escalations": [],
            "conversation_state": conversation_state.to_dict()
            if conversation_state
            else None,
        }

        for action in current_actions:
            enriched = dict(action)
            marketing_plan: List[Dict[str, Any]] = []
            escalations: List[Dict[str, Any]] = []

            for goal in detected_goals:
                attempt = self._increment_attempt(session_id, goal)
                attempt_tracker[goal] = attempt

                goal_config = self.goal_library.get(goal, {})
                plan_step = {
                    "goal": goal,
                    "insights": goal_config.get("insights"),
                    "actions": self._normalise_actions(goal_config.get("actions", [])),
                    "attempt": attempt,
                }
                marketing_plan.append(plan_step)

            escalations.extend(
                self._evaluate_escalations(
                    customer_text,
                    detected_goals,
                    attempt_tracker,
                    conversation_state,
                )
            )

            if marketing_plan:
                enriched["marketing_plan"] = marketing_plan
            if escalations:
                enriched.setdefault("commands", [])
                enriched["commands"].extend(escalations)
                telemetry_payload["escalations"].extend(escalations)
            if marketing_plan and "commands" not in enriched:
                enriched["commands"] = self._collect_commands(marketing_plan)

            if conversation_state:
                enriched.setdefault("context", {})["conversation_state"] = (
                    conversation_state.to_dict()
                )
                coaching_payload = self.coach.generate(
                    conversation_state, marketing_plan
                )
                if coaching_payload:
                    enriched["coaching"] = coaching_payload
            updated_actions.append(enriched)

        if self.telemetry_hook and (telemetry_payload["detected_goals"] or telemetry_payload["escalations"]):
            self.telemetry_hook(
                {
                    "type": "goal_feedback",
                    **telemetry_payload,
                }
            )

        return updated_actions or current_actions

    # ------------------------------------------------------------------
    # Helpers
    # ------------------------------------------------------------------
    @staticmethod
    def _resolve_session_id(goal_state: Dict[str, Any]) -> str:
        if "session_id" in goal_state:
            return str(goal_state["session_id"])
        session = goal_state.get("session", {})
        if isinstance(session, dict) and session.get("id"):
            return str(session["id"])
        return "default"

    @staticmethod
    def _extract_customer_text(history: List[Dict]) -> str:
        customer_messages = []
        for message in history:
            role = message.get("role", "").lower()
            if role in {"customer", "user", "prospect"}:
                customer_messages.append(str(message.get("content", "")))
        return " \n".join(customer_messages)

    def _detect_goals(
        self, customer_text: str, explicit_goals: Set[str]
    ) -> Set[str]:
        detected = set(explicit_goals)
        lowered = customer_text.lower()
        for goal, config in self.goal_library.items():
            if goal in detected:
                continue
            keywords: Iterable[str] = config.get("keywords", [])
            if any(keyword.lower() in lowered for keyword in keywords):
                detected.add(goal)
        return detected

    def _increment_attempt(self, session_id: str, goal: str) -> int:
        if not self.session_store:
            return 1
        return self.session_store.increment_attempt(session_id, goal)

    def _evaluate_escalations(
        self,
        customer_text: str,
        detected_goals: Set[str],
        attempts: Dict[str, int],
        conversation_state: ConversationState | None,
    ) -> List[Dict[str, Any]]:
        lowered = customer_text.lower()
        escalations: List[Dict[str, Any]] = []
        for rule in self.escalation_rules:
            keyword_triggered = any(
                keyword.lower() in lowered for keyword in rule.keywords
            )
            goal_triggered = any(goal in detected_goals for goal in rule.goals)
            if not (keyword_triggered or goal_triggered):
                continue
            if rule.goals:
                max_attempt = max(attempts.get(goal, 0) for goal in rule.goals)
            else:
                max_attempt = 0
            if max_attempt < rule.escalate_after:
                continue
            escalations.extend(self._normalise_actions(rule.actions))
        if (
            conversation_state
            and conversation_state.friction >= self._friction_escalation_threshold
        ):
            escalations.append(
                {
                    "command": COMMAND.ESCALATE,
                    "metadata": {"reason": "high_friction"},
                    "auto_execute": True,
                }
            )
        return escalations

    @staticmethod
    def _normalise_actions(actions: Iterable[Dict[str, Any]]) -> List[Dict[str, Any]]:
        normalised: List[Dict[str, Any]] = []
        for action in actions:
            if not action:
                continue
            if isinstance(action.get("command"), COMMAND):
                command_value = action["command"].value
            else:
                command_value = str(action.get("command", COMMAND.NOOP.value))
            payload = dict(action)
            payload["command"] = command_value
            normalised.append(payload)
        return normalised

    @staticmethod
    def _collect_commands(plan: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        commands: List[Dict[str, Any]] = []
        for step in plan:
            commands.extend(step.get("actions", []))
        return commands


__all__ = [
    "MarketingGoalFeedbackStrategy",
    "EscalationRule",
    "DEFAULT_GOAL_LIBRARY",
    "DEFAULT_ESCALATION_RULES",
]

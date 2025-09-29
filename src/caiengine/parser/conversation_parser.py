from __future__ import annotations

import re
from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional, Sequence, Set


_CUSTOMER_ROLES = {"customer", "user", "prospect", "lead"}
_AGENT_ROLES = {"agent", "assistant", "coach", "system"}

_POSITIVE_MARKERS = {"glad", "thanks", "great", "awesome", "perfect", "love"}
_NEGATIVE_MARKERS = {
    "angry",
    "upset",
    "frustrated",
    "cancel",
    "refund",
    "disappointed",
    "unhappy",
    "terrible",
    "issue",
    "problem",
}

_STAGE_KEYWORDS: Sequence[tuple[str, Set[str]]] = (
    ("retention", {"cancel", "refund", "churn", "switch"}),
    ("decision", {"price", "purchase", "buy", "contract", "upgrade"}),
    ("consideration", {"feature", "compare", "option", "plan", "demo"}),
    ("awareness", {"problem", "need", "looking", "interest", "help"}),
)

_INTENT_KEYWORDS: Sequence[tuple[str, Set[str]]] = (
    ("churn_risk", {"cancel", "refund", "switch"}),
    ("pricing", {"price", "cost", "budget", "quote"}),
    ("integration", {"integrate", "api", "connect", "system"}),
    ("complaint", {"issue", "problem", "broken", "bug"}),
)


@dataclass
class ConversationTurn:
    role: str
    content: str
    sentiment: str
    intents: List[str] = field(default_factory=list)
    questions: List[str] = field(default_factory=list)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "role": self.role,
            "content": self.content,
            "sentiment": self.sentiment,
            "intents": list(self.intents),
            "questions": list(self.questions),
        }


@dataclass
class ConversationState:
    session_id: str
    turns: List[ConversationTurn] = field(default_factory=list)
    stage: str = "discovery"
    sentiment: str = "neutral"
    friction: int = 0
    open_questions: List[str] = field(default_factory=list)
    metrics: Dict[str, Any] = field(default_factory=dict)
    tags: Set[str] = field(default_factory=set)
    last_customer_message: Optional[str] = None
    last_agent_message: Optional[str] = None

    def __post_init__(self) -> None:
        if not self.metrics:
            self.metrics = {
                "total_messages": 0,
                "customer_messages": 0,
                "agent_messages": 0,
                "question_count": 0,
                "negative_markers": 0,
            }

    def to_dict(self) -> Dict[str, Any]:
        return {
            "session_id": self.session_id,
            "stage": self.stage,
            "sentiment": self.sentiment,
            "friction": self.friction,
            "open_questions": list(self.open_questions),
            "metrics": dict(self.metrics),
            "tags": sorted(self.tags),
            "last_customer_message": self.last_customer_message,
            "last_agent_message": self.last_agent_message,
            "turns": [turn.to_dict() for turn in self.turns[-10:]],
        }


class ConversationParser:
    """Incrementally transform chat transcripts into stateful descriptors."""

    def __init__(self) -> None:
        self._states: Dict[str, ConversationState] = {}

    def parse(self, session_id: str, history: List[Dict[str, Any]]) -> ConversationState:
        state = self._states.setdefault(session_id, ConversationState(session_id=session_id))
        processed = len(state.turns)
        if processed > len(history):
            # History rewound; rebuild from scratch
            state = ConversationState(session_id=session_id)
            processed = 0
        for message in history[processed:]:
            turn = self._normalise_turn(message)
            state.turns.append(turn)
            state.metrics["total_messages"] += 1
            self._update_counts(state, turn)
            self._update_stage(state, turn)
            self._update_sentiment(state, turn)
            self._update_questions(state, turn)
            self._update_tags(state, turn)
        self._states[session_id] = state
        return state

    # ------------------------------------------------------------------
    # Internal helpers
    # ------------------------------------------------------------------
    @staticmethod
    def _normalise_turn(message: Dict[str, Any]) -> ConversationTurn:
        role = str(message.get("role", "unknown")).lower()
        content = str(message.get("content", "")).strip()
        sentiment = ConversationParser._analyse_sentiment(content)
        intents = ConversationParser._detect_intents(content)
        questions = ConversationParser._extract_questions(content)
        return ConversationTurn(role=role, content=content, sentiment=sentiment, intents=intents, questions=questions)

    @staticmethod
    def _analyse_sentiment(text: str) -> str:
        lowered = text.lower()
        positive_hits = sum(1 for marker in _POSITIVE_MARKERS if marker in lowered)
        negative_hits = sum(1 for marker in _NEGATIVE_MARKERS if marker in lowered)
        score = positive_hits - negative_hits
        if negative_hits and score <= 0:
            return "negative"
        if score > 0:
            return "positive"
        if score < 0:
            return "negative"
        return "neutral"

    @staticmethod
    def _detect_intents(text: str) -> List[str]:
        lowered = text.lower()
        intents = []
        for name, keywords in _INTENT_KEYWORDS:
            if any(keyword in lowered for keyword in keywords):
                intents.append(name)
        return intents

    @staticmethod
    def _extract_questions(text: str) -> List[str]:
        results = []
        for match in re.finditer(r"([^?]+\?)", text):
            question = match.group(1).strip()
            if question:
                results.append(question)
        return results

    @staticmethod
    def _keywords(text: str) -> Set[str]:
        tokens = re.findall(r"[a-zA-Z]{3,}", text.lower())
        return {token for token in tokens if len(token) > 3}

    def _update_counts(self, state: ConversationState, turn: ConversationTurn) -> None:
        if turn.role in _CUSTOMER_ROLES:
            state.metrics["customer_messages"] += 1
            state.last_customer_message = turn.content or state.last_customer_message
        elif turn.role in _AGENT_ROLES:
            state.metrics["agent_messages"] += 1
            state.last_agent_message = turn.content or state.last_agent_message
        else:
            state.metrics.setdefault("other_messages", 0)
            state.metrics["other_messages"] += 1

    def _update_stage(self, state: ConversationState, turn: ConversationTurn) -> None:
        if turn.role not in _CUSTOMER_ROLES:
            return
        lowered = turn.content.lower()
        for stage, keywords in _STAGE_KEYWORDS:
            if any(keyword in lowered for keyword in keywords):
                state.stage = stage
                return
        if state.stage == "discovery" and lowered:
            state.stage = "discovery"

    def _update_sentiment(self, state: ConversationState, turn: ConversationTurn) -> None:
        if turn.sentiment == "negative":
            state.friction += 1
            state.metrics["negative_markers"] += 1
            state.sentiment = "negative"
        elif turn.sentiment == "positive":
            state.sentiment = "positive"
        elif state.sentiment == "neutral":
            state.sentiment = turn.sentiment

    def _update_questions(self, state: ConversationState, turn: ConversationTurn) -> None:
        if turn.role in _CUSTOMER_ROLES and turn.questions:
            state.open_questions.extend(turn.questions)
            state.metrics["question_count"] += len(turn.questions)
            return
        if turn.role in _AGENT_ROLES and state.open_questions:
            current_keywords = self._keywords(turn.content)
            unresolved = []
            for question in state.open_questions:
                q_keywords = self._keywords(question)
                if q_keywords and current_keywords.intersection(q_keywords):
                    continue
                unresolved.append(question)
            state.open_questions = unresolved

    @staticmethod
    def _update_tags(state: ConversationState, turn: ConversationTurn) -> None:
        if turn.intents:
            state.tags.update(turn.intents)
        if turn.questions:
            state.tags.add("has_questions")
        if turn.sentiment == "negative":
            state.tags.add("friction")


__all__ = ["ConversationParser", "ConversationState", "ConversationTurn"]

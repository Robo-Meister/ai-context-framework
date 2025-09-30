from __future__ import annotations

import re
from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional, Sequence, Set, Tuple


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

_ENTITY_PATTERNS: Sequence[tuple[str, re.Pattern[str]]] = (
    ("email", re.compile(r"\b[\w\.-]+@[\w\.-]+\.[A-Za-z]{2,}\b")),
    ("phone", re.compile(r"\b(?:\+?\d[\d\s\-()]{7,}\d)\b")),
    (
        "money",
        re.compile(r"(?:[$£€]\s?\d+(?:,\d{3})*(?:\.\d+)?|\d+(?:\.\d+)?\s?(?:usd|dollars|bucks|eur|euro|pounds))", re.I),
    ),
    (
        "date",
        re.compile(
            r"\b(?:\d{1,2}[/-]\d{1,2}(?:[/-]\d{2,4})?|"
            r"(?:jan|feb|mar|apr|may|jun|jul|aug|sep|sept|oct|nov|dec)[a-z]*\s+\d{1,2}(?:,\s*\d{4})?)\b",
            re.I,
        ),
    ),
    ("time", re.compile(r"\b\d{1,2}:\d{2}\s?(?:am|pm)?\b|\b\d{1,2}\s?(?:am|pm)\b", re.I)),
    ("url", re.compile(r"\bhttps?://\S+")),
    ("ticket", re.compile(r"\b(?:ticket|case|incident)\s*#?\s*([A-Za-z0-9-]+)\b", re.I)),
    ("account", re.compile(r"\baccount(?: number| id)?\s*(?:is|:)?\s*([A-Za-z0-9-]+)\b", re.I)),
)

_PERSON_PATTERNS: Sequence[re.Pattern[str]] = (
    re.compile(r"\b(?:i'm|i am|this is|my name is)\s+([A-Z][a-z]+(?:\s+[A-Z][a-z]+)*)", re.I),
    re.compile(r"\b(?:call me)\s+([A-Z][a-z]+(?:\s+[A-Z][a-z]+)*)", re.I),
)

_COMPANY_PATTERNS: Sequence[re.Pattern[str]] = (
    re.compile(r"\bfrom\s+([A-Z][\w&]*(?:\s+[A-Z][\w&]*)*)", re.I),
    re.compile(r"\b(?:company|organisation|organization|team)\s*(?:is|:)?\s*([A-Z][\w&]*(?:\s+[A-Z][\w&]*)*)", re.I),
)

_TOPIC_KEYWORDS: Sequence[str] = (
    "dashboard",
    "integration",
    "portal",
    "workflow",
    "report",
    "analytics",
    "login",
    "mobile app",
    "api",
    "billing",
    "invoice",
    "contract",
)

_ISSUE_KEYWORDS: Set[str] = {
    "issue",
    "problem",
    "bug",
    "outage",
    "error",
    "crash",
    "crashes",
    "broken",
    "fail",
    "failing",
    "failure",
    "down",
    "slow",
}

_PRONOUN_PATTERN = re.compile(r"\b(it|this|that|they|them|those)\b", re.I)


@dataclass
class ConversationTurn:
    role: str
    content: str
    sentiment: str
    intents: List[str] = field(default_factory=list)
    questions: List[str] = field(default_factory=list)
    entities: Dict[str, Set[str]] = field(default_factory=dict)
    entity_mentions: List[Tuple[str, int]] = field(default_factory=list)
    slots: Dict[str, Set[str]] = field(default_factory=dict)
    references: Dict[str, str] = field(default_factory=dict)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "role": self.role,
            "content": self.content,
            "sentiment": self.sentiment,
            "intents": list(self.intents),
            "questions": list(self.questions),
            "entities": {key: sorted(values) for key, values in self.entities.items()},
            "slots": {key: sorted(values) for key, values in self.slots.items()},
            "references": dict(self.references),
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
    entities: Dict[str, Set[str]] = field(default_factory=dict)
    slots: Dict[str, Set[str]] = field(default_factory=dict)
    discourse: Dict[str, Any] = field(default_factory=dict)

    def __post_init__(self) -> None:
        if not self.metrics:
            self.metrics = {
                "total_messages": 0,
                "customer_messages": 0,
                "agent_messages": 0,
                "question_count": 0,
                "negative_markers": 0,
            }
        if not self.discourse:
            self.discourse = {
                "recent_entities": [],
                "pronoun_links": [],
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
            "entities": {key: sorted(values) for key, values in self.entities.items()},
            "slots": {key: sorted(values) for key, values in self.slots.items()},
            "discourse": {
                "recent_entities": list(self.discourse.get("recent_entities", [])),
                "pronoun_links": list(self.discourse.get("pronoun_links", [])),
            },
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
            self._update_discourse(state, turn)
            self._update_entities(state, turn)
            self._update_slots(state, turn)
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
        entities, entity_mentions = ConversationParser._extract_entities(content)
        return ConversationTurn(
            role=role,
            content=content,
            sentiment=sentiment,
            intents=intents,
            questions=questions,
            entities=entities,
            entity_mentions=entity_mentions,
        )

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
    def _extract_entities(text: str) -> Tuple[Dict[str, Set[str]], List[Tuple[str, int]]]:
        entities: Dict[str, Set[str]] = {}
        ordered: List[Tuple[int, str]] = []
        for name, pattern in _ENTITY_PATTERNS:
            for match in pattern.finditer(text):
                group_index = 1 if (match.lastindex and match.lastindex >= 1) else 0
                value = match.group(group_index).strip()
                if not value:
                    continue
                entities.setdefault(name, set()).add(value)
                ordered.append((match.start(group_index), value))
        for pattern in _PERSON_PATTERNS:
            for match in pattern.finditer(text):
                value = match.group(1).strip()
                if value:
                    entities.setdefault("person", set()).add(value)
                    ordered.append((match.start(1), value))
        for pattern in _COMPANY_PATTERNS:
            for match in pattern.finditer(text):
                value = match.group(1).strip()
                if value:
                    entities.setdefault("company", set()).add(value)
                    ordered.append((match.start(1), value))
        lowered = text.lower()
        for keyword in _TOPIC_KEYWORDS:
            if keyword in lowered:
                pattern = re.compile(
                    rf"((?:the|a|an|this|that|those|these)\s+)?((?:[A-Za-z0-9']+\s+){{0,3}}{re.escape(keyword)})",
                    re.I,
                )
                for match in pattern.finditer(text):
                    phrase = match.group(2).strip()
                    if phrase:
                        entities.setdefault("topic", set()).add(phrase)
                        ordered.append((match.start(2), phrase))
        ordered.sort(key=lambda item: item[0])
        ordered_mentions = [(value, position) for position, value in ordered]
        return entities, ordered_mentions

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
    def _update_discourse(state: ConversationState, turn: ConversationTurn) -> None:
        pronouns = list(_PRONOUN_PATTERN.finditer(turn.content))
        if not pronouns:
            return
        recent: List[str] = state.discourse.get("recent_entities", [])
        if not (recent or turn.entity_mentions):
            return
        references: Dict[str, str] = {}
        for match in pronouns:
            pronoun = match.group(1).lower()
            pronoun_position = match.start()
            resolved = None
            best_start = -1
            best_length = -1
            for value, start in turn.entity_mentions:
                if start >= pronoun_position:
                    continue
                value_length = len(value)
                if start > best_start or (start == best_start and value_length > best_length):
                    resolved = value
                    best_start = start
                    best_length = value_length
            if resolved is None and recent:
                resolved = recent[-1]
            if resolved:
                references[pronoun] = resolved
                state.discourse.setdefault("pronoun_links", []).append(
                    {
                        "turn_index": len(state.turns) - 1,
                        "pronoun": pronoun,
                        "entity": resolved,
                    }
                )
        if references:
            turn.references = references

    @staticmethod
    def _update_entities(state: ConversationState, turn: ConversationTurn) -> None:
        if not turn.entities:
            return
        recent: List[str] = state.discourse.setdefault("recent_entities", [])
        for name, values in turn.entities.items():
            store = state.entities.setdefault(name, set())
            store.update(values)
        for value, _ in turn.entity_mentions:
            if value in recent:
                recent.remove(value)
            recent.append(value)
        if len(recent) > 20:
            del recent[:-20]

    def _update_slots(self, state: ConversationState, turn: ConversationTurn) -> None:
        detected: Dict[str, Set[str]] = {}
        lowered = turn.content.lower()
        money_values = turn.entities.get("money", set())
        if money_values and any(keyword in lowered for keyword in {"price", "cost", "rate", "budget", "quote"}):
            detected["price"] = set(money_values)
        date_values = turn.entities.get("date", set())
        time_values = turn.entities.get("time", set())
        if (date_values or time_values) and any(
            keyword in lowered for keyword in {"timeline", "launch", "start", "deadline", "by", "schedule", "when"}
        ):
            detected.setdefault("timeline", set()).update(date_values)
            detected.setdefault("timeline", set()).update(time_values)
        contact_values: Set[str] = set()
        contact_values.update(turn.entities.get("email", set()))
        contact_values.update(turn.entities.get("phone", set()))
        if contact_values:
            detected["contact"] = contact_values
        account_values = turn.entities.get("account", set())
        if account_values:
            detected["account"] = set(account_values)
        ticket_values = turn.entities.get("ticket", set())
        if ticket_values:
            detected["ticket"] = set(ticket_values)
        issue_sentences: Set[str] = set()
        for sentence in re.split(r"[.!?]", turn.content):
            sentence = sentence.strip()
            if not sentence:
                continue
            lowered_sentence = sentence.lower()
            if any(keyword in lowered_sentence for keyword in _ISSUE_KEYWORDS):
                issue_sentences.add(sentence)
        if issue_sentences:
            detected["issue"] = issue_sentences
        topic_values = turn.entities.get("topic", set())
        if topic_values:
            detected.setdefault("topic", set()).update(topic_values)
        if turn.intents:
            detected.setdefault("intent", set()).update(turn.intents)
        if not detected:
            return
        turn.slots = detected
        for name, values in detected.items():
            store = state.slots.setdefault(name, set())
            store.update(values)

    @staticmethod
    def _update_tags(state: ConversationState, turn: ConversationTurn) -> None:
        if turn.intents:
            state.tags.update(turn.intents)
        if turn.questions:
            state.tags.add("has_questions")
        if turn.sentiment == "negative":
            state.tags.add("friction")


__all__ = ["ConversationParser", "ConversationState", "ConversationTurn"]

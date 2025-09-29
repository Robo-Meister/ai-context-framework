
"""Expose parsers used within the framework."""

from .log_parser import LogParser
from .robo_connector_normalizer import RoboConnectorNormalizer
from .conversation_parser import ConversationParser, ConversationState, ConversationTurn

try:  # pragma: no cover - optional dependency chain
    from .prompt_parser import PromptParser  # type: ignore
except Exception:  # pragma: no cover - surface minimal parsers when deps missing
    PromptParser = None  # type: ignore

try:  # pragma: no cover - optional dependency chain
    from .intent_classifier import IntentClassifier  # type: ignore
except Exception:  # pragma: no cover - optional when ML deps missing
    IntentClassifier = None  # type: ignore

__all__ = [
    "LogParser",
    "RoboConnectorNormalizer",
    "PromptParser",
    "IntentClassifier",
    "ConversationParser",
    "ConversationState",
    "ConversationTurn",
]

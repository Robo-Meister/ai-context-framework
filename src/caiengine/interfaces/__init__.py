
"""Interface definitions for pluggable components."""

from .context_provider import ContextProvider
from .filter_strategy import FilterStrategy
from .deduplicator_strategy import DeduplicationStrategy
from .network_interface import NetworkInterface
from .inference_engine import AIInferenceEngine, InferenceEngineInterface
from .learning_interface import LearningInterface
from .context_scorer import ContextScorer
from .goal_feedback_strategy import GoalFeedbackStrategy
from .communication_channel import CommunicationChannel

__all__ = [
    "ContextProvider",
    "FilterStrategy",
    "DeduplicationStrategy",
    "NetworkInterface",
    "InferenceEngineInterface",
    "AIInferenceEngine",
    "LearningInterface",
    "ContextScorer",
    "GoalFeedbackStrategy",
    "CommunicationChannel",
]

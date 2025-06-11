
"""Interface definitions for pluggable components."""

from .context_provider import ContextProvider
from .filter_strategy import FilterStrategy
from .deduplicator_strategy import DeduplicationStrategy
from .network_interface import NetworkInterface
from .inference_engine import AIInferenceEngine
from .learning_interface import LearningInterface
from .context_scorer import ContextScorer

__all__ = [
    "ContextProvider",
    "FilterStrategy",
    "DeduplicationStrategy",
    "NetworkInterface",
    "AIInferenceEngine",
    "LearningInterface",
    "ContextScorer",
]

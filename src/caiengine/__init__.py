__version__ = "0.1.0"

from caiengine.core import (
    CacheManager,
    ContextManager,
    DistributedContextManager,
    ContextHookManager,
    ContextHook,
    Fuser,
    PolicyEvaluator,
)
try:  # pragma: no cover - optional dependency may be missing
    from caiengine.core.ai_inference import AIInferenceEngine
except Exception:  # pragma: no cover - optional dependency may be missing
    AIInferenceEngine = None
from caiengine.pipelines import ContextPipeline, FeedbackPipeline
from caiengine.providers import MemoryContextProvider, KafkaContextProvider
from caiengine.network import NetworkManager, SimpleNetworkMock, ContextBus
from caiengine.interfaces import NetworkInterface
from caiengine.core.goal_feedback_loop import GoalDrivenFeedbackLoop
from caiengine.core.goal_strategies import SimpleGoalFeedbackStrategy
try:
    from . import cli as cli
except Exception:  # pragma: no cover - fallback when not imported as package
    import importlib
    cli = importlib.import_module("cli")

__all__ = [
    "__version__",
    "CacheManager",
    "AIInferenceEngine",
    "ContextPipeline",
    "FeedbackPipeline",
    "Fuser",
    "ContextManager",
    "DistributedContextManager",
    "ContextHookManager",
    "ContextHook",
    "MemoryContextProvider",
    "KafkaContextProvider",
    "PolicyEvaluator",
    "NetworkManager",
    "SimpleNetworkMock",
    "ContextBus",
    "NetworkInterface",
    "GoalDrivenFeedbackLoop",
    "SimpleGoalFeedbackStrategy",
    "cli",
]

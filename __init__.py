__version__ = "0.1.0"

from core import (
    CacheManager,
    ContextManager,
    DistributedContextManager,
    ContextHookManager,
    ContextHook,
    Fuser,
    PolicyEvaluator,
)
try:  # pragma: no cover - optional dependency may be missing
    from core.ai_inference import AIInferenceEngine
except Exception:  # pragma: no cover - optional dependency may be missing
    AIInferenceEngine = None
from pipelines import ContextPipeline, FeedbackPipeline
from providers import MemoryContextProvider
from network import NetworkManager, SimpleNetworkMock, ContextBus
from interfaces import NetworkInterface

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
    "PolicyEvaluator",
    "NetworkManager",
    "SimpleNetworkMock",
    "ContextBus",
    "NetworkInterface",
]

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
from providers import MemoryContextProvider, KafkaContextProvider
from network import NetworkManager, SimpleNetworkMock, ContextBus
from interfaces import NetworkInterface
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
    "cli",
]

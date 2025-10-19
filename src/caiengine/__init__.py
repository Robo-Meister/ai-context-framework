import os

__version__ = "0.2.0"

if not os.environ.get("CAIENGINE_LIGHT_IMPORT"):
    from caiengine.core import (
        CacheManager,
        ContextManager,
        DistributedContextManager,
        ContextHookManager,
        ContextHook,
        Fuser,
        PolicyEvaluator,
        export_onnx_bundle,
        load_model_manifest,
        model_manager,
    )
    try:  # pragma: no cover - optional dependency may be missing
        from caiengine.core.ai_inference import AIInferenceEngine
    except Exception:  # pragma: no cover - optional dependency may be missing
        AIInferenceEngine = None
    from caiengine.pipelines import ContextPipeline, FeedbackPipeline, QuestionPipeline, PromptPipeline, ConfigurablePipeline
    from caiengine.providers import MemoryContextProvider, KafkaContextProvider, FileModelRegistry
    from caiengine.network import (
        NetworkManager,
        SimpleNetworkMock,
        ContextBus,
        NodeRegistry,
        ModelRegistry,
        RedisPubSubChannel,
        KafkaPubSubChannel,
    )
    from caiengine.interfaces import NetworkInterface
    from caiengine.core.goal_feedback_loop import GoalDrivenFeedbackLoop
    from caiengine.core.goal_strategies import (
        SimpleGoalFeedbackStrategy,
        PersonalityGoalFeedbackStrategy,
    )
    from caiengine.core.goal_feedback_worker import GoalFeedbackWorker
    from caiengine.core.goal_state_tracker import GoalStateTracker
    from caiengine.core.feedback_event_bus import FeedbackEventBus
    from caiengine.cai_bridge import CAIBridge
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
        "QuestionPipeline",
        "PromptPipeline",
        "ConfigurablePipeline",
        "Fuser",
        "ContextManager",
        "DistributedContextManager",
        "ContextHookManager",
        "ContextHook",
        "MemoryContextProvider",
        "KafkaContextProvider",
        "PolicyEvaluator",
        "export_onnx_bundle",
        "load_model_manifest",
        "model_manager",
        "NetworkManager",
        "SimpleNetworkMock",
        "ContextBus",
        "NodeRegistry",
        "ModelRegistry",
        "RedisPubSubChannel",
        "KafkaPubSubChannel",
        "NetworkInterface",
        "GoalDrivenFeedbackLoop",
        "SimpleGoalFeedbackStrategy",
        "PersonalityGoalFeedbackStrategy",
        "GoalFeedbackWorker",
        "GoalStateTracker",
        "FeedbackEventBus",
        "CAIBridge",
        "FileModelRegistry",
        "cli",
    ]
else:  # pragma: no cover - lightweight import for CLI utilities
    try:
        from . import cli as cli
    except Exception:  # pragma: no cover
        import importlib
        cli = importlib.import_module("cli")

    __all__ = ["__version__", "cli"]

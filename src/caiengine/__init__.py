"""Top level package for :mod:`caiengine` with lazy public imports."""

from __future__ import annotations

import importlib
import os
from typing import Any, Dict, NamedTuple

__version__ = "0.2.0"

_LIGHT_IMPORT = bool(os.environ.get("CAIENGINE_LIGHT_IMPORT"))


class _ExportSpec(NamedTuple):
    module: str
    attribute: str | None = None
    extra: str | None = None


_EXPORT_ORDER = [
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
]


_EXPORT_SPECS: Dict[str, _ExportSpec] = {
    "CacheManager": _ExportSpec("caiengine.core.cache_manager", "CacheManager"),
    "AIInferenceEngine": _ExportSpec("caiengine.core.ai_inference", "AIInferenceEngine"),
    "ContextPipeline": _ExportSpec("caiengine.pipelines.context_pipeline", "ContextPipeline"),
    "FeedbackPipeline": _ExportSpec("caiengine.pipelines.feedback_pipeline", "FeedbackPipeline"),
    "QuestionPipeline": _ExportSpec("caiengine.pipelines.question_pipeline", "QuestionPipeline"),
    "PromptPipeline": _ExportSpec("caiengine.pipelines.prompt_pipeline", "PromptPipeline"),
    "ConfigurablePipeline": _ExportSpec("caiengine.pipelines.configurable_pipeline", "ConfigurablePipeline"),
    "Fuser": _ExportSpec("caiengine.core.fuser", "Fuser"),
    "ContextManager": _ExportSpec("caiengine.core.context_manager", "ContextManager"),
    "DistributedContextManager": _ExportSpec("caiengine.core.distributed_context_manager", "DistributedContextManager"),
    "ContextHookManager": _ExportSpec("caiengine.core.context_hooks", "ContextHookManager"),
    "ContextHook": _ExportSpec("caiengine.core.context_hooks", "ContextHook"),
    "MemoryContextProvider": _ExportSpec("caiengine.providers.memory_context_provider", "MemoryContextProvider"),
    "KafkaContextProvider": _ExportSpec(
        "caiengine.providers.kafka_context_provider",
        "KafkaContextProvider",
        "kafka",
    ),
    "PolicyEvaluator": _ExportSpec("caiengine.core.policy_evaluator", "PolicyEvaluator"),
    "export_onnx_bundle": _ExportSpec("caiengine.core.model_bundle", "export_onnx_bundle"),
    "load_model_manifest": _ExportSpec("caiengine.core.model_bundle", "load_model_manifest"),
    "model_manager": _ExportSpec("caiengine.core.model_manager"),
    "NetworkManager": _ExportSpec("caiengine.network.network_manager", "NetworkManager"),
    "SimpleNetworkMock": _ExportSpec("caiengine.network.simple_network", "SimpleNetworkMock"),
    "ContextBus": _ExportSpec("caiengine.network.context_bus", "ContextBus"),
    "NodeRegistry": _ExportSpec("caiengine.network.node_registry", "NodeRegistry"),
    "ModelRegistry": _ExportSpec("caiengine.network.model_registry", "ModelRegistry"),
    "RedisPubSubChannel": _ExportSpec(
        "caiengine.network.redis_pubsub_channel",
        "RedisPubSubChannel",
        "redis",
    ),
    "KafkaPubSubChannel": _ExportSpec(
        "caiengine.network.kafka_pubsub_channel",
        "KafkaPubSubChannel",
        "kafka",
    ),
    "NetworkInterface": _ExportSpec("caiengine.interfaces.network_interface", "NetworkInterface"),
    "GoalDrivenFeedbackLoop": _ExportSpec(
        "caiengine.core.goal_feedback_loop",
        "GoalDrivenFeedbackLoop",
    ),
    "SimpleGoalFeedbackStrategy": _ExportSpec(
        "caiengine.core.goal_strategies",
        "SimpleGoalFeedbackStrategy",
    ),
    "PersonalityGoalFeedbackStrategy": _ExportSpec(
        "caiengine.core.goal_strategies",
        "PersonalityGoalFeedbackStrategy",
    ),
    "GoalFeedbackWorker": _ExportSpec("caiengine.core.goal_feedback_worker", "GoalFeedbackWorker"),
    "GoalStateTracker": _ExportSpec("caiengine.core.goal_state_tracker", "GoalStateTracker"),
    "FeedbackEventBus": _ExportSpec("caiengine.core.feedback_event_bus", "FeedbackEventBus"),
    "CAIBridge": _ExportSpec("caiengine.cai_bridge", "CAIBridge"),
    "FileModelRegistry": _ExportSpec("caiengine.providers.file_model_registry", "FileModelRegistry"),
}

if _LIGHT_IMPORT:
    __all__ = ["__version__", "cli"]
else:
    __all__ = ["__version__", *_EXPORT_ORDER, "cli"]


def _load_cli() -> Any:
    try:
        return importlib.import_module(".cli", __name__)
    except Exception:  # pragma: no cover - fallback when running from source
        return importlib.import_module("cli")


def __getattr__(name: str) -> Any:  # pragma: no cover - thin wrapper
    if name == "cli":
        value = _load_cli()
        globals()[name] = value
        return value

    if _LIGHT_IMPORT:
        raise AttributeError(f"module 'caiengine' has no attribute '{name}'")

    spec = _EXPORT_SPECS.get(name)
    if spec is None:
        raise AttributeError(f"module 'caiengine' has no attribute '{name}'")

    try:
        module = importlib.import_module(spec.module)
    except ModuleNotFoundError as exc:  # pragma: no cover - optional extras
        if spec.extra:
            raise ImportError(
                f"{name} requires the optional dependency set '{spec.extra}'. "
                f"Install it with `pip install caiengine[{spec.extra}]`."
            ) from exc
        raise

    value = getattr(module, spec.attribute) if spec.attribute else module
    globals()[name] = value
    return value


def __dir__() -> list[str]:  # pragma: no cover - dynamic module attributes
    return sorted(set(__all__ + list(globals().keys())))


"""Core utilities for the AI Context Framework."""

import os
from typing import Callable

from . import model_manager


def _missing_ai_dependency(name: str, exc: ModuleNotFoundError) -> Callable:
    def _raiser(*args, **kwargs):
        raise ImportError(
            f"{name} requires the optional dependency set 'ai'. "
            "Install it with `pip install caiengine[ai]`."
        ) from exc

    return _raiser


if not os.environ.get("CAIENGINE_LIGHT_IMPORT"):
    from .cache_manager import CacheManager
    from .context_manager import ContextManager
    from .distributed_context_manager import DistributedContextManager
    from .context_hooks import ContextHookManager, ContextHook
    from .fuser import Fuser
    from .policy_evaluator import PolicyEvaluator
    from .categorizer import (
        Categorizer,
        NeuralKeywordCategorizer,
        NeuralEmbeddingCategorizer,
    )
    from .text_embeddings import (
        SimpleTextCategorizer,
        HashingTextEmbedder,
        TextEmbeddingComparer,
    )
    from .context_filer import ContextFilter
    from .trust_module import TrustModule
    from .time_decay_scorer import TimeDecayScorer
    from .ann_index import ANNIndex
    from .goal_feedback_loop import (
        GoalDrivenFeedbackLoop,
        InMemoryGoalFeedbackPersistence,
        RedisGoalFeedbackPersistence,
        SQLiteGoalFeedbackPersistence,
        create_goal_feedback_persistence,
    )
    from .goal_strategies import (
        SimpleGoalFeedbackStrategy,
        PersonalityGoalFeedbackStrategy,
    )
    from .goal_feedback_worker import GoalFeedbackWorker
    from .goal_state_tracker import (
        GoalStateTracker,
        RedisGoalStateBackend,
        SQLiteGoalStateBackend,
    )
    from .feedback_event_bus import FeedbackEventBus
    try:
        from .model_storage import save_model_with_metadata, load_model_with_metadata
    except ModuleNotFoundError as exc:
        save_model_with_metadata = _missing_ai_dependency("save_model_with_metadata", exc)
        load_model_with_metadata = _missing_ai_dependency("load_model_with_metadata", exc)

    try:
        from .model_bundle import export_onnx_bundle, load_model_manifest
    except ModuleNotFoundError as exc:
        export_onnx_bundle = _missing_ai_dependency("export_onnx_bundle", exc)
        load_model_manifest = _missing_ai_dependency("load_model_manifest", exc)

    __all__ = [
        "CacheManager",
        "ContextManager",
        "DistributedContextManager",
        "ContextHookManager",
        "ContextHook",
        "Fuser",
        "PolicyEvaluator",
        "Categorizer",
        "NeuralKeywordCategorizer",
        "NeuralEmbeddingCategorizer",
        "SimpleTextCategorizer",
        "HashingTextEmbedder",
        "TextEmbeddingComparer",
        "ContextFilter",
        "TrustModule",
        "TimeDecayScorer",
        "ANNIndex",
        "GoalDrivenFeedbackLoop",
        "InMemoryGoalFeedbackPersistence",
        "SQLiteGoalFeedbackPersistence",
        "RedisGoalFeedbackPersistence",
        "create_goal_feedback_persistence",
        "SimpleGoalFeedbackStrategy",
        "PersonalityGoalFeedbackStrategy",
        "GoalFeedbackWorker",
        "GoalStateTracker",
        "SQLiteGoalStateBackend",
        "RedisGoalStateBackend",
        "FeedbackEventBus",
        "save_model_with_metadata",
        "load_model_with_metadata",
        "export_onnx_bundle",
        "load_model_manifest",
        "model_manager",
    ]
else:  # pragma: no cover - lightweight import
    __all__ = ["model_manager"]

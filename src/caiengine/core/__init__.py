
"""Core utilities for the AI Context Framework."""

import os

from . import model_manager

if not os.environ.get("CAIENGINE_LIGHT_IMPORT"):
    from .cache_manager import CacheManager
    from .context_manager import ContextManager
    from .distributed_context_manager import DistributedContextManager
    from .context_hooks import ContextHookManager, ContextHook
    from .fuser import Fuser
    from .policy_evaluator import PolicyEvaluator
    from .categorizer import Categorizer, NeuralKeywordCategorizer
    from .context_filer import ContextFilter
    from .trust_module import TrustModule
    from .time_decay_scorer import TimeDecayScorer
    from .ann_index import ANNIndex
    from .goal_feedback_loop import GoalDrivenFeedbackLoop
    from .goal_strategies import (
        SimpleGoalFeedbackStrategy,
        PersonalityGoalFeedbackStrategy,
    )
    from .goal_feedback_worker import GoalFeedbackWorker
    from .goal_state_tracker import GoalStateTracker
    from .feedback_event_bus import FeedbackEventBus
    from .model_storage import save_model_with_metadata, load_model_with_metadata
    from .model_bundle import export_onnx_bundle, load_model_manifest

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
        "ContextFilter",
        "TrustModule",
        "TimeDecayScorer",
        "ANNIndex",
        "GoalDrivenFeedbackLoop",
        "SimpleGoalFeedbackStrategy",
        "PersonalityGoalFeedbackStrategy",
        "GoalFeedbackWorker",
        "GoalStateTracker",
        "FeedbackEventBus",
        "save_model_with_metadata",
        "load_model_with_metadata",
        "export_onnx_bundle",
        "load_model_manifest",
        "model_manager",
    ]
else:  # pragma: no cover - lightweight import
    __all__ = ["model_manager"]

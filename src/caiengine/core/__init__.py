
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
    from .categorizer import Categorizer
    from .context_filer import ContextFilter
    from .trust_module import TrustModule
    from .time_decay_scorer import TimeDecayScorer
    from .ann_index import ANNIndex
    from .goal_feedback_loop import GoalDrivenFeedbackLoop
    from .goal_strategies import (
        SimpleGoalFeedbackStrategy,
        PersonalityGoalFeedbackStrategy,
    )
    from .model_storage import save_model_with_metadata, load_model_with_metadata

    __all__ = [
        "CacheManager",
        "ContextManager",
        "DistributedContextManager",
        "ContextHookManager",
        "ContextHook",
        "Fuser",
        "PolicyEvaluator",
        "Categorizer",
        "ContextFilter",
        "TrustModule",
        "TimeDecayScorer",
        "ANNIndex",
        "GoalDrivenFeedbackLoop",
        "SimpleGoalFeedbackStrategy",
        "PersonalityGoalFeedbackStrategy",
        "save_model_with_metadata",
        "load_model_with_metadata",
        "model_manager",
    ]
else:  # pragma: no cover - lightweight import
    __all__ = ["model_manager"]

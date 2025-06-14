from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Dict, List, Optional

from caiengine.pipelines.context_pipeline import ContextPipeline
from caiengine.pipelines.feedback_pipeline import FeedbackPipeline
from caiengine.providers import (
    FileContextProvider,
    XMLContextProvider,
    SQLiteContextProvider,
    MySQLContextProvider,
    MemoryContextProvider,
)
from caiengine.interfaces.context_provider import ContextProvider
from caiengine.inference.dummy_engine import DummyAIInferenceEngine
from caiengine.core.trust_module import TrustModule
from caiengine.core.goal_feedback_loop import GoalDrivenFeedbackLoop
from caiengine.core.goal_strategies.simple_goal_strategy import SimpleGoalFeedbackStrategy
from caiengine.policies.simple_policy import SimplePolicyEvaluator
from caiengine.parser.log_parser import LogParser


_PROVIDER_MAP = {
    "json": FileContextProvider,
    "xml": XMLContextProvider,
    "sqlite": SQLiteContextProvider,
    "mysql": MySQLContextProvider,
    "memory": lambda **kwargs: ContextProvider(**kwargs),
}


@dataclass
class ConfigurablePipeline:
    pipeline: ContextPipeline | FeedbackPipeline
    provider: Any
    parser: Any = None
    candidates: List[Dict] | None = None
    trust_module: Optional[TrustModule] = None
    policy: Optional[SimplePolicyEvaluator] = None
    feedback_loop: Optional[GoalDrivenFeedbackLoop] = None

    @classmethod
    def from_dict(cls, cfg: Dict[str, Any]) -> "ConfigurablePipeline":
        prov_cfg = cfg.get("provider", {})
        prov_type = prov_cfg.get("type", "memory")
        prov_args = prov_cfg.get("args", {})
        if prov_type not in _PROVIDER_MAP:
            raise ValueError(f"Unsupported provider type: {prov_type}")
        provider_factory = _PROVIDER_MAP[prov_type]
        if prov_type == "memory" and "context_weights" not in prov_args and "trust_weights" in cfg:
            prov_args = dict(prov_args)
            prov_args["context_weights"] = cfg["trust_weights"]
        provider = provider_factory(**prov_args)

        parser = LogParser() if cfg.get("parser") == "log" else None

        trust_module = None
        if "trust_weights" in cfg:
            trust_module = TrustModule(cfg["trust_weights"], parser=parser)

        policy = SimplePolicyEvaluator() if cfg.get("policy") == "simple" else None

        feedback_cfg = cfg.get("feedback") or {}
        feedback_loop = None
        if not feedback_cfg:
            pipeline = ContextPipeline(provider)
        elif feedback_cfg.get("type") == "complex_nn":
            from caiengine.core.learning.learning_manager import LearningManager
            manager = LearningManager(
                feedback_cfg.get("input_size", 4),
                hidden_size=feedback_cfg.get("hidden_size", 16),
                output_size=feedback_cfg.get("output_size", 1),
                parser=parser,
            )
            pipeline = FeedbackPipeline(
                provider, manager.inference_engine, learning_manager=manager
            )
        elif feedback_cfg.get("type") == "goal":
            engine = DummyAIInferenceEngine()
            pipeline = FeedbackPipeline(provider, engine)
            strategy = SimpleGoalFeedbackStrategy(
                feedback_cfg.get("one_direction_layers", [])
            )
            feedback_loop = GoalDrivenFeedbackLoop(
                strategy, goal_state=feedback_cfg.get("goal_state", {})
            )
        else:
            raise ValueError(f"Unsupported feedback type: {feedback_cfg.get('type')}")

        return cls(
            pipeline=pipeline,
            provider=provider,
            parser=parser,
            candidates=cfg.get("candidates", []),
            trust_module=trust_module,
            policy=policy,
            feedback_loop=feedback_loop,
        )

    def run(self, data_batch: List[Any]) -> List[Dict]:
        processed = []
        for item in data_batch:
            if self.parser and isinstance(item, str):
                item = self.parser.transform(item)
            processed.append(item)

        results = self.pipeline.run(processed, self.candidates or [])

        if isinstance(results, dict):
            results = [dict(v, category=k) for k, v in results.items()]

        if self.policy:
            filtered = []
            for res in results:
                ctx = res.get("item", res)
                outcome = self.policy.evaluate(ctx)
                if isinstance(outcome, tuple):
                    passed, pred = outcome
                else:
                    passed, pred = outcome, None
                if passed:
                    if pred is not None:
                        res["prediction"] = pred
                    filtered.append(res)
            results = filtered

        if self.trust_module:
            for res in results:
                ctx = res.get("item", res)
                presence = {k: bool(ctx.get(k)) for k in self.trust_module.weights}
                res["trust"] = self.trust_module.calculate_trust(presence)

        if self.feedback_loop:
            actions = [r.get("prediction", {}) for r in results]
            suggestions = self.feedback_loop.suggest([], actions)
            for res, sugg in zip(results, suggestions):
                res["goal_suggestion"] = sugg

        return results

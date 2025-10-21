from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Dict, List, Optional

from caiengine.pipelines.context_pipeline import ContextPipeline
from caiengine.pipelines.feedback_pipeline import FeedbackPipeline
from caiengine.providers import (
    CSVContextProvider,
    FileContextProvider,
    HTTPContextProvider,
    KafkaContextProvider,
    MemoryContextProvider,
    MockContextProvider,
    MySQLContextProvider,
    OCRContextProvider,
    PostgresContextProvider,
    RedisContextProvider,
    SQLiteContextProvider,
    SimpleContextProvider,
    XMLContextProvider,
)
from caiengine.interfaces.context_provider import ContextProvider
from caiengine.inference.dummy_engine import DummyAIInferenceEngine
from caiengine.inference.token_usage_tracker import TokenUsageTracker
from caiengine.core.trust_module import TrustModule
from caiengine.core.goal_feedback_loop import GoalDrivenFeedbackLoop
from caiengine.core.goal_strategies.simple_goal_strategy import SimpleGoalFeedbackStrategy
from caiengine.policies.simple_policy import SimplePolicyEvaluator
from caiengine.parser.log_parser import LogParser
from caiengine.common import AuditLogger


_PROVIDER_MAP = {
    "json": FileContextProvider,
    "file": FileContextProvider,
    "xml": XMLContextProvider,
    "sqlite": SQLiteContextProvider,
    "mysql": MySQLContextProvider,
    "postgres": PostgresContextProvider,
    "postgresql": PostgresContextProvider,
    "memory": MemoryContextProvider,
    "redis": RedisContextProvider,
    "kafka": KafkaContextProvider,
    "http": HTTPContextProvider,
    "csv": CSVContextProvider,
    "ocr": OCRContextProvider,
    "mock": MockContextProvider,
    "simple": SimpleContextProvider,
}


class _TrustWrappingProvider:
    """Proxy that augments providers with trust weighting helpers."""

    def __init__(
        self,
        provider: Any,
        *,
        trust_weights: dict | None = None,
        layer_types: dict | None = None,
    ) -> None:
        self._provider = provider
        self._delegate = ContextProvider(
            context_weights=trust_weights, layer_types=layer_types
        )

    def __getattr__(self, item: str) -> Any:
        return getattr(self._provider, item)

    def calculate_trust(self, context_data: dict) -> float:
        return self._delegate.calculate_trust(context_data)

    def get_adjusted_weight(self, base_weight: float, context_data: dict) -> float:
        return self._delegate.get_adjusted_weight(base_weight, context_data)


@dataclass
class ConfigurablePipeline:
    pipeline: ContextPipeline | FeedbackPipeline
    provider: Any
    parser: Any = None
    candidates: List[Dict] | None = None
    trust_module: Optional[TrustModule] = None
    policy: Optional[SimplePolicyEvaluator] = None
    feedback_loop: Optional[GoalDrivenFeedbackLoop] = None
    audit_logger: AuditLogger | None = None

    @classmethod
    def from_dict(cls, cfg: Dict[str, Any], audit_logger: AuditLogger | None = None) -> "ConfigurablePipeline":
        prov_cfg = cfg.get("provider", {})
        prov_type = prov_cfg.get("type", "memory")
        prov_args = prov_cfg.get("args", {})
        if prov_type not in _PROVIDER_MAP:
            raise ValueError(f"Unsupported provider type: {prov_type}")
        provider_factory = _PROVIDER_MAP[prov_type]
        provider = provider_factory(**prov_args)

        pipeline_provider: Any = provider
        if not hasattr(pipeline_provider, "get_adjusted_weight"):
            pipeline_provider = _TrustWrappingProvider(
                pipeline_provider, trust_weights=cfg.get("trust_weights")
            )

        parser = LogParser() if cfg.get("parser") == "log" else None

        trust_module = None
        if "trust_weights" in cfg:
            trust_module = TrustModule(cfg["trust_weights"], parser=parser)

        policy = SimplePolicyEvaluator() if cfg.get("policy") == "simple" else None

        feedback_cfg = cfg.get("feedback") or {}
        feedback_loop = None
        if not feedback_cfg:
            pipeline = ContextPipeline(pipeline_provider, audit_logger=audit_logger)
        elif feedback_cfg.get("type") == "complex_nn":
            from caiengine.core.learning.learning_manager import LearningManager
            manager = LearningManager(
                feedback_cfg.get("input_size", 4),
                hidden_size=feedback_cfg.get("hidden_size", 16),
                output_size=feedback_cfg.get("output_size", 1),
                parser=parser,
            )
            engine = TokenUsageTracker(manager.inference_engine)
            manager.inference_engine = engine
            pipeline = FeedbackPipeline(
                pipeline_provider,
                engine,
                learning_manager=manager,
                audit_logger=audit_logger,
            )
        elif feedback_cfg.get("type") == "goal":
            engine = TokenUsageTracker(DummyAIInferenceEngine())
            pipeline = FeedbackPipeline(
                pipeline_provider, engine, audit_logger=audit_logger
            )
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
            audit_logger=audit_logger,
        )

    def run(self, data_batch: List[Any]) -> List[Dict]:
        processed = []
        for item in data_batch:
            if self.parser and isinstance(item, str):
                item = self.parser.transform(item)
            processed.append(item)

        if self.audit_logger:
            self.audit_logger.log("ConfigurablePipeline", "preprocessed", {"items": len(processed)})

        results = self.pipeline.run(processed, self.candidates or [])

        if self.audit_logger:
            self.audit_logger.log("ConfigurablePipeline", "pipeline_run", {"results": len(results) if isinstance(results, list) else len(results.keys())})

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
            if self.audit_logger:
                self.audit_logger.log("ConfigurablePipeline", "policy_applied", {"results": len(results)})

        if self.trust_module:
            for res in results:
                ctx = res.get("item", res)
                presence = {k: bool(ctx.get(k)) for k in self.trust_module.weights}
                res["trust"] = self.trust_module.calculate_trust(presence)
            if self.audit_logger:
                self.audit_logger.log("ConfigurablePipeline", "trust_calculated", {})

        if self.feedback_loop:
            actions = [r.get("prediction", {}) for r in results]
            suggestions = self.feedback_loop.suggest([], actions)
            for res, sugg in zip(results, suggestions):
                res["goal_suggestion"] = sugg
            if self.audit_logger:
                self.audit_logger.log("ConfigurablePipeline", "feedback_suggested", {})

        return results

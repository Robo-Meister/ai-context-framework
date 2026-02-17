"""Built-in expert implementation for tests and local orchestration."""

from __future__ import annotations

from typing import Any

from caiengine.inference import DummyAIInferenceEngine

from .expert_types import ExpertResult


class DummyExpert:
    """Adapter that exposes :class:`DummyAIInferenceEngine` as an orchestration expert."""

    expert_id = "dummy_expert"

    def __init__(self, engine: DummyAIInferenceEngine | None = None) -> None:
        self.engine = engine or DummyAIInferenceEngine()

    def run(self, input: dict[str, Any], context: dict[str, Any]) -> ExpertResult:
        payload = dict(input)
        payload["context"] = context
        inference_result = self.engine.infer(payload)
        return ExpertResult(
            output=inference_result,
            confidence=float(inference_result.get("confidence", 0.0)),
            cost_ms=0.0,
            debug={"engine": self.engine.__class__.__name__},
            used_layers=["dummy"],
            model_id="dummy-ai",
            model_version="1",
        )

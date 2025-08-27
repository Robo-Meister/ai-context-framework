import json
from typing import Dict

from caiengine.interfaces.inference_engine import AIInferenceEngine
from caiengine.common.token_usage import TokenCounter, TokenUsage


class TokenUsageTracker(AIInferenceEngine):
    """Wrap an :class:`AIInferenceEngine` and record token usage for calls."""

    def __init__(self, engine: AIInferenceEngine, counter: TokenCounter | None = None) -> None:
        self.engine = engine
        self.counter = counter or TokenCounter()

    # ------------------------------------------------------------------
    # utility helpers
    # ------------------------------------------------------------------
    def _count_tokens(self, text: str) -> int:
        """Naive whitespace tokeniser used for usage accounting."""
        return len(text.split()) if text else 0

    # ------------------------------------------------------------------
    # AIInferenceEngine interface
    # ------------------------------------------------------------------
    def infer(self, input_data: Dict) -> Dict:
        result = self.engine.infer(input_data)
        prompt_tokens = self._count_tokens(json.dumps(input_data))
        completion_tokens = self._count_tokens(json.dumps(result))
        usage = TokenUsage(prompt_tokens, completion_tokens)
        self.counter.add(usage)
        enriched = dict(result)
        enriched["usage"] = usage.as_dict()
        return enriched

    def predict(self, input_data: Dict) -> Dict:
        result = self.engine.predict(input_data)
        if "usage" in result:
            self.counter.add(result["usage"])
            return result
        prompt_tokens = self._count_tokens(json.dumps(input_data))
        completion_tokens = self._count_tokens(json.dumps(result))
        usage = TokenUsage(prompt_tokens, completion_tokens)
        self.counter.add(usage)
        enriched = dict(result)
        enriched["usage"] = usage.as_dict()
        return enriched

    # delegate optional methods to underlying engine when available
    def train(self, input_data: Dict, target: float) -> float:
        return self.engine.train(input_data, target)

    def replace_model(self, model, lr: float):
        return self.engine.replace_model(model, lr)

    def save_model(self, path: str):
        return self.engine.save_model(path)

    def load_model(self, path: str):
        return self.engine.load_model(path)

    # convenience accessor
    @property
    def usage(self) -> dict:
        """Return aggregated token usage for this tracker."""
        return self.counter.as_dict()

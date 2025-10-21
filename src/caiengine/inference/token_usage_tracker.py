import json
from datetime import datetime
from typing import Callable, Dict, Mapping, Sequence

from caiengine.interfaces.inference_engine import AIInferenceEngine
from caiengine.common.token_usage import TokenCounter, TokenUsage


class TokenUsageTracker(AIInferenceEngine):
    """Wrap an :class:`AIInferenceEngine` and record token usage for calls."""

    def __init__(
        self,
        engine: AIInferenceEngine,
        counter: TokenCounter | None = None,
        *,
        provider: str | None = None,
        usage_listeners: Sequence[Callable[[dict], None]] | None = None,
    ) -> None:
        self.engine = engine
        self.counter = counter or TokenCounter()
        self.provider = provider
        self._usage_listeners: list[Callable[[dict], None]] = []
        if usage_listeners:
            for listener in usage_listeners:
                self.register_usage_listener(listener)

    # ------------------------------------------------------------------
    # utility helpers
    # ------------------------------------------------------------------
    def _count_tokens(self, text: str) -> int:
        """Naive whitespace tokeniser used for usage accounting."""
        return len(text.split()) if text else 0

    def _normalise_for_json(self, value):
        if isinstance(value, datetime):
            return value.isoformat()
        if isinstance(value, Mapping):
            return {k: self._normalise_for_json(v) for k, v in value.items()}
        if isinstance(value, (list, tuple, set)):
            return [self._normalise_for_json(v) for v in value]
        return value

    def register_usage_listener(self, listener: Callable[[dict], None]) -> None:
        """Register a callback to receive token usage events."""

        self._usage_listeners.append(listener)

    def _emit_usage_event(
        self,
        operation: str,
        input_data: Dict,
        usage: TokenUsage | dict,
    ) -> None:
        if not self._usage_listeners:
            return

        if isinstance(usage, dict):
            usage_obj = TokenUsage(**usage)
        else:
            usage_obj = usage

        event = {
            "timestamp": datetime.utcnow().isoformat(),
            "operation": operation,
            "provider": self.provider,
            "category": input_data.get("category"),
            "usage": usage_obj.as_dict(),
        }

        for listener in self._usage_listeners:
            listener(dict(event))

    # ------------------------------------------------------------------
    # AIInferenceEngine interface
    # ------------------------------------------------------------------
    def infer(self, input_data: Dict) -> Dict:
        result = self.engine.infer(input_data)
        prompt_tokens = self._count_tokens(json.dumps(self._normalise_for_json(input_data)))
        completion_tokens = self._count_tokens(json.dumps(self._normalise_for_json(result)))
        usage = TokenUsage(prompt_tokens, completion_tokens)
        self.counter.add(usage)
        self._emit_usage_event("infer", input_data, usage)
        enriched = dict(result)
        enriched["usage"] = usage.as_dict()
        return enriched

    def predict(self, input_data: Dict) -> Dict:
        result = self.engine.predict(input_data)
        if "usage" in result:
            usage = result["usage"]
            self.counter.add(usage)
            self._emit_usage_event("predict", input_data, usage)
            return result
        prompt_tokens = self._count_tokens(json.dumps(self._normalise_for_json(input_data)))
        completion_tokens = self._count_tokens(json.dumps(self._normalise_for_json(result)))
        usage = TokenUsage(prompt_tokens, completion_tokens)
        self.counter.add(usage)
        self._emit_usage_event("predict", input_data, usage)
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

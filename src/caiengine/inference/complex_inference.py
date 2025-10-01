from __future__ import annotations

from dataclasses import dataclass
from math import exp
from typing import Dict, Iterable, List

from caiengine.interfaces.inference_engine import AIInferenceEngine


def _sigmoid(value: float) -> float:
    return 1.0 / (1.0 + exp(-value))


@dataclass
class _LogisticModel:
    weights: List[float]
    bias: float

    def state_dict(self) -> Dict[str, List[float]]:
        return {"weights": list(self.weights), "bias": [self.bias]}

    def load_state_dict(self, state: Dict[str, Iterable[float]]) -> None:
        self.weights = [float(v) for v in state.get("weights", self.weights)]
        bias_values = list(state.get("bias", [self.bias]))
        self.bias = float(bias_values[0]) if bias_values else self.bias


class ComplexAIInferenceEngine(AIInferenceEngine):
    """Gradient-descent based learner that mimics the torch implementation."""

    def __init__(self, input_size: int, hidden_size: int = 16, output_size: int = 1, lr: float = 0.2):
        del hidden_size, output_size  # parameters kept for API compatibility
        self.learning_rate = lr
        self.model = _LogisticModel(weights=[0.0] * input_size, bias=0.0)

    def _forward(self, features: Iterable[float]) -> float:
        total = sum(w * f for w, f in zip(self.model.weights, features)) + self.model.bias
        return _sigmoid(total)

    def infer(self, input_data: Dict) -> Dict[str, float]:
        value = self.predict(input_data)["prediction"]
        return {"prediction": value, "confidence": min(1.0, max(0.0, value))}

    def predict(self, input_data: Dict) -> Dict[str, float]:
        features = [float(v) for v in input_data.get("features", [])]
        prediction = self._forward(features)
        return {"prediction": prediction, "confidence": min(1.0, max(0.0, prediction))}

    def train(self, input_data: Dict, target: float) -> float:
        features = [float(v) for v in input_data.get("features", [])]
        prediction = self._forward(features)
        error = prediction - float(target)
        for i, feature in enumerate(features):
            self.model.weights[i] -= self.learning_rate * error * feature
        self.model.bias -= self.learning_rate * error
        loss = error * error
        return loss

    def get_model(self) -> _LogisticModel:
        return self.model

    def replace_model(self, model: _LogisticModel, lr: float = 0.01) -> None:
        self.model = model
        self.learning_rate = lr

    def save_model(self, path: str) -> None:
        import json

        with open(path, "w", encoding="utf-8") as handle:
            json.dump(self.model.state_dict(), handle)

    def load_model(self, path: str) -> None:
        import json

        with open(path, "r", encoding="utf-8") as handle:
            state = json.load(handle)
        self.model.load_state_dict(state)

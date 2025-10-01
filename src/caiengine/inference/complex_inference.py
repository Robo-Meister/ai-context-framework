"""Lightweight complex inference engine used in the tests."""

from __future__ import annotations

from dataclasses import dataclass, asdict
from pathlib import Path
from typing import Dict, List, Sequence
import json
import math

from caiengine.interfaces.inference_engine import AIInferenceEngine


@dataclass
class _LinearModel:
    """Simple linear model trained with gradient descent."""

    weights: List[float]
    bias: float = 0.0

    def linear_output(self, features: Sequence[float]) -> float:
        padded = list(features) + [0.0] * max(0, len(self.weights) - len(features))
        trimmed = padded[: len(self.weights)]
        return sum(w * x for w, x in zip(self.weights, trimmed)) + self.bias

    def apply_gradient(self, features: Sequence[float], gradient: float, lr: float) -> None:
        padded = list(features) + [0.0] * max(0, len(self.weights) - len(features))
        trimmed = padded[: len(self.weights)]
        for idx, value in enumerate(trimmed):
            self.weights[idx] -= lr * gradient * value
        self.bias -= lr * gradient

    def to_dict(self) -> Dict[str, float | List[float]]:
        return asdict(self)

    @classmethod
    def from_dict(cls, data: Dict[str, float | List[float]]) -> "_LinearModel":
        weights = list(data.get("weights", []))  # type: ignore[arg-type]
        bias = float(data.get("bias", 0.0))
        return cls(weights=weights, bias=bias)


class ComplexAIInferenceEngine(AIInferenceEngine):
    def __init__(self, input_size, hidden_size=16, output_size=1, lr: float = 0.01):
        # ``hidden_size`` and ``output_size`` are ignored but retained for
        # compatibility with the original API.
        self.input_size = int(input_size)
        self.learning_rate = float(lr)
        self.model = _LinearModel(weights=[0.0 for _ in range(self.input_size)])

    def infer(self, input_data: dict) -> dict:
        prediction = self._predict_value(input_data)
        return {
            "prediction": complex(prediction, 0.0),
            "confidence": self._confidence_from_prediction(prediction),
        }

    def predict(self, input_data: dict) -> dict:
        return self.infer(input_data)

    def train(self, input_data: dict, target: float) -> float:
        features = self._normalize_features(input_data)
        linear = self.model.linear_output(features)
        prediction = self._sigmoid(linear)
        error = prediction - float(target)
        gradient = 2.0 * error * prediction * (1.0 - prediction)
        self.model.apply_gradient(features, gradient, self.learning_rate)
        return error * error

    def _preprocess(self, input_data):  # pragma: no cover - retained for API
        return self._extract_features(input_data)

    def _train_step(self, input_data, target):  # pragma: no cover - alias
        return self.train(input_data, target)

    def get_model(self):
        return self.model

    def replace_model(self, model, lr: float = 0.01):
        if not isinstance(model, _LinearModel):  # pragma: no cover - defensive
            raise TypeError("Expected a _LinearModel compatible instance")
        self.model = model
        self.learning_rate = float(lr)

    def save_model(self, path: str):
        Path(path).write_text(json.dumps(self.model.to_dict()))

    def load_model(self, path: str):
        data = json.loads(Path(path).read_text())
        self.model = _LinearModel.from_dict(data)

    # ------------------------------------------------------------------
    # Internal helpers
    # ------------------------------------------------------------------
    def _extract_features(self, input_data: Dict) -> List[float]:
        features = input_data.get("features", [])
        return [float(value) for value in features]

    def _normalize_features(self, input_data: Dict) -> List[float]:
        raw = self._extract_features(input_data)
        return [value - 0.5 for value in raw]

    def _predict_value(self, input_data: Dict) -> float:
        features = self._normalize_features(input_data)
        linear = self.model.linear_output(features)
        return self._sigmoid(linear)

    @staticmethod
    def _sigmoid(value: float) -> float:
        if value >= 0:
            exp_neg = math.exp(-value)
            return 1.0 / (1.0 + exp_neg)
        exp_pos = math.exp(value)
        return exp_pos / (1.0 + exp_pos)

    @staticmethod
    def _confidence_from_prediction(prediction: float) -> float:
        return max(0.0, min(1.0, 1.0 - min(1.0, abs(prediction - 0.5) * 2)))

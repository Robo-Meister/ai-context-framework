"""Pure-Python learning manager that avoids heavyweight dependencies."""

from __future__ import annotations

from math import exp
from typing import Dict, List

from caiengine.core.trust_module import TrustModule
from caiengine.interfaces.learning_interface import LearningInterface


def _sigmoid(value: float) -> float:
    return 1.0 / (1.0 + exp(-value))


class LearningManager(LearningInterface):
    """Simple gradient-descent learner operating on context features."""

    def __init__(self, input_size: int, hidden_size: int = 16, output_size: int = 1, lr: float = 0.2, parser=None):
        del hidden_size, output_size  # retained for API compatibility
        self.learning_rate = lr
        self.weights = [0.0 for _ in range(input_size)]
        self.bias = 0.0
        self.history: List[float] = []
        self.trust_module = TrustModule(
            weights={"trust": 1.0, "role": 1.0, "time": 1.0, "frequency": 1.0},
            parser=parser,
        )

    def _forward(self, features: List[float]) -> float:
        total = sum(w * f for w, f in zip(self.weights, features)) + self.bias
        return _sigmoid(total)

    def train_step(self, features: List[float], target: float) -> float:
        prediction = self._forward(features)
        error = prediction - float(target)
        for i, value in enumerate(features):
            self.weights[i] -= self.learning_rate * error * value
        self.bias -= self.learning_rate * error
        loss = error * error
        self.history.append(loss)
        return loss

    def train(self, input_data: Dict, target: float) -> float:
        features = self.trust_module.extract_numeric_features(input_data)
        return self.train_step(features, target)

    def predict(self, input_data: Dict) -> Dict:
        features = self.trust_module.extract_numeric_features(input_data)
        score = self.predict_from_vector(features)
        return {"score": score}

    def predict_from_vector(self, features: List[float]) -> float:
        return self._forward(features)

    def predict_from_context(self, input_data: dict) -> dict:
        features = self.trust_module.extract_numeric_features(input_data)
        score = self.predict_from_vector(features)
        return {"score": score}

    def train_from_context(self, input_data: dict, target: float) -> float:
        features = self.trust_module.extract_numeric_features(input_data)
        return self.train_step(features, target)

    def learn_from_log(self, log_line: str, y_true: float | None = None) -> float:
        features, target_score = self.trust_module.extract_features_and_score(log_line)
        if y_true is None:
            y_true = target_score
        return self.train_step(features, y_true)

    def predict_from_dict(self, input_data: dict) -> float:
        features = self.trust_module.extract_features(input_data)
        return self.predict_from_vector(features)

    def predict_from_log(self, log_line: str, trace: bool = True, y_true: float | None = None) -> float:
        features, _ = self.trust_module.extract_features_and_score(log_line)
        y_pred = self.predict_from_vector(features)
        if trace:
            self.trace(features, y_pred, y_true, meta={"log": log_line})
        return y_pred

    def trace(self, features: List[float], y_pred: float, y_true: float | None = None, meta: dict | None = None):
        self.history.append(
            {
                "input": list(features),
                "predicted": y_pred,
                "target": y_true,
                "meta": meta or {},
                "loss": abs(y_pred - y_true) if y_true is not None else None,
            }
        )

    def infer(self, input_data: dict) -> dict:
        log_line = input_data.get("log_line")
        y_true = input_data.get("label")
        y_pred = self.predict_from_log(log_line, trace=True, y_true=y_true)
        return {
            "prediction": y_pred,
            "input_log": log_line,
            "label": y_true,
            "confidence": min(1.0, abs(y_pred)),
        }

    def learn_from_feedback(self, log_line: str, corrected_label: float) -> float:
        return self.learn_from_log(log_line, corrected_label)


from typing import List, Dict
import math

from core.trust_module import TrustModule
from interfaces.learning_interface import LearningInterface


class LearningManager(LearningInterface):
    """Lightweight learning manager using a simple logistic model."""

    def __init__(self, input_size: int, hidden_size: int = 16, output_size: int = 1, lr: float = 0.1, parser=None):
        self.input_size = input_size
        self.lr = lr
        # Simple weights and bias for logistic regression
        self.weights = [0.0 for _ in range(input_size)]
        self.bias = 0.0
        self.history = []
        self.trust_module = TrustModule(weights={"trust": 1.0, "role": 1.0, "time": 1.0, "frequency": 1.0}, parser=parser)

    def _forward(self, x: List[float]) -> float:
        z = self.bias + sum(w * xi for w, xi in zip(self.weights, x))
        # Sigmoid activation to keep output in [0,1]
        return 1.0 / (1.0 + math.exp(-z))

    def train_step(self, x: List[float], y_true: float) -> float:
        """Perform one gradient descent step."""
        y_pred = self._forward(x)
        error = y_pred - y_true

        grad = error * y_pred * (1.0 - y_pred)
        for i, xi in enumerate(x):
            self.weights[i] -= self.lr * grad * xi
        self.bias -= self.lr * grad

        loss = error * error
        self.history.append(float(loss))
        return float(loss)
    # def predict(self, input_data: dict) -> dict:
    #     return self.inference_engine.infer(input_data)
    #
    # def train(self, input_data: dict, target: float) -> float:
    #     return self.inference_engine.train(input_data, target)

    def train(self, input_data: Dict, target: float) -> float:
        features = self.trust_module.extract_numeric_features(input_data)
        return self.train_step(features, target)

    def predict(self, input_data: Dict) -> Dict:
        features = self.trust_module.extract_numeric_features(input_data)
        score = self.predict_from_vector(features)
        return {"score": score}

    def predict_from_vector(self, x: List[float]) -> float:
        return self._forward(x)

    def predict_from_context(self, input_data: dict) -> dict:
        features = self.trust_module.extract_numeric_features(input_data)
        score = self.predict_from_vector(features)
        return {"score": score}

    def train_from_context(self, input_data: dict, target: float) -> float:
        features = self.trust_module.extract_numeric_features(input_data)
        return self.train_step(features, target)

    def learn_from_log(self, log_line: str, y_true: float = None) -> float:
        features, target_score = self.trust_module.extract_features_and_score(log_line)
        if y_true is None:
            y_true = target_score  # fallback to TrustModule's target score if no external label given
        loss = self.train_step(features, y_true)
        return loss

    def predict_from_dict(self, input_data: dict) -> float:
        features = self.trust_module.extract_features(input_data)
        return self.predict_from_vector(features)

    def predict_from_log(self, log_line: str, trace: bool = True, y_true: float = None) -> float:
        features, _ = self.trust_module.extract_features_and_score(log_line)
        y_pred = self.predict_from_vector(features)
        if trace:
            self.trace(features, y_pred, y_true, meta={"log": log_line})
        return y_pred

    def trace(self, x: List[float], y_pred: float, y_true: float = None, meta: dict = None):
        self.history.append({
            "input": x,
            "predicted": y_pred,
            "target": y_true,
            "meta": meta or {},
            "loss": abs(y_pred - y_true) if y_true is not None else None
        })

    def infer(self, input_data: dict) -> dict:
        log_line = input_data.get("log_line")
        y_true = input_data.get("label")  # optional ground truth
        y_pred = self.predict_from_log(log_line, trace=True, y_true=y_true)

        return {
            "prediction": y_pred,
            "input_log": log_line,
            "label": y_true,
            "confidence": min(1.0, abs(y_pred)),  # temp logic
        }
    def learn_from_feedback(self, log_line: str, corrected_label: float) -> float:
        return self.learn_from_log(log_line, corrected_label)

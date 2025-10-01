from __future__ import annotations

from typing import List, Dict, Any

from caiengine.core.trust_module import TrustModule
from caiengine.inference.complex_inference import ComplexAIInferenceEngine
from caiengine.interfaces.learning_interface import LearningInterface


class LearningManager(LearningInterface):
    def __init__(self, input_size: int, hidden_size: int = 16, output_size: int = 1, lr: float = 0.01, parser=None):
        self.inference_engine = ComplexAIInferenceEngine(input_size, hidden_size, output_size)
        self.history = []
        self.trust_module = TrustModule(weights={"trust": 1.0, "role": 1.0, "time": 1.0, "frequency": 1.0}, parser= parser)

    def train_step(self, x: List[float], y_true: float):
        loss = self.inference_engine.train({"features": x}, y_true)
        self.history.append(loss)
        return loss

    def train(self, input_data: Dict, target: float) -> float:
        features = self.trust_module.extract_numeric_features(input_data)
        return self.train_step(features, target)

    def predict(self, input_data: Dict) -> Dict:
        features = self.trust_module.extract_numeric_features(input_data)
        score = self.predict_from_vector(features)
        return {"score": score}

    def predict_from_vector(self, x: List[float]) -> float:
        result = self.inference_engine.predict({"features": x})
        prediction = result.get("prediction", 0.0)
        if hasattr(prediction, "real"):
            return float(prediction.real)
        return float(prediction)

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
        entry: Dict[str, Any] = {
            "input": x,
            "predicted": y_pred,
            "target": y_true,
            "meta": meta or {},
        }
        entry["loss"] = abs(y_pred - y_true) if y_true is not None else None
        self.history.append(entry)

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

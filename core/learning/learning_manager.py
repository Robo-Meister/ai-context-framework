from typing import List, Dict

from torch import optim

from core.learning.complex_net import ComplexNet
import torch.nn as nn
import torch
from core.trust_module import TrustModule
from inference.complex_inference import ComplexAIInferenceEngine
from interfaces.learning_interface import LearningInterface


class LearningManager(LearningInterface):
    def __init__(self, input_size: int, hidden_size: int = 16, output_size: int = 1, lr: float = 0.01, parser=None):
        self.inference_engine = ComplexAIInferenceEngine(input_size, hidden_size, output_size)
        self.model = self.inference_engine.get_model()
        self.loss_fn = nn.MSELoss()
        self.optimizer = optim.Adam(self.model.parameters(), lr=lr)
        self.history = []
        self.trust_module = TrustModule(weights={"trust": 1.0, "role": 1.0, "time": 1.0, "frequency": 1.0}, parser= parser)

    def _to_complex_tensor(self, features: List[float]) -> torch.Tensor:
        real = torch.tensor(features, dtype=torch.float32)
        imag = torch.zeros_like(real)
        return torch.complex(real, imag)
    def train_step(self, x: List[float], y_true: float):
        self.model.train()
        z = self._to_complex_tensor(x)
        output = self.model(z)
        target = torch.tensor([y_true], dtype=torch.float32)

        loss = self.loss_fn(torch.abs(output), target)
        self.optimizer.zero_grad()
        loss.backward()
        self.optimizer.step()
        self.history.append(loss.item())
        return loss.item()
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
        self.model.eval()
        with torch.no_grad():
            z = self._to_complex_tensor(x)
            output = self.model(z)
            return torch.abs(output).item()

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

from typing import List

from torch import optim

from ContextAi.core.learning.complex_net import ComplexNet
import torch.nn as nn
import torch
from ContextAi.core.trust_module import TrustModule


class LearningManager:
    def __init__(self, input_size: int, hidden_size: int = 16, output_size: int = 1, lr: float = 0.01, parser=None):
        self.model = ComplexNet(input_size, hidden_size, output_size)
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

    def predict(self, x: List[float]) -> float:
        self.model.eval()
        with torch.no_grad():
            z = self._to_complex_tensor(x)
            output = self.model(z)
            return torch.abs(output).item()

    def learn_from_log(self, log_line: str, y_true: float = None) -> float:
        features, target_score = self.trust_module.extract_features_and_score(log_line)
        if y_true is None:
            y_true = target_score  # fallback to TrustModule's target score if no external label given
        loss = self.train_step(features, y_true)
        return loss

    def predict_from_log(self, log_line: str) -> float:
        features, _ = self.trust_module.extract_features_and_score(log_line)
        return self.predict(features)

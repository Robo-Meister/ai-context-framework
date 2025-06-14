import torch
import torch.nn as nn

from caiengine.core.learning.complex_net import ComplexNet
from caiengine.interfaces.inference_engine import AIInferenceEngine


class ComplexAIInferenceEngine(AIInferenceEngine):
    def __init__(self, input_size, hidden_size=16, output_size=1, lr: float = 0.01):
        self.model = ComplexNet(input_size, hidden_size, output_size)
        self.loss_fn = nn.MSELoss()
        self.optimizer = torch.optim.Adam(self.model.parameters(), lr=lr)

    def infer(self, input_data: dict) -> dict:
        # Convert input dict to tensor (you decide input format)
        x = self._preprocess(input_data)
        with torch.no_grad():
            y_pred = self.model(x).real
        return {"prediction": y_pred.item(), "confidence": 1.0}

    def predict(self, input_data: dict) -> dict:
        return self.infer(input_data)

    def train(self, input_data: dict, target: float) -> float:
        # Implement training loop or forward call here
        loss = self._train_step(input_data, target)
        return loss

    def _preprocess(self, input_data):
        # Expect input_data to contain a list of numeric features
        features = input_data.get("features", [])
        real = torch.tensor(features, dtype=torch.float32)
        imag = torch.zeros_like(real)
        return torch.complex(real, imag)

    def _train_step(self, input_data, target):
        # One step of training returning loss float
        self.model.train()
        x = self._preprocess(input_data)
        y_true = torch.tensor([target], dtype=torch.float32)
        output = self.model(x).real
        loss = self.loss_fn(output, y_true)
        self.optimizer.zero_grad()
        loss.backward()
        self.optimizer.step()
        return loss.item()

    def get_model(self):
        return self.model

    def replace_model(self, model: nn.Module, lr: float = 0.01):
        """Replace the underlying model and optimizer."""
        self.model = model
        self.optimizer = torch.optim.Adam(self.model.parameters(), lr=lr)
        self.loss_fn = nn.MSELoss()

    def save_model(self, path: str):
        """Persist the current model to ``path``."""
        torch.save(self.model.state_dict(), path)

    def load_model(self, path: str):
        """Load model weights from ``path``."""
        state = torch.load(path)
        self.model.load_state_dict(state)
